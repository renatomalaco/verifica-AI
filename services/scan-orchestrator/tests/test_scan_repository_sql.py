import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from contracts import Channel, ScanDetails, ScanResponse, ThreatLevel, VerdictMessage
from scan_orchestrator.infrastructure.scan_repository import SqlScanRepository, metadata

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture
async def repository():
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set (needs the Postgres from infra/docker-compose.yml)")
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    yield SqlScanRepository(async_sessionmaker(engine, expire_on_commit=False))
    await engine.dispose()


async def test_saved_verdict_comes_back_without_the_content(repository):
    scan = ScanResponse(
        id=uuid4(),
        threat_level=ThreatLevel.SCAM,
        verdict_message=VerdictMessage.SCAM_URGENCY,
        details=ScanDetails(
            channel=Channel.TEXT,
            deciding_stage="triage",
            scores={"is_phishing": 0.97},
            latency_breakdown={"triage": 12.5},
        ),
    )

    await repository.save("a" * 64, scan)
    loaded = await repository.get(scan.id)

    assert loaded is not None
    assert loaded.threat_level is ThreatLevel.SCAM
    assert loaded.verdict_message is VerdictMessage.SCAM_URGENCY
    assert loaded.details.latency_breakdown == {"triage": 12.5}
