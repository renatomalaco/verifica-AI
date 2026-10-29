from contracts import ThreatLevel
from scan_orchestrator.domain.domain_risk import DomainEvidence, assess_domain

OLD = DomainEvidence(age_days=4000, certificate_age_days=900, tranco_rank=500)
YOUNG = DomainEvidence(age_days=5)
UNKNOWN = DomainEvidence()


def test_young_lookalike_is_a_scam():
    assessment = assess_domain(YOUNG, imitated="itau.com.br")
    assert assessment.threat is ThreatLevel.SCAM


def test_a_recent_certificate_also_counts_as_young():
    assessment = assess_domain(DomainEvidence(certificate_age_days=2), imitated="itau.com.br")
    assert assessment.threat is ThreatLevel.SCAM


def test_lookalike_alone_raises_to_caution_but_lets_inspection_decide():
    assessment = assess_domain(OLD, imitated="mercadolivre.com.br")
    assert assessment.threat is None
    assert assessment.score_floor == 0.6


def test_young_domain_alone_raises_to_caution():
    assessment = assess_domain(YOUNG, imitated=None)
    assert assessment.threat is None
    assert assessment.score_floor == 0.6


def test_unknown_age_is_not_treated_as_old():
    # Missing evidence (RDAP down, private registry) never makes a domain look trustworthy.
    assert assess_domain(UNKNOWN, imitated=None).is_reputable is False


def test_popular_old_domain_is_reputable_but_never_safe_by_itself():
    assessment = assess_domain(OLD, imitated=None)
    assert assessment.is_reputable is True
    assert assessment.threat is None
    assert assessment.score_floor is None


def test_evidence_becomes_readable_signals():
    assert YOUNG.as_signals() == {"domain_age_days": "5"}
    assert OLD.as_signals() == {"domain_age_days": "4000", "certificate_age_days": "900", "tranco_rank": "500"}
