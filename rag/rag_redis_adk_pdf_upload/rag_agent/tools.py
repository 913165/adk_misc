"""
Custom ADK tools for PDF RAG operations.
These functions are used by the ADK agent as callable tools.
"""

import os
from .redis_store import RedisVectorStore

_store = None


def _get_store() -> RedisVectorStore:
    global _store
    if _store is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _store = RedisVectorStore(redis_url=redis_url)
    return _store


def search_documents(query: str, top_k: int = 5, filename: str = "") -> dict:
    """Search through indexed PDF documents using semantic similarity.

    Use this tool to find relevant passages from uploaded PDFs that can
    help answer the user's question.

    Args:
        query: The search query describing what information to find.
        top_k: Number of top results to return (default 5).
        filename: Optional — filter results to a specific PDF filename.

    Returns:
        A dictionary with 'results' (list of matching passages with metadata)
        and 'total' (number of results found).
    """
    store = _get_store()
    fname_filter = filename if filename else None
    results = store.search(query=query, top_k=top_k, filename_filter=fname_filter)

    if not results:
        return {
            "results": [],
            "total": 0,
            "message": "No relevant passages found. The user may need to upload PDFs first.",
        }

    formatted = []
    for r in results:
        formatted.append({
            "text": r["text"],
            "filename": r["filename"],
            "page": r["page_num"],
            "relevance_score": round(1 - r["score"], 4),  # convert distance to similarity
        })

    return {
        "results": formatted,
        "total": len(formatted),
    }


def list_documents() -> dict:
    """List all PDF documents that have been indexed in the vector store.

    Use this tool when the user asks which documents are available or
    wants to know what has been uploaded.

    Returns:
        A dictionary with 'files' (list of indexed filenames) and 'count'.
    """
    store = _get_store()
    files = store.list_indexed_files()
    return {
        "files": files,
        "count": len(files),
        "message": "No documents indexed yet." if not files else f"{len(files)} document(s) indexed.",
    }
