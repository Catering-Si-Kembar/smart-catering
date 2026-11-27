from __future__ import annotations

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from app.chroma.chunker import load_and_chunk_knowledge_dir
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
    KnowledgeChunkRecord,
)
from app.config import AppSettings
from app.rag.schemas import KnowledgeChunk


class VectorStoreAdapter(Protocol):
    """Protocol defining vector store backend capabilities."""

    def collection_exists(self) -> bool: ...

    def count(self) -> int: ...

    def upsert_chunks(self, chunks: Sequence[KnowledgeChunkRecord]) -> int: ...

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 3,
        category: str | None = None,
        max_distance: float = 0.65,
    ) -> list[ChromaQueryHit]: ...


class InMemoryVectorStoreAdapter:
    """Pure-Python in-memory vector store implementation for isolated test/CI execution."""

    def __init__(
        self,
        collection_name: str = "catering_knowledge",
        embedding_function: LocalHashEmbeddingFunction | None = None,
    ) -> None:
        self.collection_name = collection_name
        self.embedding_function = (
            embedding_function if embedding_function is not None else LocalHashEmbeddingFunction()
        )
        self._chunks: dict[str, KnowledgeChunkRecord] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._initialized: bool = False

    def collection_exists(self) -> bool:
        return self._initialized

    def count(self) -> int:
        return len(self._chunks)

    def upsert_chunks(self, chunks: Sequence[KnowledgeChunkRecord]) -> int:
        self._initialized = True
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_function(texts)
        for chunk, emb in zip(chunks, embeddings, strict=True):
            self._chunks[chunk.chunk_id] = chunk
            self._embeddings[chunk.chunk_id] = emb
        return len(chunks)

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 3,
        category: str | None = None,
        max_distance: float = 0.65,
    ) -> list[ChromaQueryHit]:
        if not self.collection_exists():
            raise ChromaCollectionNotFoundError(
                f"Collection '{self.collection_name}' does not exist. Run ingest first."
            )

        query_emb = self.embedding_function([query_text])[0]
        scored_hits: list[ChromaQueryHit] = []

        for chunk_id, chunk in self._chunks.items():
            meta = chunk.metadata
            if not (meta.is_verified is True and meta.validation_status == "verified"):
                continue
            if category is not None and meta.category != category:
                continue

            emb = self._embeddings[chunk_id]
            dist = cosine_distance(query_emb, emb)
            if dist <= max_distance:
                scored_hits.append(
                    ChromaQueryHit(
                        chunk_id=chunk.chunk_id,
                        content=chunk.content,
                        distance=round(dist, 4),
                        metadata=meta,
                    )
                )

        scored_hits.sort(key=lambda hit: hit.distance)
        return scored_hits[:top_k]


class ChromaHttpVectorStoreAdapter:
    """HTTP client vector store adapter connecting to remote/local ChromaDB with lazy import."""

    def __init__(
        self,
        chroma_url: str,
        collection_name: str = "catering_knowledge",
        embedding_function: LocalHashEmbeddingFunction | None = None,
    ) -> None:
        self.chroma_url = chroma_url
        self.collection_name = collection_name
        self.embedding_function = (
            embedding_function
            if embedding_function is not None
            else LocalHashEmbeddingFunction(dim=DEFAULT_EMBEDDING_DIM)
        )

        parsed = urlparse(chroma_url)
        self.ssl_enabled: bool = parsed.scheme.lower() == "https"
        self.host: str = parsed.hostname or "127.0.0.1"
        if parsed.port is not None:
            self.port: int = parsed.port
        else:
            self.port = 443 if self.ssl_enabled else 8000

        self._client: Any = None
        self._collection: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            chromadb = importlib.import_module("chromadb")
        except Exception as exc:
            raise ChromaUnavailableError(
                f"ChromaDB library is not installed: {exc}. Install with [rag] extra."
            ) from exc

        try:
            self._client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                ssl=self.ssl_enabled,
            )
            return self._client
        except Exception as exc:
            raise ChromaUnavailableError(
                f"Failed to connect to ChromaDB at {self.host}:{self.port}: {exc}"
            ) from exc

    def _get_collection(self, create_if_missing: bool = False) -> Any:
        if self._collection is not None:
            return self._collection

        client = self._get_client()
        try:
            if create_if_missing:
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                self._collection = client.get_collection(name=self.collection_name)
            return self._collection
        except Exception as exc:
            err_name = type(exc).__name__
            if "InvalidCollection" in err_name or "NotFoundError" in err_name:
                raise ChromaCollectionNotFoundError(
                    f"Collection '{self.collection_name}' not found in ChromaDB."
                ) from exc
            raise ChromaUnavailableError(f"ChromaDB collection access failed: {exc}") from exc

    def collection_exists(self) -> bool:
        client = self._get_client()
        try:
            collections = client.list_collections()
            return any(c.name == self.collection_name for c in collections)
        except Exception as exc:
            raise ChromaUnavailableError(f"Failed to list collections: {exc}") from exc

    def count(self) -> int:
        col = self._get_collection(create_if_missing=False)
        try:
            return int(col.count())
        except Exception as exc:
            raise ChromaUnavailableError(f"Failed to count collection items: {exc}") from exc

    def upsert_chunks(self, chunks: Sequence[KnowledgeChunkRecord]) -> int:
        if not chunks:
            return 0
        col = self._get_collection(create_if_missing=True)
        try:
            ids = [chunk.chunk_id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas: list[dict[str, Any]] = [
                {
                    "doc_id": chunk.metadata.doc_id,
                    "source": chunk.metadata.source,
                    "category": chunk.metadata.category,
                    "version": chunk.metadata.version,
                    "validated_at": chunk.metadata.validated_at,
                    "validation_status": chunk.metadata.validation_status,
                    "is_verified": chunk.metadata.is_verified,
                }
                for chunk in chunks
            ]
            embeddings = self.embedding_function(documents)
            col.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )
            return len(chunks)
        except Exception as exc:
            raise ChromaUnavailableError(f"ChromaDB upsert failed: {exc}") from exc

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 3,
        category: str | None = None,
        max_distance: float = 0.65,
    ) -> list[ChromaQueryHit]:
        col = self._get_collection(create_if_missing=False)
        try:
            query_emb = self.embedding_function([query_text])[0]
            where_filter: dict[str, Any] = {
                "$and": [
                    {"is_verified": True},
                    {"validation_status": "verified"},
                ]
            }
            if category is not None:
                where_filter["$and"].append({"category": category})

            results = col.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            hits: list[ChromaQueryHit] = []
            if not results or not results.get("ids") or not results["ids"][0]:
                return hits

            res_ids = results["ids"][0]
            res_docs = results["documents"][0] if results.get("documents") else []
            res_metas = results["metadatas"][0] if results.get("metadatas") else []
            res_dists = results["distances"][0] if results.get("distances") else []

            for idx, chunk_id in enumerate(res_ids):
                dist = float(res_dists[idx]) if idx < len(res_dists) else 0.0
                if dist > max_distance:
                    continue
                meta_dict = res_metas[idx] if idx < len(res_metas) else {}
                meta = ChunkMetadataRecord(
                    doc_id=str(meta_dict.get("doc_id", "")),
                    source=str(meta_dict.get("source", "")),
                    category=str(meta_dict.get("category", "")),
                    version=str(meta_dict.get("version", "")),
                    validated_at=str(meta_dict.get("validated_at", "")),
                    validation_status=str(meta_dict.get("validation_status", "")),
                    is_verified=bool(meta_dict.get("is_verified", False)),
                )
                doc_content = str(res_docs[idx]) if idx < len(res_docs) else ""
                hits.append(
                    ChromaQueryHit(
                        chunk_id=chunk_id,
                        content=doc_content,
                        distance=round(dist, 4),
                        metadata=meta,
                    )
                )

            return hits
        except ChromaCollectionNotFoundError:
            raise
        except Exception as exc:
            raise ChromaUnavailableError(f"ChromaDB query execution failed: {exc}") from exc


