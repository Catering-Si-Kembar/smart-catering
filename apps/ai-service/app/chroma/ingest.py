from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.chroma.client import (
    ChromaHttpVectorStoreAdapter,
    ChromaKnowledgeService,
    InMemoryVectorStoreAdapter,
)
from app.chroma.schemas import HitAt3EvalReport
from app.rag.schemas import RetrievalEvalSample

DEFAULT_EVAL_SAMPLES: tuple[RetrievalEvalSample, ...] = (
    RetrievalEvalSample(
        query="Pilihan menu utama paket nasi box ayam bakar madu dan rendang daging",
        expected_sources=["menus.md"],
        category="menu",
    ),
    RetrievalEvalSample(
        query="Ketentuan porsi paket tumpeng kuning komplit dan nasi liwet tampah",
        expected_sources=["menus.md"],
        category="menu",
    ),
    RetrievalEvalSample(
        query="Kombinasi kue snack box tradisional dan modern untuk seminar",
        expected_sources=["menus.md"],
        category="menu",
    ),
    RetrievalEvalSample(
        query="Menu prasmanan silver dan gold untuk perayaan pernikahan",
        expected_sources=["menus.md"],
        category="menu",
    ),
    RetrievalEvalSample(
        query="Berapa minimal order pemesanan paket nasi box dan snack box?",
        expected_sources=["faq.md"],
        category="faq",
    ),
    RetrievalEvalSample(
        query="Batas waktu pemesanan lead time katering sebelum hari H acara",
        expected_sources=["faq.md"],
        category="faq",
    ),
    RetrievalEvalSample(
        query="Area wilayah layanan pengantaran katering Bandung dan Cimahi",
        expected_sources=["faq.md"],
        category="faq",
    ),
    RetrievalEvalSample(
        query="Permintaan khusus menu katering halal vegetarian dan alergi makanan",
        expected_sources=["faq.md"],
        category="faq",
    ),
    RetrievalEvalSample(
        query="SOP pencatatan dan validasi pesanan masuk oleh staf admin",
        expected_sources=["sop.md"],
        category="sop",
    ),
    RetrievalEvalSample(
        query="SOP persiapan dapur dan pengecekan stok bahan baku H-1",
        expected_sources=["sop.md"],
        category="sop",
    ),
    RetrievalEvalSample(
        query="SOP standar kebersihan penutup rambut dan pengemasan food safety",
        expected_sources=["sop.md"],
        category="sop",
    ),
    RetrievalEvalSample(
        query="SOP kedatangan pengantaran kurir dan penanganan keluhan pelanggan",
        expected_sources=["sop.md"],
        category="sop",
    ),
    RetrievalEvalSample(
        query="Berapa ketentuan minimal uang muka DP pembayaran pesanan katering?",
        expected_sources=["payment_policy.md"],
        category="payment",
    ),
    RetrievalEvalSample(
        query="Batas waktu pelunasan sisa tagihan pembayaran katering H-1",
        expected_sources=["payment_policy.md"],
        category="payment",
    ),
    RetrievalEvalSample(
        query="Kebijakan pengembalian dana refund dan reschedule pembatalan pesanan",
        expected_sources=["payment_policy.md"],
        category="payment",
    ),
    RetrievalEvalSample(
        query="Prosedur penerbitan invoice digital resmi dan bukti transfer",
        expected_sources=["payment_policy.md"],
        category="payment",
    ),
)

DEFAULT_NEGATIVE_QUERIES: tuple[str, ...] = (
    "Bagaimana cara konfigurasi kernel Linux Ubuntu di server AWS?",
    "Resep cara membuat sushi salmon segar khas Jepang",
    "Jadwal keberangkatan kereta api Argo Parahyangan Bandung Jakarta",
    "Berapa kurs nilai tukar mata uang dolar Amerika ke rupiah hari ini?",
)


