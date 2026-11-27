from __future__ import annotations

import re
from pathlib import Path

from app.chroma.schemas import ChunkMetadataRecord, KnowledgeChunkRecord


def parse_markdown_document(path: Path) -> tuple[ChunkMetadataRecord, str]:
    """Parse YAML frontmatter and extract body from a curated markdown file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        raise ValueError(f"File {path.name} is missing YAML frontmatter opening '---'")

    closing_idx = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            closing_idx = idx
            break

    if closing_idx == -1:
        raise ValueError(f"File {path.name} is missing YAML frontmatter closing '---'")

    raw_meta: dict[str, str] = {}
    for line in lines[1:closing_idx]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, val = stripped.split(":", 1)
        k = key.strip()
        v = val.strip().strip("'\"")
        raw_meta[k] = v

    required_fields = (
        "doc_id",
        "source",
        "category",
        "version",
        "validated_at",
        "validation_status",
        "is_verified",
    )
    for field_name in required_fields:
        if field_name not in raw_meta:
            raise ValueError(f"Missing required metadata field '{field_name}' in {path.name}")

    is_verified_bool = raw_meta["is_verified"].lower() in {"true", "1", "yes"}

    metadata = ChunkMetadataRecord(
        doc_id=raw_meta["doc_id"],
        source=raw_meta["source"],
        category=raw_meta["category"],
        version=raw_meta["version"],
        validated_at=raw_meta["validated_at"],
        validation_status=raw_meta["validation_status"],
        is_verified=is_verified_bool,
    )

    body = "\n".join(lines[closing_idx + 1 :]).strip()
    return metadata, body


def chunk_markdown_body(
    body: str,
    *,
    min_chars: int = 300,
    max_chars: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split markdown body into chunks of 80-650 characters preserving heading context."""
    if not body.strip():
        return []

    # Split by level 2 headings
    sections = re.split(r"(?m)^(?=##\s+)", body)
    raw_chunks: list[str] = []

    for sec in sections:
        sec_clean = sec.strip()
        if not sec_clean or sec_clean.startswith("# "):
            # Top-level title without ## content
            continue

        if len(sec_clean) <= max_chars:
            raw_chunks.append(sec_clean)
        else:
            # Split section into paragraphs
            paragraphs = [p.strip() for p in sec_clean.split("\n\n") if p.strip()]
            if len(paragraphs) <= 1:
                # Long single paragraph, split by sentences or sliding window
                heading = ""
                content = sec_clean
                if sec_clean.startswith("##"):
                    first_nl = sec_clean.find("\n")
                    if first_nl != -1:
                        heading = sec_clean[:first_nl].strip()
                        content = sec_clean[first_nl:].strip()

                start = 0
                step = max_chars - overlap
                while start < len(content):
                    chunk_slice = content[start : start + max_chars].strip()
                    if heading:
                        chunk_text = f"{heading}\n{chunk_slice}"
                    else:
                        chunk_text = chunk_slice
                    raw_chunks.append(chunk_text)
                    start += step
            else:
                current_chunk: list[str] = []
                current_len = 0
                heading = paragraphs[0] if paragraphs[0].startswith("##") else ""

                for p in paragraphs:
                    p_len = len(p)
                    if current_len + p_len + 2 > max_chars and current_chunk:
                        chunk_text = "\n\n".join(current_chunk).strip()
                        raw_chunks.append(chunk_text)
                        # Carry over heading for context
                        current_chunk = [heading, p] if heading and not p.startswith("##") else [p]
                        current_len = sum(len(x) for x in current_chunk) + len(current_chunk)
                    else:
                        current_chunk.append(p)
                        current_len += p_len + 2

                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk).strip()
                    raw_chunks.append(chunk_text)

    # Post-process: ensure every chunk is at least 80 chars by merging tiny chunks
    processed_chunks: list[str] = []
    buffer = ""

    for chunk in raw_chunks:
        if buffer:
            combined = f"{buffer}\n\n{chunk}".strip()
            if len(combined) <= 650:
                buffer = combined
                continue
            else:
                processed_chunks.append(buffer)
                buffer = ""

        if len(chunk) < 80:
            buffer = chunk
        else:
            processed_chunks.append(chunk)

    if buffer:
        if processed_chunks and len(processed_chunks[-1]) + len(buffer) + 2 <= 650:
            processed_chunks[-1] = f"{processed_chunks[-1]}\n\n{buffer}".strip()
        else:
            processed_chunks.append(buffer)

    return processed_chunks


def load_and_chunk_knowledge_dir(knowledge_dir: Path) -> list[KnowledgeChunkRecord]:
    """Load, validate, and chunk all curated markdown files in directory."""
    if not knowledge_dir.exists() or not knowledge_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {knowledge_dir}")

    records: list[KnowledgeChunkRecord] = []
    files = sorted(knowledge_dir.glob("*.md"))

    for file_path in files:
        if file_path.name.lower() == "readme.md":
            continue

        metadata, body = parse_markdown_document(file_path)
        chunks = chunk_markdown_body(body)

        for idx, chunk_content in enumerate(chunks):
            chunk_id = f"{metadata.doc_id}_c{idx}"
            records.append(
                KnowledgeChunkRecord(
                    chunk_id=chunk_id,
                    content=chunk_content,
                    metadata=metadata,
                )
            )

    return records
