# ====================================================================
# rag/retriever.py — ベクトル検索
# ====================================================================


class Retriever:
    """ChromaDB でベクトル検索を行う。"""

    def __init__(self, config):
        from sentence_transformers import SentenceTransformer
        import chromadb

        self.embed_model = SentenceTransformer(
            config.embedding.model_name, device=config.embedding.device
        )
        self.client = chromadb.PersistentClient(path=config.rag.db_dir)
        # コレクションが存在しない場合は例外が発生する（RAG未初期化）
        self.collection = self.client.get_collection(config.rag.collection_name)
        self.top_k = config.rag.top_k

    def search(self, query, top_k=None):
        """クエリに関連するドキュメントチャンクを返す。"""
        k = top_k or self.top_k
        embedding = self.embed_model.encode([query]).tolist()
        result = self.collection.query(query_embeddings=embedding, n_results=k)

        return [
            {
                "text": result["documents"][0][i],
                "source": result["metadatas"][0][i].get("source", ""),
                "score": 1 - result["distances"][0][i],
            }
            for i in range(len(result["ids"][0]))
        ]
