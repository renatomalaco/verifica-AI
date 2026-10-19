from typing import Any, Dict, List
from ai_gateway.domain.sanitizer import sanitize_text
from ai_gateway.domain.envelope import build_envelope
from research_runner.domain.classical_nlp import ClassicalPTBRClassifier


def evaluate_adversarial_injections(
    samples: List[str],
) -> Dict[str, Any]:
    classifier = ClassicalPTBRClassifier.create_default()

    total = len(samples)
    defended_count = 0
    raw_bypassed_count = 0

    for sample in samples:
        # Without sanitization: injections with override commands or zero-width chars
        # With sanitization + envelope:
        clean_text = sanitize_text(sample)
        wrapped = build_envelope(clean_text)

        # The classifier evaluates the sanitized text (real content stripped of zero-width chars and delimiters)
        pred, conf = classifier.predict(clean_text)

        # Scam detected despite the adversarial injection attempt
        if pred == "GOLPE":
            defended_count += 1

    robustness = defended_count / total if total > 0 else 1.0

    return {
        "total_adversarial": total,
        "defended_with_sanitization": defended_count,
        "robustness_rate": robustness,
    }
