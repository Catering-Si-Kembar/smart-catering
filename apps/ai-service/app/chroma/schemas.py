from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ChromaCollectionNotFoundError(Exception):
    """Raised when the specified ChromaDB collection does not exist."""


class ChromaUnavailableError(Exception):
    """Raised when ChromaDB service is unreachable or vector store client fails."""


@dataclass(frozen=True, slots=True)
class ChunkMetadataRecord:
    """Immutable PIC-validated metadata associated with a knowledge base chunk."""

    doc_id: str
    source: str
    category: str
    version: str
    validated_at: str
    validation_status: str
    is_verified: bool


@dataclass(frozen=True, slots=True)
class KnowledgeChunkRecord:
    """Document chunk extracted from curated markdown knowledge base."""

    chunk_id: str
    content: str
    metadata: ChunkMetadataRecord


@dataclass(frozen=True, slots=True)
class ChromaQueryHit:
    """Individual query hit returned from vector store retrieval."""

    chunk_id: str
    content: str
    distance: float
    metadata: ChunkMetadataRecord


@dataclass(frozen=True, slots=True)
class ChromaIngestSummary:
    """Summary metrics of a knowledge base ingest operation."""

    collection_name: str
    files_processed: int
    chunks_upserted: int
    total_chunks: int
    idempotent: bool = True


@dataclass(frozen=True, slots=True)
class HitAt3EvalReport:
    """Comprehensive evaluation metrics for Hit@3 and negative rejection."""

    total_positive_queries: int
    hits_at_3: int
    hit_rate_at_3: float
    metadata_complete_ratio: float
    total_negative_queries: int
    negative_rejected: int
    negative_rejection_rate: float
    details: list[dict[str, Any]] = field(default_factory=list)
