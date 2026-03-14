"""Phase 1 matching: Filter → Score → MMR → Explain."""
from autoquery.matching.phase1.pipeline import match, persist_results, ALGORITHM_VERSION

__all__ = ["match", "persist_results", "ALGORITHM_VERSION"]
