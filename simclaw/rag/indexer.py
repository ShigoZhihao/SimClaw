# ====================================================================
# rag/indexer.py — ドキュメント取込み・チャンク化・ChromaDB格納
# ====================================================================

from pathlib import Path


class DocumentIndexer:
    """ドキュメントをRAGインデックスに取り込む。"""

    def __init__(self, config):
        print(f"Embeddingモデル読込み: {config.embedding.model_name}")
        from sentence_transformers import SentenceTransformer
        import chromadb

        self.embed_model = SentenceTransformer(
            config.embedding.model_name, device=config.embedding.device
        )
        self.client = chromadb.PersistentClient(path=config.rag.db_dir)
        self.collection = self.client.get_or_create_collection(
            name=config.rag.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.chunk_size = config.rag.chunk_size
        self.chunk_overlap = config.rag.chunk_overlap

    def index_directory(self, docs_dir):
        """指定フォルダの全ドキュメントを取り込む。"""
        docs_path = Path(docs_dir)
        if not docs_path.exists():
            raise FileNotFoundError(f"フォルダが見つかりません: {docs_dir}")

        indexed = 0
        total_chunks = 0

        for fp in sorted(docs_path.rglob("*")):
            if fp.is_dir():
                continue
            if fp.suffix.lower() not in [".pdf", ".txt", ".md", ".html"]:
                continue

            print(f"  処理中: {fp.name}")
            text = self._load(fp)
            if not text.strip():
                continue

            chunks = self._chunk(text, fp.name)
            self._store(chunks)
            indexed += 1
            total_chunks += len(chunks)
            print(f"    → {len(chunks)} チャンク")

        print(f"\n完了: {indexed} ファイル, {total_chunks} チャンク")
        return {"indexed_files": indexed, "total_chunks": total_chunks}

    def _load(self, path):
        """ファイルからテキストを抽出する。"""
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
        elif path.suffix.lower() in [".txt", ".md"]:
            return path.read_text(encoding="utf-8")
        elif path.suffix.lower() == ".html":
            import re
            return re.sub(r"<[^>]+>", "", path.read_text(encoding="utf-8"))
        return ""

    def _chunk(self, text, source):
        """テキストをチャンクに分割する。"""
        chunks = []
        current = ""
        idx = 0

        for para in text.split("\n\n"):
            if len(current) + len(para) < self.chunk_size:
                current += para + "\n\n"
            else:
                if current.strip():
                    chunks.append({
                        "id": f"{source}_{idx}",
                        "text": current.strip(),
                        "source": source
                    })
                    idx += 1
                # オーバーラップ部分を次のチャンクの先頭に付ける
                overlap = current[-self.chunk_overlap:] if self.chunk_overlap else ""
                current = overlap + para + "\n\n"

        if current.strip():
            chunks.append({
                "id": f"{source}_{idx}",
                "text": current.strip(),
                "source": source
            })
        return chunks

    def _store(self, chunks):
        """チャンクを ChromaDB に保存する。"""
        if not chunks:
            return
        texts = [c["text"] for c in chunks]
        embeddings = self.embed_model.encode(texts).tolist()
        self.collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[{"source": c["source"]} for c in chunks],
        )
