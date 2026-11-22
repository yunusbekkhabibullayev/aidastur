from typing import Optional
from pydantic import BaseModel
from .schemas import VerdictEnum


class BenchmarkItem(BaseModel):
    id: str
    claim: str
    expected_verdict: VerdictEnum
    category: str  # politics, science, health, technology, society, education, etc.
    language: str  # uz, ru, en
    known_source: Optional[str] = None
    expected_explanation: Optional[str] = None


class EvaluationMetrics(BaseModel):
    total_samples: int
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    per_class_metrics: dict
    confusion_matrix: dict

