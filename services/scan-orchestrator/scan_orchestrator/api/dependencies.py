"""Wires the orchestrator dependencies for FastAPI (overridable in tests)."""

import secrets
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from scan_orchestrator.application.analyze_text import AnalyzeTextUseCase
from scan_orchestrator.application.explain_scan import ExplainScanUseCase
from scan_orchestrator.domain.cascade import (
    BrandMatcherClientProtocol,
    Cascade,
    InspectorClientProtocol,
    RedisCacheClientProtocol,
    DomainEvidenceClient,
    Stage0CacheAndFeeds,
    Stage1ReputationAndSignals,
    Stage2RemoteInspection,
    TriageClient,
)
from scan_orchestrator.domain.decision import ThresholdPolicy
from scan_orchestrator.domain.quota import ExplainQuota, QuotaLimits, QuotaStore
from scan_orchestrator.infrastructure.brand_matcher_client import HttpBrandMatcherClient
from scan_orchestrator.infrastructure.explainer_client import ExplainerClientProtocol, HttpExplainerClient
from scan_orchestrator.infrastructure.image_extractor_client import (
    HttpImageExtractorClient,
    ImageExtractorClientProtocol,
)
from scan_orchestrator.infrastructure.inspector_client import HttpInspectorClient
from scan_orchestrator.infrastructure.quota_store import RedisQuotaStore
from scan_orchestrator.infrastructure.redis_client import RedisCacheClient
from scan_orchestrator.infrastructure.domain_evidence_client import (
    CrtShClient,
    HttpDomainEvidenceClient,
    RdapClient,
    RedisTrancoRanks,
)
from scan_orchestrator.infrastructure.scan_repository import (
    InMemoryScanRepository,
    ScanRepository,
    SqlScanRepository,
)
from scan_orchestrator.infrastructure.triage_client import HttpTriageClient
from scan_orchestrator.settings import Settings

_in_memory_repo = InMemoryScanRepository()
# Without DEVICE_TOKEN_SECRET, each process picks a random one and device cookies are invalidated on every restart.
_ephemeral_device_secret = secrets.token_bytes(32)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_threshold_policy(settings: Settings = Depends(get_settings)) -> ThresholdPolicy:
    return ThresholdPolicy(scam=settings.THRESHOLD_SCAM, safe=settings.THRESHOLD_SAFE)


def get_device_secret(settings: Settings = Depends(get_settings)) -> bytes:
    if settings.DEVICE_TOKEN_SECRET:
        return settings.DEVICE_TOKEN_SECRET.encode("utf-8")
    return _ephemeral_device_secret


def get_triage_client(settings: Settings = Depends(get_settings)) -> TriageClient:
    return HttpTriageClient(base_url=settings.AI_GATEWAY_URL)


@lru_cache
def _sql_repository(database_url: str) -> SqlScanRepository:
    # One engine (and connection pool) per process, not per request.
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return SqlScanRepository(async_sessionmaker(engine, expire_on_commit=False))


def get_scan_repository(settings: Settings = Depends(get_settings)) -> ScanRepository:
    if not settings.DATABASE_URL:
        return _in_memory_repo
    return _sql_repository(settings.DATABASE_URL)


def get_redis_client(settings: Settings = Depends(get_settings)) -> RedisCacheClientProtocol:
    return RedisCacheClient(redis_url=settings.REDIS_URL)


@lru_cache
def _tranco_ranks(redis_url: str) -> RedisTrancoRanks:
    return RedisTrancoRanks.from_url(redis_url)


def get_domain_evidence_client(settings: Settings = Depends(get_settings)) -> DomainEvidenceClient:
    return HttpDomainEvidenceClient(rdap=RdapClient(), crtsh=CrtShClient(), tranco=_tranco_ranks(settings.REDIS_URL))


def get_inspector_client(settings: Settings = Depends(get_settings)) -> InspectorClientProtocol:
    return HttpInspectorClient(base_url=settings.URL_INSPECTOR_URL)


def get_image_extractor_client(settings: Settings = Depends(get_settings)) -> ImageExtractorClientProtocol:
    return HttpImageExtractorClient(base_url=settings.IMAGE_EXTRACTOR_URL)


def get_brand_matcher_client(settings: Settings = Depends(get_settings)) -> BrandMatcherClientProtocol:
    return HttpBrandMatcherClient(base_url=settings.AI_GATEWAY_URL)


def get_explainer_client(settings: Settings = Depends(get_settings)) -> ExplainerClientProtocol:
    return HttpExplainerClient(base_url=settings.AI_GATEWAY_URL)


@lru_cache
def _redis_quota_store(redis_url: str) -> RedisQuotaStore:
    return RedisQuotaStore(redis_url=redis_url)


def get_quota_store(settings: Settings = Depends(get_settings)) -> QuotaStore:
    return _redis_quota_store(settings.REDIS_URL)


def get_cascade(
    policy: ThresholdPolicy = Depends(get_threshold_policy),
    redis_client: RedisCacheClientProtocol = Depends(get_redis_client),
    evidence_client: DomainEvidenceClient = Depends(get_domain_evidence_client),
    inspector_client: InspectorClientProtocol = Depends(get_inspector_client),
    triage_client: TriageClient = Depends(get_triage_client),
    brand_matcher: BrandMatcherClientProtocol = Depends(get_brand_matcher_client),
) -> Cascade:
    stages = [
        Stage0CacheAndFeeds(cache_client=redis_client),
        Stage1ReputationAndSignals(evidence_client=evidence_client),
        Stage2RemoteInspection(
            inspector_client=inspector_client,
            triage_client=triage_client,
            brand_matcher=brand_matcher,
        ),
    ]
    return Cascade(stages=stages, policy=policy)


def get_analyze_text_use_case(
    policy: ThresholdPolicy = Depends(get_threshold_policy),
    triage_client: TriageClient = Depends(get_triage_client),
    repository: ScanRepository = Depends(get_scan_repository),
    cascade: Cascade = Depends(get_cascade),
    image_extractor: ImageExtractorClientProtocol = Depends(get_image_extractor_client),
    redis_client: RedisCacheClientProtocol = Depends(get_redis_client),
) -> AnalyzeTextUseCase:
    return AnalyzeTextUseCase(
        triage_client=triage_client,
        repository=repository,
        policy=policy,
        cascade=cascade,
        image_extractor=image_extractor,
        redis_client=redis_client,
    )


def get_explain_use_case(
    settings: Settings = Depends(get_settings),
    repository: ScanRepository = Depends(get_scan_repository),
    explainer: ExplainerClientProtocol = Depends(get_explainer_client),
    store: QuotaStore = Depends(get_quota_store),
) -> ExplainScanUseCase:
    quota = ExplainQuota(
        store=store,
        limits=QuotaLimits(
            daily=settings.EXPLAIN_DAILY_LIMIT,
            monthly=settings.EXPLAIN_MONTHLY_LIMIT,
            ip_per_window=settings.EXPLAIN_IP_LIMIT,
            ip_window_seconds=settings.EXPLAIN_IP_WINDOW_SECONDS,
        ),
        utc_offset_hours=settings.QUOTA_UTC_OFFSET_HOURS,
    )
    return ExplainScanUseCase(repository=repository, explainer=explainer, quota=quota)
