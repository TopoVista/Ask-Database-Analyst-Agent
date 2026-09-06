"""RAG (Retrieval-Augmented Generation) package.

Provides document ingestion, chunking, vector storage, and retrieval
with per-user scoping for grounding LLM responses in uploaded documents.
"""

from app.rag.chunker import Chunk, chunk_text
from app.rag.parser import parse_document
from app.rag.retriever import RAGRetriever
from app.rag.vector_store import VectorStore, get_vector_store

__all__ = [
    "Chunk",
    "chunk_text",
    "parse_document",
    "RAGRetriever",
    "VectorStore",
    "get_vector_store",
]
