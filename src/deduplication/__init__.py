"""Contact deduplication system."""

from src.deduplication.dedup_engine import (
    DeduplicationEngine,
    DuplicateMatch,
    MergeResult,
    DeduplicationRule,
    MatchConfidence,
    get_dedup_engine,
)

__all__ = [
    "DeduplicationEngine",
    "DuplicateMatch",
    "MergeResult",
    "DeduplicationRule",
    "MatchConfidence",
    "get_dedup_engine",
]
