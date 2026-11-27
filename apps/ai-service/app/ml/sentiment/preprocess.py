"""Indonesian text preprocessing utilities for customer feedback sentiment classification."""

from __future__ import annotations

import re

# Indonesian review slang and colloquial word normalization for catering domain
_ABBREVIATIONS: dict[str, str] = {
    "recommended": "rekomendasi",
    "rekomen": "rekomendasi",
    "banget": "sangat",
    "bgtu": "begitu",
    "bbrp": "beberapa",
    "mknan": "makanan",
    "nggak": "tidak",
    "mantul": "mantap",
    "mantap": "mantap",
    "bgt": "sangat",
    "gak": "tidak",
    "ngga": "tidak",
    "gk": "tidak",
    "ga": "tidak",
    "tp": "tetapi",
    "tapi": "tetapi",
    "dtg": "datang",
    "yg": "yang",
    "dgn": "dengan",
    "udh": "sudah",
    "udah": "sudah",
    "blm": "belum",
    "krn": "karena",
    "trs": "terus",
    "mkn": "makanan",
    "hrg": "harga",
    "sy": "saya",
}

_ABBREVIATION_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(k) for k in sorted(_ABBREVIATIONS.keys(), key=len, reverse=True))
    + r")\b"
)
_HYPHEN_SLASH_PATTERN = re.compile(r"[-/]")
_PUNCTUATION_PATTERN = re.compile(r"[^0-9a-zA-Z\s]")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TOKEN_PATTERN = re.compile(r"(?u)\b\w+\b")


def _replace_abbreviation(match: re.Match[str]) -> str:
    return _ABBREVIATIONS.get(match.group(1), match.group(1))


def normalize_sentiment_text(text: str) -> str:
    """Normalize Indonesian customer feedback text for sentiment classification.

    Applies lowercase folding, converts hyphens and slashes to spaces, strips non-alphanumeric
    punctuation, normalizes Indonesian slang and review abbreviations, and collapses extra spaces.
    The transformation is deterministic and idempotent.
    """
    if not text:
        return ""

    lowered = text.lower()
    spaced = _HYPHEN_SLASH_PATTERN.sub(" ", lowered)
    stripped = _PUNCTUATION_PATTERN.sub(" ", spaced)
    expanded = _ABBREVIATION_PATTERN.sub(_replace_abbreviation, stripped)
    return _WHITESPACE_PATTERN.sub(" ", expanded).strip()


def tokenize_sentiment_text(text: str) -> list[str]:
    """Tokenize Indonesian customer feedback text into alphanumeric tokens."""
    normalized = normalize_sentiment_text(text)
    return _TOKEN_PATTERN.findall(normalized)
