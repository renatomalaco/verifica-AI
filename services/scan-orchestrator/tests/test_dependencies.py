from contracts import VerdictMessage
from scan_orchestrator.api.dependencies import (
    get_brand_matcher_client,
    get_cascade,
    get_explainer_client,
    get_image_extractor_client,
    get_scan_repository,
    get_triage_client,
)
from scan_orchestrator.domain.cascade import StageContext
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.infrastructure.brand_matcher_client import HttpBrandMatcherClient
from scan_orchestrator.infrastructure.fakes import (
    FakeDomainEvidenceClient,
    FakeInspectorClient,
    FakeRedisCacheClient,
    FakeTriageClient,
)
from scan_orchestrator.infrastructure.scan_repository import (
    InMemoryScanRepository,
    SqlScanRepository,
)
from scan_orchestrator.settings import Settings
from scan_orchestrator.application.confirm_triage import ConfirmingTriage
from scan_orchestrator.infrastructure.triage_client import HttpTriageClient

POLICY = ThresholdPolicy(scam=0.90, safe=0.10)


def test_without_database_url_scans_stay_in_memory():
    assert isinstance(get_scan_repository(Settings(DATABASE_URL="")), InMemoryScanRepository)


def test_with_database_url_scans_are_persisted_in_sql():
    # Building the engine does not connect, so no database is needed here.
    settings = Settings(DATABASE_URL="postgresql+asyncpg://verifica:x@localhost:5432/verifica_db")
    assert isinstance(get_scan_repository(settings), SqlScanRepository)


def test_visual_rag_is_off_until_explicitly_enabled():
    # An unseeded catalog answers 503, which would cap every page at CUIDADO; off means "not run".
    assert Settings(_env_file=None).VISUAL_RAG_ENABLED is False
    assert get_brand_matcher_client(Settings(_env_file=None)) is None


def test_enabled_visual_rag_calls_the_ai_gateway():
    client = get_brand_matcher_client(Settings(_env_file=None, VISUAL_RAG_ENABLED=True))
    assert isinstance(client, HttpBrandMatcherClient)


def test_ai_gateway_calls_outwait_the_gemini_timeout_of_the_gateway():
    # The gateway gives Gemini up to 15 s (GEMINI_TIMEOUT_SECONDS). Giving up earlier here
    # turned every Gemini triage into the INCONCLUSIVO fallback in production.
    settings = Settings(_env_file=None)

    assert settings.AI_GATEWAY_TIMEOUT_SECONDS == 20.0
    assert _gateway_of(get_triage_client(settings, POLICY))._timeout_seconds == 20.0
    assert get_explainer_client(settings)._timeout_seconds == 20.0


def test_ai_gateway_timeout_is_configurable():
    settings = Settings(_env_file=None, AI_GATEWAY_TIMEOUT_SECONDS=30.0)

    assert _gateway_of(get_triage_client(settings, POLICY))._timeout_seconds == 30.0


def test_every_triage_is_confirmed_by_the_deep_model_when_in_doubt():
    triage = get_triage_client(Settings(_env_file=None), POLICY)

    assert isinstance(triage, ConfirmingTriage)
    assert isinstance(_gateway_of(triage), HttpTriageClient)


def _gateway_of(triage: ConfirmingTriage) -> HttpTriageClient:
    return triage._models
    assert get_explainer_client(settings)._timeout_seconds == 30.0


async def test_the_cascade_knows_the_public_address_of_the_site():
    cascade = get_cascade(
        settings=Settings(_env_file=None, PUBLIC_BASE_URL="https://verifica-ai.duckdns.org"),
        policy=ThresholdPolicy(scam=0.70, safe=0.30),
        redis_client=FakeRedisCacheClient(),
        evidence_client=FakeDomainEvidenceClient(),
        inspector_client=FakeInspectorClient(),
        triage_client=FakeTriageClient(),
        brand_matcher=None,
    )

    response = await cascade.run(StageContext(raw_url="https://verifica-ai.duckdns.org/"))

    assert response.verdict_message is VerdictMessage.SAFE_OWN_ADDRESS


def test_image_reading_gets_enough_time_on_a_small_vm():
    # Tesseract on the VM's single CPU took longer than the old 12 s on real screenshots.
    settings = Settings(_env_file=None)

    assert settings.IMAGE_EXTRACTOR_TIMEOUT_SECONDS == 40.0
    assert get_image_extractor_client(settings)._timeout_seconds == 40.0
