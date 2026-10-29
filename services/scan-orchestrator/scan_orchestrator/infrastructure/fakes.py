from contracts import BrandMatchResult, InspectResult, Persuasion, ScanResponse, TriageResult, normalize_url
from scan_orchestrator.domain.domain_risk import DomainEvidence
from scan_orchestrator.domain.perceptual_hash import nearest


class FakeRedisCacheClient:
    def __init__(self) -> None:
        self._blacklist: set[str] = set()
        self._cache: dict[str, ScanResponse] = {}
        self._phashes: dict[str, ScanResponse] = {}

    def add_to_blacklist(self, url: str) -> None:
        self._blacklist.add(normalize_url(url))

    async def is_blacklisted(self, url: str) -> bool:
        return normalize_url(url) in self._blacklist

    async def get_cached_scan(self, sha256_hash: str) -> ScanResponse | None:
        return self._cache.get(sha256_hash)

    async def set_cached_scan(self, sha256_hash: str, response: ScanResponse, ttl: int = 3600) -> None:
        self._cache[sha256_hash] = response

    async def get_cached_phash(self, phash: str) -> ScanResponse | None:
        match = nearest(phash, set(self._phashes))
        return self._phashes[match] if match else None

    async def set_cached_phash(self, phash: str, response: ScanResponse, ttl: int = 3600) -> None:
        self._phashes[phash] = response


class FakeDomainEvidenceClient:
    """Unknown evidence by default, like a registry that did not answer."""

    def __init__(self) -> None:
        self._evidence: dict[str, DomainEvidence] = {}

    def set_evidence(self, domain: str, evidence: DomainEvidence) -> None:
        self._evidence[domain] = evidence

    async def lookup(self, domain: str) -> DomainEvidence:
        return self._evidence.get(domain, DomainEvidence())


class FakeInspectorClient:
    def __init__(self) -> None:
        self._results: dict[str, InspectResult] = {}
        self._default = InspectResult(dom_text="", final_url="", is_blocked=False)
        self.calls: list[str] = []

    def set_result(self, url: str, result: InspectResult) -> None:
        self._results[normalize_url(url)] = result

    async def inspect(self, url: str) -> InspectResult:
        self.calls.append(url)
        return self._results.get(normalize_url(url), self._default)


class FakeBrandMatcherClient:
    def __init__(self, default_result: BrandMatchResult | None = None) -> None:
        self._default = default_result or BrandMatchResult()

    def set_result(self, result: BrandMatchResult) -> None:
        self._default = result

    async def match_brand(self, image_b64: str, current_domain: str | None = None) -> BrandMatchResult:
        return self._default


class FakeTriageClient:
    def __init__(self, default_result: TriageResult | None = None) -> None:
        self._result = default_result or TriageResult(is_phishing=0.1, persuasion=Persuasion.NONE)

    def set_result(self, result: TriageResult) -> None:
        self._result = result

    async def triage(self, text: str) -> TriageResult | None:
        return self._result
