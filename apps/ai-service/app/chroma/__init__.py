from __future__ import annotations

from app.chroma.chunker import chunk_markdown_body, load_and_chunk_knowledge_dir
from app.chroma.client import (
    ChromaHttpVectorStoreAdapter,
    ChromaKnowledgeService,
    InMemoryVectorStoreAdapter,
    VectorStoreAdapter,
    build_default_chroma_service,
)
from app.chroma.embedding import (
    DEFAULT_EMBEDDING_DIM,
    LocalHashEmbeddingFunction,
    cosine_distance,
)
from app.chroma.schemas import (
    ChromaCollectionNotFoundError,
    ChromaIngestSummary,
    ChromaQueryHit,
    ChromaUnavailableError,
    ChunkMetadataRecord,
    HitAt3EvalReport,
    KnowledgeChunkRecord,
)

__all__ = [
    "DEFAULT_EMBEDDING_DIM",
    "ChromaCollectionNotFoundError",
    "ChromaHttpVectorStoreAdapter",
    "ChromaIngestSummary",
    "ChromaKnowledgeService",
    "ChromaQueryHit",
    "ChromaUnavailableError",
    "ChunkMetadataRecord",
    "HitAt3EvalReport",
    "InMemoryVectorStoreAdapter",
    "KnowledgeChunkRecord",
    "LocalHashEmbeddingFunction",
    "VectorStoreAdapter",
    "build_default_chroma_service",
    "chunk_markdown_body",
    "cosine_distance",
    "load_and_chunk_knowledge_dir",
]
