"""Clip-selection analysis: prompt building, LLM calls, and dedup heuristics."""

from .llm import analyze_with_llm

__all__ = ["analyze_with_llm"]
