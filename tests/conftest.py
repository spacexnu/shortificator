import pytest

from shortificator.models import Segment, ShortCandidate


def make_words(*spans: tuple[str, float, float]) -> list[dict]:
    return [{"word": w, "start": s, "end": e} for w, s, e in spans]


@pytest.fixture
def segments() -> list[Segment]:
    return [
        Segment(
            start=0.0,
            end=3.0,
            text="o gato subiu",
            words=make_words(("o", 0.0, 0.5), ("gato", 0.5, 1.5), ("subiu", 1.5, 3.0)),
        ),
        Segment(
            start=5.0,
            end=8.0,
            text="no telhado quente",
            words=make_words(("no", 5.0, 5.5), ("telhado", 5.5, 6.8), ("quente", 6.8, 8.0)),
        ),
    ]


@pytest.fixture
def candidate() -> ShortCandidate:
    return ShortCandidate(start=10.0, end=45.0, hook="abertura forte", reason="porque sim", score=9)
