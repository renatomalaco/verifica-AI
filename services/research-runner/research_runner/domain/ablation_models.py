from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AblationMode(str, Enum):
    HEURISTIC = "heuristic"
    CLASSICAL_NLP = "classical_nlp"
    PURE_VLM = "pure_vlm"
    CASCADE = "cascade"


@dataclass
class SamplePrediction:
    sample_id: str
    expected: str
    predicted: str
    confidence: float
    latency_ms: float
    cost_usd: float
    deciding_stage: str
    is_correct: bool = False

    def __post_init__(self):
        self.is_correct = (self.expected == self.predicted)


@dataclass
class ConfusionMatrix:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0


@dataclass
class MetricsReport:
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    f2_score: float
    confusion_matrix: ConfusionMatrix
    ece: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cost_per_1k_usd: float
    cost_per_1k_brl: float
    total_samples: int
    correct_samples: int


@dataclass
class ModeEvaluation:
    mode: AblationMode
    metrics: MetricsReport
    predictions: List[SamplePrediction] = field(default_factory=list)
    stage_breakdown: Dict[str, int] = field(default_factory=dict)
    status: str = "executed"  # "executed" or "not_executed"; a skipped mode never gets numbers
    note: Optional[str] = None
