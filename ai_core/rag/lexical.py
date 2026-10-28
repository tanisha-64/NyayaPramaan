"""Small in-process lexical retrieval primitives for hybrid chunk search."""

from collections import Counter
from collections.abc import Iterable, Sequence
from math import log
import re
from typing import Hashable


# A token is a maximal run of chars that are either plain \w (letters/digits in any script
# that Python's regex engine already treats as word chars) OR anywhere in the Devanagari
# Unicode block (U+0900-U+097F). That block also covers vowel signs (matras) and the virama,
# which \w alone does NOT count as word characters -- without this, "न्याय" was being split
# into separate tokens at every matra/virama.
_TOKEN_PATTERN = re.compile(r"(?:[^\W_]|[\u0900-\u097F])+", re.UNICODE)


def tokens(text: str) -> list[str]:
    """Return lowercase alphanumeric tokens, preserving Unicode letters and digits."""
    return _TOKEN_PATTERN.findall((text or "").lower())


class Bm25:
    """BM25 index over a fixed collection of text documents."""

    def __init__(self, documents: Iterable[str], k1: float = 1.5, b: float = 0.75):
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")

        self._documents = [tokens(document) for document in documents]
        self._k1 = k1
        self._b = b
        self._lengths = [len(document) for document in self._documents]
        self._average_length = sum(self._lengths) / len(self._lengths) if self._lengths else 0.0
        self._document_frequency: Counter[str] = Counter(
            term for document in self._documents for term in set(document)
        )

    def scores(self, query: str) -> tuple[list[float], list[float]]:
        """Return one BM25 score and query-term coverage value per indexed document."""
        query_terms = set(tokens(query))
        if not query_terms or not self._documents:
            return [0.0] * len(self._documents), [0.0] * len(self._documents)

        document_count = len(self._documents)
        scores: list[float] = []
        coverage: list[float] = []
        for document, length in zip(self._documents, self._lengths):
            term_frequency = Counter(document)
            present_terms = query_terms.intersection(term_frequency)
            coverage.append(len(present_terms) / len(query_terms))

            score = 0.0
            for term in present_terms:
                frequency = term_frequency[term]
                document_frequency = self._document_frequency[term]
                inverse_frequency = log(
                    1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                length_normalizer = (
                    1 - self._b + self._b * length / self._average_length
                    if self._average_length
                    else 1.0
                )
                score += inverse_frequency * (
                    frequency * (self._k1 + 1) / (frequency + self._k1 * length_normalizer)
                )
            scores.append(score)
        return scores, coverage


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Hashable]],
    weights: Sequence[float] | None = None,
    k: int = 60,
) -> dict[Hashable, float]:
    """Combine ranked identifiers using weighted reciprocal-rank fusion.
    An item appearing in several rankings keeps its single BEST (highest) weighted score
    rather than summing across rankings -- this avoids double-counting the same result
    just because both retrieval strategies happened to surface it."""
    if k < 0:
        raise ValueError("k must be non-negative")
    if weights is None:
        weights = [1.0] * len(rankings)
    elif len(weights) != len(rankings):
        raise ValueError("weights must have one value per ranking")

    fused: dict[Hashable, float] = {}
    for ranking, weight in zip(rankings, weights):
        seen: set[Hashable] = set()
        for rank, item in enumerate(ranking, start=1):
            if item in seen:
                continue
            seen.add(item)
            score = weight / (k + rank)
            fused[item] = max(fused.get(item, 0.0), score)
    return fused