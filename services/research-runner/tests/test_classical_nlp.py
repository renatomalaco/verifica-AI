import pytest
from research_runner.domain.classical_nlp import ClassicalPTBRClassifier


def test_classical_nlp_training_and_inference():
    classifier = ClassicalPTBRClassifier()
    # Train on small PT-BR bootstrap corpus
    train_texts = [
        "Oi mãe troquei de número me manda um pix urgente",
        "Sua conta foi bloqueada acesse para regularizar",
        "Notificação urgente de débito pendente regularize agora",
        "Você ganhou um sorteio envie seu pix para resgatar",
        "Oi filho tudo bem o almoço no domingo vai ser às 13h",
        "Lembrete de consulta médica amanhã com Dr Silva",
        "Seu pedido foi entregue com sucesso",
        "Segue o comprovante da pizza de ontem",
    ]
    train_labels = [
        "GOLPE",
        "GOLPE",
        "GOLPE",
        "GOLPE",
        "SEGURO",
        "SEGURO",
        "SEGURO",
        "SEGURO",
    ]
    classifier.fit(train_texts, train_labels)

    # Predict on test samples
    pred_phish, conf_phish = classifier.predict("Oi mãe me manda um pix urgente por favor")
    assert pred_phish == "GOLPE"
    assert conf_phish >= 0.50

    pred_legit, conf_legit = classifier.predict("Almoço de domingo em família com a vovó")
    assert pred_legit == "SEGURO"
    assert conf_legit >= 0.50


def test_scam_probability_is_the_probability_of_the_golpe_class():
    classifier = ClassicalPTBRClassifier().fit(
        ["manda um pix urgente", "conta bloqueada regularize", "almoco de domingo", "consulta amanha"],
        ["GOLPE", "GOLPE", "SEGURO", "SEGURO"],
    )
    label, confidence = classifier.predict("pix urgente")
    assert label == "GOLPE"
    assert classifier.scam_probability("pix urgente") == pytest.approx(confidence)
