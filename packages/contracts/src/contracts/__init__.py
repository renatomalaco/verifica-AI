from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
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


class VerdictMessage(StrEnum):
    """Code of the summary and advice shown with a verdict. The backend decides and the
    front end words it (web/src/domain/verdictMessages.ts), so no user-facing text
    lives in the services."""

    SCAM_AFFECTIVE_COERCION = "scam_affective_coercion"
    SCAM_FINANCIAL_THREAT = "scam_financial_threat"
    SCAM_URGENCY = "scam_urgency"
    SCAM_BRAND_SPOOFING = "scam_brand_spoofing"
    SCAM_GENERIC = "scam_generic"
    CAUTION = "caution"
    SAFE = "safe"
    INCONCLUSIVE = "inconclusive"


class Locale(StrEnum):
    PT_BR = "pt-BR"


DEFAULT_LOCALE = Locale.PT_BR


def resolve_locale(raw: str | None) -> Locale:
    """Unknown or missing locales fall back to the product's default language."""
    for locale in Locale:
        if raw and raw.lower() == locale.value.lower():
            return locale
    return DEFAULT_LOCALE


class ScanRequest(BaseModel):
    content: str = Field(default="", max_length=10_000)
    image_b64: str | None = Field(default=None)

    @model_validator(mode="after")
    def check_non_empty_input(self) -> "ScanRequest":
        if not self.content.strip() and not (self.image_b64 and self.image_b64.strip()):
            raise ValueError("Request content must not be empty: send text, a URL or an image.")
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
    verdict_message: VerdictMessage
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
    ocr_confidence: float | None = None  # 0-100; None when the engine cannot tell
    clean_image_b64: str | None = None  # upright JPEG without EXIF: the only copy that travels on


# DTOs for Visual RAG and Brand Spoofing (Phase 4)
class ImageSource(StrEnum):
    # Only a page our own browser opened may go to a third-party VLM; a person's
    # screenshot can show their chats, names and numbers.
    PAGE_SCREENSHOT = "page_screenshot"
    USER_IMAGE = "user_image"


class BrandMatchRequest(BaseModel):
    image_b64: str
    current_domain: str | None = None
    image_source: ImageSource = ImageSource.USER_IMAGE


class BrandMatchResult(BaseModel):
    matched_brand: str | None = None
    is_spoofing: bool = False
    similarity: float = 0.0
    official_domains: list[str] = Field(default_factory=list)
    # Resembles a brand but below the threshold and not confirmed: a signal, never a verdict.
    possible_brand: str | None = None


# "Me explica" DTOs (R5b). The ai-gateway request carries only the persisted
# verdict, never the raw content sent by the person (LGPD).
class ExplainRequest(BaseModel):
    threat_level: ThreatLevel
    channel: Channel
    deciding_stage: str
    category: str | None = None
    verdict_message: VerdictMessage
    locale: Locale = DEFAULT_LOCALE
    scores: dict[str, float] = Field(default_factory=dict)
    domain_signals: dict[str, str] = Field(default_factory=dict)
    links_not_inspected: bool = False


class ExplainScanRequest(BaseModel):
    """Body of POST /api/v1/scans/{id}/explain: the language the explanation must be written in."""

    locale: Locale = DEFAULT_LOCALE

    @field_validator("locale", mode="before")
    @classmethod
    def fallback_to_default(cls, value: object) -> Locale:
        return resolve_locale(value if isinstance(value, str) else None)


class ExplainResult(BaseModel):
    lines: list[str] = Field(min_length=1, max_length=12)


class ExplainResponse(BaseModel):
    lines: list[str]
    remaining_today: int = Field(ge=0)


class QuotaExceeded(BaseModel):
    retry_at: datetime
