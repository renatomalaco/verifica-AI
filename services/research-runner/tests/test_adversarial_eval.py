from research_runner.domain.adversarial_eval import evaluate_adversarial
from research_runner.domain.dataset import Sample

INVISIBLE = "​"


def adversarial(id: str, content: str, label: str = "GOLPE") -> Sample:
    return Sample(id=id, channel="texto", content=content, label=label, origin="real", source="t", adversarial=True)


def detects_only_clean_pix(text: str) -> float:
    """Toy detector: it only sees the scam when the word survives intact."""
    return 0.95 if "pix" in text.lower() else 0.05


def strip_invisible(text: str) -> str:
    return text.replace(INVISIBLE, "")


def test_reports_detection_with_and_without_sanitization():
    samples = [
        adversarial("a1", f"me manda um p{INVISIBLE}ix urgente"),
        adversarial("a2", "me manda um pix urgente"),
    ]

    result = evaluate_adversarial(samples, scam_probability=detects_only_clean_pix, sanitize=strip_invisible)

    assert result.total == 2
    assert result.detected_without_sanitization == 1
    assert result.detected_with_sanitization == 2


def test_only_adversarial_scams_are_counted():
    samples = [
        adversarial("a1", "pix", label="SEGURO"),
        Sample(id="n1", channel="texto", content="pix", label="GOLPE", origin="real", source="t"),
    ]
    result = evaluate_adversarial(samples, scam_probability=detects_only_clean_pix, sanitize=strip_invisible)
    assert result.total == 0
