"""Shared result shapes for Glance AI analysis.

These types describe the current demo API. They are not model weights
and do not imply that real inference is implemented.
"""

from typing import Any, TypedDict


class DemoModuleResult(TypedDict, total=False):
    module: str
    demo: bool
    status: str
    message: str
    score: None
    label: None


class AnalysisResult(TypedDict, total=False):
    filename: str
    verdict: str
    confidence: int
    risk_level: str
    message: str
    demo: bool
    details: dict[str, Any]
