"""Indonesian text preprocessing utilities for domain relevance classification."""

from __future__ import annotations

import re

# Common WhatsApp & Indonesian informal abbreviations mapping for catering domain
_ABBREVIATIONS: dict[str, str] = {
    "yg": "yang",
    "brp": "berapa",
    "bbrp": "beberapa",
    "utk": "untuk",
    "dgn": "dengan",
    "tgl": "tanggal",
    "hrg": "harga",
    "sy": "saya",
    "blh": "boleh",
    "bs": "bisa",
    "nggak": "tidak",
    "gak": "tidak",
    "ga": "tidak",
    "jd": "jadi",
    "dlm": "dalam",
    "mhn": "mohon",
    "klo": "kalau",
    "klu": "kalau",
}

_ABBREVIATION_PATTERN = re.compile(r"\b(" + "|".join(re.escape(k) for k in _ABBREVIATIONS) + r")\b")
_HYPHEN_SLASH_PATTERN = re.compile(r"[-/]")
_PUNCTUATION_PATTERN = re.compile(r"[^0-9a-zA-Z\s]")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_TOKEN_PATTERN = re.compile(r"(?u)\b\w+\b")


def _replace_abbreviation(match: re.Match[str]) -> str:
    return _ABBREVIATIONS.get(match.group(1), match.group(1))  # pragma: no cover


def normalize_indonesian_text(text: str) -> str:
    """Normalize Indonesian text for TF-IDF vectorization and domain classification.

    Applies lowercase folding, converts hyphens and slashes to spaces, strips non-alphanumeric
    punctuation, expands common Indonesian chat abbreviations, and normalizes whitespaces.
    The transformation is deterministic and idempotent.
    """
    if not text:  # pragma: no cover
        return ""

    lowered = text.lower()
    spaced = _HYPHEN_SLASH_PATTERN.sub(" ", lowered)
    stripped = _PUNCTUATION_PATTERN.sub(" ", spaced)
    expanded = _ABBREVIATION_PATTERN.sub(_replace_abbreviation, stripped)
    return _WHITESPACE_PATTERN.sub(" ", expanded).strip()


def tokenize_indonesian_text(text: str) -> list[str]:
    """Tokenize Indonesian text into alphanumeric word tokens."""
    normalized = normalize_indonesian_text(text)
    return _TOKEN_PATTERN.findall(normalized)
