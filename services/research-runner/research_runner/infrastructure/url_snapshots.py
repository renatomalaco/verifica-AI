"""Frozen URL snapshots for reproducible replay of stages 1 and 2 in the ablation study."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from contracts import InspectResult
from scan_orchestrator.domain.domain_risk import DomainEvidence


@dataclass(frozen=True)
class UrlSnapshotStore:
    collected_at: str
    domains: dict[str, DomainEvidence]
    pages: dict[str, InspectResult]


def load_url_snapshots(path: str) -> tuple[UrlSnapshotStore, str]:
    raw = Path(path).read_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode("utf-8"))
    domains = {
        host.lower(): DomainEvidence(
            age_days=entry.get("age_days"),
            certificate_age_days=entry.get("certificate_age_days"),
            tranco_rank=entry.get("tranco_rank"),
        )
        for host, entry in data.get("domains", {}).items()
    }
    pages = {
        url: InspectResult(
            dom_text=entry.get("dom_text", ""),
            final_url=entry.get("final_url", url),
            screenshot_b64=entry.get("screenshot_b64"),
            has_password_field=bool(entry.get("has_password_field", False)),
            is_blocked=bool(entry.get("is_blocked", False)),
            blocked_reason=entry.get("blocked_reason"),
        )
        for url, entry in data.get("pages", {}).items()
    }
    store = UrlSnapshotStore(
        collected_at=str(data.get("collected_at", "")),
        domains=domains,
        pages=pages,
    )
    return store, sha256


class SnapshotDomainEvidenceClient:
    """Replays recorded RDAP, crt.sh and Tranco signals; missing domains stay unknown."""

    def __init__(self, store: UrlSnapshotStore) -> None:
        self._store = store

    async def lookup(self, domain: str) -> DomainEvidence:
        return self._store.domains.get(domain.lower(), DomainEvidence())


class SnapshotInspectorClient:
    """Replays recorded Playwright inspections; missing URLs are blocked, never clean."""

    def __init__(self, store: UrlSnapshotStore) -> None:
        self._store = store

    async def inspect(self, url: str) -> InspectResult:
        page = self._store.pages.get(url)
        if page is None:
            return InspectResult(final_url=url, is_blocked=True, blocked_reason="not_in_snapshot")
        return page
