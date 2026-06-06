"""Core data structures shared across the pipeline stages."""

from dataclasses import dataclass, field


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list = field(default_factory=list)  # list of {"word", "start", "end"}


@dataclass
class ShortCandidate:
    start: float
    end: float
    hook: str
    reason: str
    score: int = 0