class ChromaKnowledgeService:
    """Service facade providing verified knowledge base indexing and semantic retrieval."""

    def __init__(
        self,
        *,
        adapter: VectorStoreAdapter,
        default_knowledge_dir: Path,
        default_max_distance: float = 0.65,
    ) -> None:
        self._adapter = adapter
        self.default_knowledge_dir = default_knowledge_dir
        self.default_max_distance = default_max_distance

    @property
    def adapter(self) -> VectorStoreAdapter:
        return self._adapter

    def ingest_directory(self, knowledge_dir: Path | None = None) -> ChromaIngestSummary:
        target_dir = knowledge_dir if knowledge_dir is not None else self.default_knowledge_dir
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Knowledge directory not found: {target_dir}")

        chunks = load_and_chunk_knowledge_dir(target_dir)
        files_processed = len({chunk.metadata.source for chunk in chunks})
        upserted = self._adapter.upsert_chunks(chunks)
        total = self._adapter.count()
        coll_name = getattr(self._adapter, "collection_name", "catering_knowledge")

        return ChromaIngestSummary(
            collection_name=coll_name,
            files_processed=files_processed,
            chunks_upserted=upserted,
            total_chunks=total,
            idempotent=True,
        )

    def query(
        self,
        query_text: str,
        *,
        top_k: int = 3,
        category: str | None = None,
        max_distance: float | None = None,
    ) -> list[ChromaQueryHit]:
        stripped = query_text.strip()
        if not stripped:
            raise ValueError("Query text cannot be blank.")

        dist_threshold = max_distance if max_distance is not None else self.default_max_distance
        return self._adapter.query(
            stripped,
            top_k=top_k,
            category=category,
            max_distance=dist_threshold,
        )

    async def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        category: str | None = None,
    ) -> list[KnowledgeChunk]:
        hits = self.query(query, top_k=top_k, category=category)
        return [
            KnowledgeChunk(
                chunk_id=hit.chunk_id,
                content=hit.content,
                distance=hit.distance,
                source=hit.metadata.source,
                category=hit.metadata.category,
                version=hit.metadata.version,
                validated_at=hit.metadata.validated_at,
                validation_status="verified",
                is_verified=hit.metadata.is_verified,
            )
            for hit in hits
        ]


def build_default_chroma_service(settings: AppSettings) -> ChromaKnowledgeService:
    """Factory creating production ChromaKnowledgeService using AppSettings configuration."""
    repo_root = Path(__file__).resolve().parents[4]
    default_dir = repo_root / "data" / "knowledge"
    adapter = ChromaHttpVectorStoreAdapter(
        chroma_url=settings.chroma_url,
        collection_name=settings.chroma_collection_name,
    )
    return ChromaKnowledgeService(
        adapter=adapter,
        default_knowledge_dir=default_dir,
    )
