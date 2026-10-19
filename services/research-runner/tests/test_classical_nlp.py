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


def test_classical_nlp_default_trained_instance():
    # Factory with standard pre-trained or default corpus
    classifier = ClassicalPTBRClassifier.create_default()
    pred, conf = classifier.predict("URGENTE: Sua conta bancária foi bloqueada. Acesse o link para desbloquear.")
    assert pred == "GOLPE"
    assert conf >= 0.50

    pred_legit, conf_legit = classifier.predict("Bom dia, reunião de trabalho agendada para as 15h.")
    assert pred_legit == "SEGURO"
    assert conf_legit >= 0.50
