from typing import Protocol
from uuid import UUID
from datetime import datetime, timezone
from contracts import Channel, ScanDetails, ScanResponse, ThreatLevel, VerdictMessage
from sqlalchemy import select, Column, String, DateTime, Numeric, JSON, Table, MetaData
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

metadata = MetaData()

analises_phishing_table = Table(
    "analises_phishing",
    metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    Column("scan_type", String(20), nullable=False),
    Column("input_hash", String(64), nullable=False, index=True),
    Column("threat_level", String(30), nullable=False),
    Column("confidence_score", Numeric(4, 3), nullable=False),
    Column("verdict_message", String(40), nullable=False),
    Column("latency_breakdown", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)


class ScanRepository(Protocol):
    async def save(self, input_hash: str, response: ScanResponse) -> None:
        ...

    async def get(self, scan_id: UUID) -> ScanResponse | None:
        ...


class InMemoryScanRepository:
    """In-memory implementation for tests and lightweight development without Docker."""

    def __init__(self):
        self.records: dict[str, list[ScanResponse]] = {}
        self._by_id: dict[UUID, ScanResponse] = {}

    async def save(self, input_hash: str, response: ScanResponse) -> None:
        if input_hash not in self.records:
            self.records[input_hash] = []
        self.records[input_hash].append(response)
        self._by_id[response.id] = response

    async def get(self, scan_id: UUID) -> ScanResponse | None:
        return self._by_id.get(scan_id)


class SqlScanRepository:
    """SQL implementation that persists verdicts in PostgreSQL for telemetry and LGPD auditing."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def save(self, input_hash: str, response: ScanResponse) -> None:
        confidence = response.details.scores.get("is_phishing", 0.50)
        stmt = analises_phishing_table.insert().values(
            id=response.id,
            scan_type=response.details.channel.value,
            input_hash=input_hash,
            threat_level=response.threat_level.value,
            confidence_score=round(float(confidence), 3),
            verdict_message=response.verdict_message.value,
            latency_breakdown=response.details.latency_breakdown,
            created_at=datetime.now(timezone.utc),
        )
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(stmt)

    async def get(self, scan_id: UUID) -> ScanResponse | None:
        # The table stores only the verdict essentials (no raw content); the remaining
        # details are not persisted and come back empty.
        stmt = select(analises_phishing_table).where(analises_phishing_table.c.id == scan_id)
        async with self._session_factory() as session:
            row = (await session.execute(stmt)).mappings().first()
        if row is None:
            return None
        return ScanResponse(
            id=row["id"],
            threat_level=ThreatLevel(row["threat_level"]),
            verdict_message=VerdictMessage(row["verdict_message"]),
            details=ScanDetails(
                channel=Channel(row["scan_type"]),
                deciding_stage="persisted",
                scores={"is_phishing": float(row["confidence_score"])},
                latency_breakdown=row["latency_breakdown"] or {},
            ),
        )
