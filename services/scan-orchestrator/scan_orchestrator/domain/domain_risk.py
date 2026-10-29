"""Stage 1 rule: what registration age, first certificate and popularity say about a domain."""

from dataclasses import asdict, dataclass

from contracts import ThreatLevel

YOUNG_DAYS = 30
REPUTABLE_RANK = 100_000
REPUTABLE_DAYS = 365
SUSPICIOUS_FLOOR = 0.6  # lands on CUIDADO with the default thresholds; inspection may raise it


@dataclass(frozen=True)
class DomainEvidence:
    """Each field is None when its source did not answer: unknown, never assumed old."""

    age_days: int | None = None
    certificate_age_days: int | None = None
    tranco_rank: int | None = None

    def as_signals(self) -> dict[str, str]:
        names = {"age_days": "domain_age_days", "certificate_age_days": "certificate_age_days", "tranco_rank": "tranco_rank"}
        return {names[k]: str(v) for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class DomainAssessment:
    threat: ThreatLevel | None = None
    score_floor: float | None = None
    is_reputable: bool = False


def assess_domain(evidence: DomainEvidence, imitated: str | None) -> DomainAssessment:
    young = _is_young(evidence)
    if imitated and young:
        return DomainAssessment(threat=ThreatLevel.SCAM)
    if imitated or young:
        return DomainAssessment(score_floor=SUSPICIOUS_FLOOR)
    return DomainAssessment(is_reputable=_is_reputable(evidence))


def _is_young(evidence: DomainEvidence) -> bool:
    ages = (evidence.age_days, evidence.certificate_age_days)
    return any(age is not None and age < YOUNG_DAYS for age in ages)


def _is_reputable(evidence: DomainEvidence) -> bool:
    rank, age = evidence.tranco_rank, evidence.age_days
    return rank is not None and rank <= REPUTABLE_RANK and age is not None and age >= REPUTABLE_DAYS
