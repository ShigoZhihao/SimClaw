# ====================================================================
# memory/search.py — ハイブリッド検索（ベクトル + BM25）
# ====================================================================
#
# 【このファイルは何？】
# ベクトル検索（意味で探す）+ BM25検索（キーワードで探す）を
# 組み合わせて精度を上げる「ハイブリッド検索」を実装する。
#
# 【なぜ2種類？】
# ベクトル検索: 「流体解析のメッシュ」→「CFDのグリッド生成」も見つかる
# BM25検索:     「PolyhederalMesher」→ 正確なクラス名で見つかる
# 両方を組み合わせると漏れが減る。
# ====================================================================


class HybridSearch:
    """ベクトル検索とBM25検索を組み合わせたハイブリッド検索。"""

    def __init__(self, config):
        self.vector_weight = config.memory.vector_weight   # 0.6
        self.bm25_weight = config.memory.bm25_weight       # 0.4
        self.top_k = config.rag.top_k

        from sentence_transformers import SentenceTransformer
        import chromadb

        self.embed_model = SentenceTransformer(
            config.embedding.model_name, device=config.embedding.device
        )
        self.chroma_client = chromadb.PersistentClient(path=config.rag.db_dir)

        # BM25 用のコーパス（全文書を保持する）
        self._bm25_corpus = []
        self._bm25_index = None

    def add_documents(self, collection_name, documents):
        """ドキュメントをベクトルDB + BM25インデックスに追加する。"""
        if not documents:
            return

        collection = self.chroma_client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        texts = [d["text"] for d in documents]
        embeddings = self.embed_model.encode(texts).tolist()
        collection.upsert(
            ids=[d["id"] for d in documents],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{"source": d.get("source", "")} for d in documents],
        )

        self._bm25_corpus.extend(documents)
        self._rebuild_bm25()

    def search(self, query, collection_name, top_k=None):
        """ハイブリッド検索を実行する。

        引数:
            query: 検索クエリ
            collection_name: ChromaDB コレクション名
            top_k: 返す件数
        戻り値:
            [{"text": ..., "source": ..., "score": ...}] のリスト
        """
        k = top_k or self.top_k

        # 両方の検索を実行する（件数を多めにして後でマージする）
        vec_results = self._vector_search(query, collection_name, k * 2)
        bm25_results = self._bm25_search(query, k * 2)

        # スコアを正規化してマージする
        merged = self._merge(vec_results, bm25_results)
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:k]

    def _vector_search(self, query, collection_name, k):
        """ChromaDB でベクトル検索する。"""
        try:
            col = self.chroma_client.get_collection(collection_name)
        except Exception:
            return []

        emb = self.embed_model.encode([query]).tolist()
        res = col.query(query_embeddings=emb, n_results=k)

        return [
            {
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "source": res["metadatas"][0][i].get("source", ""),
                "v": 1 - res["distances"][0][i],  # コサイン距離をスコアに変換
            }
            for i in range(len(res["ids"][0]))
        ]

    def _bm25_search(self, query, k):
        """BM25 でキーワード検索する。"""
        if not self._bm25_index:
            return []

        scores = self._bm25_index.get_scores(query.lower().split())
        results = [
            {
                "id": self._bm25_corpus[i]["id"],
                "text": self._bm25_corpus[i]["text"],
                "source": self._bm25_corpus[i].get("source", ""),
                "b": score,
            }
            for i, score in enumerate(scores) if score > 0
        ]
        results.sort(key=lambda x: x["b"], reverse=True)
        return results[:k]

    def _merge(self, vec_results, bm25_results):
        """ベクトルスコアとBM25スコアを正規化して合成する。"""
        combined = {}

        # ベクトル検索結果を登録する
        if vec_results:
            max_v = max(r["v"] for r in vec_results) or 1
            for r in vec_results:
                combined[r["id"]] = {
                    "text": r["text"],
                    "source": r["source"],
                    "vs": r["v"] / max_v,   # 0〜1に正規化
                    "bs": 0,
                }

        # BM25検索結果をマージする
        if bm25_results:
            max_b = max(r["b"] for r in bm25_results) or 1
            for r in bm25_results:
                if r["id"] in combined:
                    combined[r["id"]]["bs"] = r["b"] / max_b
                else:
                    combined[r["id"]] = {
                        "text": r["text"],
                        "source": r["source"],
                        "vs": 0,
                        "bs": r["b"] / max_b,
                    }

        # 重み付きスコアを計算する
        return [
            {
                "text": d["text"],
                "source": d["source"],
                "score": self.vector_weight * d["vs"] + self.bm25_weight * d["bs"],
            }
            for d in combined.values()
        ]

    def _rebuild_bm25(self):
        """BM25インデックスを再構築する。"""
        if not self._bm25_corpus:
            self._bm25_index = None
            return
        from rank_bm25 import BM25Okapi
        self._bm25_index = BM25Okapi([d["text"].lower().split() for d in self._bm25_corpus])
