import hashlib
import json
import numpy as np
from typing import Optional

import redis
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema
from sentence_transformers import SentenceTransformer

INDEX_NAME = "pdf_chunks"
PREFIX = "doc"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

SCHEMA_DICT = {
    "index": {
        "name": INDEX_NAME,
        "prefix": PREFIX,
        "storage_type": "hash",
    },
    "fields": [
        {"name": "filename", "type": "tag"},
        {"name": "page_num", "type": "numeric"},
        {"name": "chunk_id", "type": "tag"},
        {"name": "text", "type": "text"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "algorithm": "hnsw",
                "datatype": "float32",
                "dims": EMBEDDING_DIM,
                "distance_metric": "cosine",
            },
        },
    ],
}

# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> bytes:
    """Return embedding as float32 bytes suitable for Redis HSET."""
    model = _get_model()
    vec = model.encode(text)
    return np.array(vec, dtype=np.float32).tobytes()


def embed_texts(texts: list[str]) -> list[bytes]:
    """Batch-embed a list of texts."""
    model = _get_model()
    vecs = model.encode(texts, show_progress_bar=False)
    return [np.array(v, dtype=np.float32).tobytes() for v in vecs]


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# RedisVectorStore class
# ---------------------------------------------------------------------------

class RedisVectorStore:
    """Manages a Redis vector index for PDF document chunks."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.client = redis.from_url(redis_url, decode_responses=True)
        self.schema = IndexSchema.from_dict(SCHEMA_DICT)
        self.index = SearchIndex(self.schema, self.client)
        self._ensure_index()

    def _ensure_index(self):
        """Create the index if it doesn't already exist."""
        try:
            self.index.create(overwrite=False)
        except Exception:
            pass  # index already exists

    # nike.pdf:p3:c2
    def _make_key(self, filename: str, page: int, chunk_idx: int) -> str:
        raw = f"{filename}:p{page}:c{chunk_idx}"
        return hashlib.md5(raw.encode()).hexdigest()
        # a7c91f9bfa...

    # ----- Ingestion --------------------------------------------------------

    def ingest_pdf_text(self, filename: str, pages: list[dict]):
        """
        Ingest extracted PDF text into Redis.

        Args:
            filename: original PDF filename
            pages: list of dicts with keys 'page_num' (1-based) and 'text'
        """
        all_records = []
        all_texts = []

        for page_info in pages:
            page_num = page_info["page_num"]
            text = page_info["text"]
            chunks = chunk_text(text)

            for ci, chunk in enumerate(chunks):
                key = self._make_key(filename, page_num, ci)
                all_records.append({
                    "chunk_id": key,
                    "filename": filename,
                    "page_num": page_num,
                    "text": chunk,
                })
                all_texts.append(chunk)

        if not all_texts:
            return 0

        # Batch embed
        embeddings = embed_texts(all_texts)

        # Write to Redis via pipeline
        pipe = self.client.pipeline(transaction=False)
        for rec, emb in zip(all_records, embeddings):
            redis_key = f"{PREFIX}:{rec['chunk_id']}"
            pipe.hset(
                redis_key,
                mapping={
                    "chunk_id": rec["chunk_id"],
                    "filename": rec["filename"],
                    "page_num": str(rec["page_num"]),
                    "text": rec["text"],
                    "embedding": emb,
                },
            )
        pipe.execute()
        return len(all_records)

    # ----- Search -----------------------------------------------------------

    def search(self, query: str, top_k: int = 5, filename_filter: str | None = None) -> list[dict]:
        """
        Semantic search over indexed PDF chunks.

        Returns list of dicts with keys: text, filename, page_num, score.
        """
        query_embedding = embed_text(query)

        vq = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            num_results=top_k,
            return_fields=["text", "filename", "page_num", "chunk_id"],
        )

        if filename_filter:
            from redisvl.query.filter import Tag
            tag_filter = Tag("filename") == filename_filter
            vq.set_filter(tag_filter)

        results = self.index.query(vq)

        output = []
        for r in results:
            output.append({
                "text": r.get("text", ""),
                "filename": r.get("filename", ""),
                "page_num": int(r.get("page_num", 0)),
                "score": float(r.get("vector_distance", 1.0)),
            })
        return output

    # ----- Management -------------------------------------------------------

    def list_indexed_files(self) -> list[str]:
        """Return list of unique filenames in the index."""
        try:
            cursor = 0
            filenames = set()
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=f"{PREFIX}:*", count=200)
                for key in keys:
                    fname = self.client.hget(key, "filename")
                    if fname:
                        filenames.add(fname)
                if cursor == 0:
                    break
            return sorted(filenames)
        except Exception:
            return []

    def delete_file(self, filename: str) -> int:
        """Delete all chunks belonging to a specific file."""
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = self.client.scan(cursor=cursor, match=f"{PREFIX}:*", count=200)
            for key in keys:
                fname = self.client.hget(key, "filename")
                if fname == filename:
                    self.client.delete(key)
                    deleted += 1
            if cursor == 0:
                break
        return deleted

    def clear_all(self):
        """Drop and recreate the index."""
        try:
            self.index.delete(drop=True)
        except Exception:
            pass
        self._ensure_index()
