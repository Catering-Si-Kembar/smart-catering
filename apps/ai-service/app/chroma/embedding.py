from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Final

DEFAULT_EMBEDDING_DIM: Final[int] = 384

CATERING_SYNONYM_MAP: Final[dict[str, tuple[str, ...]]] = {
    "dp": ("uang", "muka", "down", "payment", "dp"),
    "down": ("dp", "uang", "muka"),
    "payment": ("pembayaran", "tagihan", "bayar", "transfer", "pelunasan"),
    "pembayaran": ("payment", "transfer", "lunas", "pelunasan", "tagihan", "dp"),
    "katering": ("catering", "katering", "konsumsi"),
    "catering": ("catering", "katering", "konsumsi"),
    "order": ("pesanan", "pemesanan", "order", "porsi"),
    "pesanan": ("order", "pemesanan", "pesan", "porsi"),
    "pemesanan": ("order", "pesanan", "pesan", "porsi"),
    "ongkir": ("ongkos", "kirim", "pengantaran", "antar", "ongkir"),
    "pengantaran": ("kirim", "antar", "pengiriman", "delivery"),
    "revisi": ("perubahan", "reschedule", "ubah", "ganti", "revisi"),
    "batal": ("pembatalan", "cancel", "refund", "pengembalian"),
    "pembatalan": ("batal", "cancel", "refund", "pengembalian"),
    "refund": ("pengembalian", "dana", "batal", "pembatalan"),
    "tumpeng": ("tumpeng", "kuning", "liwet", "tampah"),
    "snack": ("snack", "kue", "box"),
    "prasmanan": ("buffet", "prasmanan", "silver", "gold"),
    "sop": ("standar", "operasional", "prosedur", "sop"),
    "lead": ("lead", "time", "waktu", "tenggat", "jadwal"),
}


def cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute cosine distance between two L2-normalized vectors in [0.0, 2.0]."""
    if len(a) != len(b):
        raise ValueError(f"Vector dimension mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return max(0.0, min(2.0, 1.0 - dot))


class LocalHashEmbeddingFunction:
    """Deterministic pure-Python feature hashing embedding function for offline CI/test."""

    def __init__(self, dim: int = DEFAULT_EMBEDDING_DIM) -> None:
        if dim <= 0:
            raise ValueError(f"Embedding dimension must be positive, got {dim}")
        self.dim = dim

    def embed_text(self, text: str) -> list[float]:
        cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        raw_words = [w for w in cleaned.split() if len(w) >= 2]
        if not raw_words:
            return [0.0] * self.dim

        expanded_words: list[str] = []
        for word in raw_words:
            expanded_words.append(word)
            synonyms = CATERING_SYNONYM_MAP.get(word)
            if synonyms:
                expanded_words.extend(synonyms)

        vec = [0.0] * self.dim

        # Unigrams (weight 2.0)
        for w in expanded_words:
            digest = hashlib.blake2b(f"u:{w}".encode(), digest_size=8).digest()
            val = int.from_bytes(digest, "big")
            sign = 1.0 if ((val >> 16) & 1) == 0 else -1.0
            vec[val % self.dim] += sign * 2.0

        # Bigrams (weight 1.5)
        for i in range(len(expanded_words) - 1):
            bg = f"b:{expanded_words[i]}_{expanded_words[i + 1]}"
            digest = hashlib.blake2b(bg.encode("utf-8"), digest_size=8).digest()
            val = int.from_bytes(digest, "big")
            sign = 1.0 if ((val >> 16) & 1) == 0 else -1.0
            vec[val % self.dim] += sign * 1.5

        # Character 3-grams (weight 0.6)
        for w in raw_words:
            for j in range(len(w) - 2):
                c3 = f"c:{w[j : j + 3]}"
                digest = hashlib.blake2b(c3.encode("utf-8"), digest_size=8).digest()
                val = int.from_bytes(digest, "big")
                sign = 1.0 if ((val >> 16) & 1) == 0 else -1.0
                vec[val % self.dim] += sign * 0.6

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0.0:
            return [x / norm for x in vec]
        return [0.0] * self.dim

    def __call__(self, input: Sequence[str]) -> list[list[float]]:
        return [self.embed_text(item) for item in input]
