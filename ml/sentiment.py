"""VADER-based sentiment analysis for study session notes.

VADER is rule-based and fast, with no model download required, which makes it
a clean fit for short, informal text like study notes ("phone kept buzzing",
"finally cracked recursion", "tired but pushed through").

Public API:
- score_text(text) -> float in [-1.0, 1.0]
- label_from_score(score) -> "positive" | "neutral" | "negative"
- batch_score(texts) -> list[float]
"""

from functools import lru_cache

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@lru_cache(maxsize=1)
def _analyzer():
    return SentimentIntensityAnalyzer()


def score_text(text):
    """Return VADER compound score in [-1, 1]. Empty/None returns 0.0."""
    if not text or not text.strip():
        return 0.0
    return float(_analyzer().polarity_scores(text)["compound"])


def label_from_score(score):
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"


def batch_score(texts):
    return [score_text(text) for text in texts]
