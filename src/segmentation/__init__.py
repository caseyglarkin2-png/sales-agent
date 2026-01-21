"""Smart contact segmentation engine."""

from src.segmentation.segmentation_engine import (
    SegmentationEngine,
    Segment,
    SegmentRule,
    SegmentMembership,
    RuleOperator,
    get_segmentation_engine,
)

__all__ = [
    "SegmentationEngine",
    "Segment",
    "SegmentRule",
    "SegmentMembership",
    "RuleOperator",
    "get_segmentation_engine",
]
