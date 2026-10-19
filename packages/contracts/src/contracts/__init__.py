from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from contracts.url_utils import normalize_url, extract_domain


class ThreatLevel(StrEnum):
    SAFE = "SEGURO"
    CAUTION = "CUIDADO"
    SCAM = "GOLPE"
    INCONCLUSIVE = "INCONCLUSIVO"


class Channel(StrEnum):
    TEXT = "texto"
    URL = "url"
    IMAGE = "imagem"


class Persuasion(StrEnum):
    URGENCY = "urgencia"
    FINANCIAL_THREAT = "ameaca_financeira"
    AFFECTIVE_COERCION = "coercao_afetiva"
    NONE = "nenhuma"


class ScanRequest(BaseModel):
    content: str = Field(default="", max_length=10_000)
    image_b64: str | None = Field(default=None)

    @model_validator(mode="after")
    def check_non_empty_input(self) -> "ScanRequest":
        if not self.content.strip() and not (self.image_b64 and self.image_b64.strip()):
            raise ValueError("O conteúdo da requisição não pode ser vazio. Envie texto, URL ou imagem.")
        return self


class TriageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class TriageResult(BaseModel):
    is_phishing: float = Field(ge=0.0, le=1.0)
    requires_visual_inspection: float = Field(default=0.0, ge=0.0, le=1.0)
    persuasion: Persuasion = Field(default=Persuasion.NONE)


class ScanDetails(BaseModel):
    channel: Channel
    deciding_stage: str
    category: str | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    domain_signals: dict[str, str] | None = None
    links_not_inspected: bool = False
    latency_breakdown: dict[str, float] = Field(default_factory=dict)


class ScanResponse(BaseModel):
    id: UUID
    threat_level: ThreatLevel
    verdict_plain: str
    action_advice: str
    details: ScanDetails


class StageName(StrEnum):
    """Single contract for the stages emitted over SSE. The front end translates them in web/src/utils/stages.ts."""

    TRIAGE = "triage"
    IMAGE_EXTRACTION = "image_extraction"
    STAGE_0_CACHE = "stage_0_cache"
    STAGE_1_SIGNALS = "stage_1_signals"
    STAGE_2_INSPECTION = "stage_2_inspection"
    VISUAL_RAG = "visual_rag"


StageStatus = Literal["started", "done", "skipped"]


class StageEvent(BaseModel):
    stage: StageName
    status: StageStatus


# DTO for communication between scan-orchestrator and url-inspector
class InspectRequest(BaseModel):
    url: str
    timeout_seconds: float = 8.0


class InspectResult(BaseModel):
    dom_text: str = ""
    final_url: str = ""
    screenshot_b64: str | None = None
    has_password_field: bool = False
    is_blocked: bool = False
    blocked_reason: str | None = None


# DTO for communication between scan-orchestrator and image-extractor (Phase 3)
class ExtractRequest(BaseModel):
    image_b64: str


class ExtractResult(BaseModel):
    sha256: str
    phash: str
    extracted_text: str = ""
    qr_codes: list[str] = Field(default_factory=list)
    urls_found: list[str] = Field(default_factory=list)


# DTOs for Visual RAG and Brand Spoofing (Phase 4)
class BrandMatchRequest(BaseModel):
    image_b64: str
    current_domain: str | None = None


class BrandMatchResult(BaseModel):
    matched_brand: str | None = None
    is_spoofing: bool = False
    similarity: float = 0.0
    official_domains: list[str] = Field(default_factory=list)


# "Me explica" DTOs (R5b). The ai-gateway request carries only the persisted
# verdict, never the raw content sent by the person (LGPD).
class ExplainRequest(BaseModel):
    threat_level: ThreatLevel
    channel: Channel
    deciding_stage: str
    category: str | None = None
    verdict_plain: str
    action_advice: str
    scores: dict[str, float] = Field(default_factory=dict)
    domain_signals: dict[str, str] = Field(default_factory=dict)
    links_not_inspected: bool = False


class ExplainResult(BaseModel):
    lines: list[str] = Field(min_length=1, max_length=12)


class ExplainResponse(BaseModel):
    lines: list[str]
    remaining_today: int = Field(ge=0)


class QuotaExceeded(BaseModel):
    retry_at: datetime