def evaluate_knowledge_base_hit_at_3(
    service: ChromaKnowledgeService,
    samples: tuple[RetrievalEvalSample, ...] = DEFAULT_EVAL_SAMPLES,
    negative_queries: tuple[str, ...] = DEFAULT_NEGATIVE_QUERIES,
) -> HitAt3EvalReport:
    """Evaluate Hit@3 retrieval rate, metadata completeness, and negative rejection."""
    if not samples:
        return HitAt3EvalReport(
            total_positive_queries=0,
            hits_at_3=0,
            hit_rate_at_3=0.0,
            metadata_complete_ratio=0.0,
            total_negative_queries=len(negative_queries),
            negative_rejected=0,
            negative_rejection_rate=0.0,
        )

    hits_at_3 = 0
    total_retrieved_chunks = 0
    complete_metadata_chunks = 0
    details: list[dict[str, Any]] = []

    for sample in samples:
        hits = service.query(sample.query, top_k=3, category=sample.category)
        expected_lower = {s.lower() for s in sample.expected_sources}
        retrieved_sources = [hit.metadata.source.lower() for hit in hits[:3]]

        matched = bool(expected_lower.intersection(retrieved_sources))
        if matched:
            hits_at_3 += 1

        for hit in hits[:3]:
            total_retrieved_chunks += 1
            meta = hit.metadata
            if (
                bool(meta.source)
                and bool(meta.version)
                and bool(meta.validated_at)
                and meta.validation_status == "verified"
                and meta.is_verified is True
            ):
                complete_metadata_chunks += 1

        details.append(
            {
                "query": sample.query,
                "expected": list(sample.expected_sources),
                "retrieved": [h.metadata.source for h in hits[:3]],
                "matched": matched,
            }
        )

    hit_rate = round(hits_at_3 / len(samples), 4)
    metadata_ratio = (
        round(complete_metadata_chunks / total_retrieved_chunks, 4)
        if total_retrieved_chunks > 0
        else 0.0
    )

    neg_rejected = 0
    for neg_query in negative_queries:
        neg_hits = service.query(neg_query, top_k=3)
        if len(neg_hits) == 0:
            neg_rejected += 1

    neg_rejection_rate = round(neg_rejected / len(negative_queries), 4) if negative_queries else 1.0

    return HitAt3EvalReport(
        total_positive_queries=len(samples),
        hits_at_3=hits_at_3,
        hit_rate_at_3=hit_rate,
        metadata_complete_ratio=metadata_ratio,
        total_negative_queries=len(negative_queries),
        negative_rejected=neg_rejected,
        negative_rejection_rate=neg_rejection_rate,
        details=details,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest curated knowledge base into ChromaDB and evaluate Hit@3."
    )
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=None,
        help="Path to directory containing knowledge markdown files.",
    )
    parser.add_argument(
        "--chroma-url",
        type=str,
        default="http://127.0.0.1:8000",
        help="ChromaDB service URL.",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default="catering_knowledge",
        help="ChromaDB collection name.",
    )
    parser.add_argument(
        "--in-memory",
        action="store_true",
        help="Use pure-Python InMemoryVectorStoreAdapter instead of HTTP client.",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run Hit@3 and negative rejection evaluation after ingest.",
    )

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    knowledge_dir = args.knowledge_dir or (repo_root / "data" / "knowledge")

    from app.chroma.client import VectorStoreAdapter

    adapter: VectorStoreAdapter
    if args.in_memory:
        adapter = InMemoryVectorStoreAdapter(collection_name=args.collection_name)
    else:
        adapter = ChromaHttpVectorStoreAdapter(
            chroma_url=args.chroma_url,
            collection_name=args.collection_name,
        )

    service = ChromaKnowledgeService(
        adapter=adapter,
        default_knowledge_dir=knowledge_dir,
    )

    # Ingest run 1
    summary1 = service.ingest_directory(knowledge_dir)
    # Ingest run 2 (prove idempotency)
    summary2 = service.ingest_directory(knowledge_dir)

    print(f"Ingest #1: {summary1.chunks_upserted} chunks from {summary1.files_processed} files.")
    print(f"Ingest #2: {summary2.chunks_upserted} chunks, total {summary2.total_chunks} chunks.")
    print(f"Idempotent: {summary2.idempotent}")

    if args.eval:
        report = evaluate_knowledge_base_hit_at_3(service)
        print("\n--- Hit@3 Evaluation Summary ---")
        eval_dict = {
            "total_positive_queries": report.total_positive_queries,
            "hits_at_3": report.hits_at_3,
            "hit_rate_at_3": report.hit_rate_at_3,
            "metadata_complete_ratio": report.metadata_complete_ratio,
            "total_negative_queries": report.total_negative_queries,
            "negative_rejected": report.negative_rejected,
            "negative_rejection_rate": report.negative_rejection_rate,
        }
        print(json.dumps(eval_dict, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
