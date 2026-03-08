"""
7-dimension quality gate for crawled page text.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

try:
    from langdetect import detect as langdetect_detect
    from langdetect.lang_detect_exception import LangDetectException
except ImportError:  # graceful degradation if package missing
    langdetect_detect = None  # type: ignore[assignment]
    LangDetectException = Exception  # type: ignore[assignment,misc]

_THRESHOLD = 0.5


@dataclass
class QualityResult:
    score: float                      # 0.0 - 1.0 composite
    passed: bool                      # score >= 0.5
    issues: list[str] = field(default_factory=list)
    dimensions: dict[str, float] = field(default_factory=dict)


def _score_min_length(text: str) -> float:
    n = len(text)
    if n >= 200:
        return 1.0
    return n / 200.0


def _score_signal_noise(text: str) -> float:
    """word_count / token_count — low ratio = link-heavy/nav-heavy page."""
    tokens = text.split()
    if not tokens:
        return 0.0
    words = [t for t in tokens if re.match(r"[A-Za-z]{2,}", t)]
    return min(len(words) / max(len(tokens), 1), 1.0)


def _score_structure(text: str) -> float:
    """Fraction of 'sentences' (split by . ! ?) that contain >3 words."""
    sentences = re.split(r"[.!?]+", text)
    if not sentences:
        return 0.0
    long_sentences = [s for s in sentences if len(s.split()) > 3]
    return min(len(long_sentences) / max(len(sentences), 1), 1.0)


def _score_noise_level(text: str) -> float:
    """1.0 minus the ratio of special/non-alpha chars — high ratio = ad-heavy."""
    if not text:
        return 0.0
    special = sum(1 for c in text if not c.isalpha() and not c.isspace())
    ratio = special / len(text)
    return max(0.0, 1.0 - ratio)


def _score_encoding(text: str) -> float:
    try:
        text.encode("utf-8").decode("utf-8")
        return 1.0
    except (UnicodeEncodeError, UnicodeDecodeError):
        return 0.0


def _score_language(text: str) -> float:
    if langdetect_detect is None:
        return 0.5  # neutral if library unavailable
    try:
        return 1.0 if langdetect_detect(text) == "en" else 0.0
    except Exception:
        return 0.5  # non-deterministic — neutral on exception


def _score_duplicate(text: str, seen_hashes: set[str]) -> float:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    if digest in seen_hashes:
        return 0.0
    seen_hashes.add(digest)
    return 1.0


def check_quality(text: str, seen_hashes: set[str]) -> QualityResult:
    """
    Score a page across 7 dimensions.  Returns QualityResult with composite
    score, pass/fail flag, failing dimension names, and per-dimension scores.
    """
    dims: dict[str, float] = {
        "min_length": _score_min_length(text),
        "signal_noise": _score_signal_noise(text),
        "structure": _score_structure(text),
        "noise_level": _score_noise_level(text),
        "encoding": _score_encoding(text),
        "language": _score_language(text),
        "duplicate": _score_duplicate(text, seen_hashes),
    }

    composite = sum(dims.values()) / len(dims)
    issues = [name for name, score in dims.items() if score < _THRESHOLD]

    return QualityResult(
        score=composite,
        passed=composite >= _THRESHOLD,
        issues=issues,
        dimensions=dims,
    )
