from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


DEFAULT_TRAIN_CORPUS = [
    # GOLPE (phishing / coercion / fraud in PT-BR)
    ("Oi mãe troquei de número me manda um pix urgente para pagar conta", "GOLPE"),
    ("Sua conta bancária foi bloqueada por suspeita de fraude acesse agora", "GOLPE"),
    ("Aviso urgente notificação extrajudicial de protesto em cartório", "GOLPE"),
    ("Você ganhou um sorteio de R$ 5.000 clique no link para resgatar", "GOLPE"),
    ("Receita Federal comunica irregularidade no CPF clique para regularizar", "GOLPE"),
    ("Banco informa pendência cadastral crítica e cancelamento de cartão", "GOLPE"),
    ("Transferência Pix retida confirme sua senha para liberação imediata", "GOLPE"),
    ("Parabéns você foi selecionado para vaga de emprego com depósito antecipado", "GOLPE"),
    ("Comprovante falso de pagamento agendado envie a mercadoria", "GOLPE"),
    ("Seu pacote dos Correios está retido na alfândega pague a taxa aqui", "GOLPE"),
    ("URGENTE: Sua conta bancária foi bloqueada. Acesse o link para desbloquear.", "GOLPE"),

    # SEGURO (legitimate messages in PT-BR)
    ("Oi filho tudo bem o almoço de domingo vai ser na casa da vovó às 13h", "SEGURO"),
    ("Lembrete de consulta médica confirmada para amanhã com Dr Silva", "SEGURO"),
    ("Seu pedido da loja online foi entregue no endereço cadastrado", "SEGURO"),
    ("Segue o comprovante da pizza de ontem que combinamos", "SEGURO"),
    ("Bom dia reunião de trabalho e alinhamento agendada para as 15h via Teams", "SEGURO"),
    ("Aviso aos condôminos sobre manutenção preventiva do elevador", "SEGURO"),
    ("Parabéns pelo seu aniversário que Deus te abençoe com muita saúde", "SEGURO"),
    ("Segue o arquivo com o resumo da aula de algoritmos de hoje", "SEGURO"),
    ("Sua fatura fechou e o débito automático será efetuado no vencimento", "SEGURO"),
    ("Obrigado pela preferência volte sempre à nossa padaria", "SEGURO"),
]


class ClassicalPTBRClassifier:
    """Lightweight classical NLP classifier (TF-IDF + Logistic Regression) for PT-BR text."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            sublinear_tf=True,
            ngram_range=(1, 2),
            lowercase=True,
            strip_accents="unicode",
        )
        self.model = LogisticRegression(class_weight="balanced", random_state=42)
        self._is_fitted = False

    def fit(self, texts: List[str], labels: List[str]) -> "ClassicalPTBRClassifier":
        x_vec = self.vectorizer.fit_transform(texts)
        self.model.fit(x_vec, labels)
        self._is_fitted = True
        return self

    def predict(self, text: str) -> Tuple[str, float]:
        if not self._is_fitted:
            raise RuntimeError("Classifier must be fitted before calling predict.")

        x_vec = self.vectorizer.transform([text])
        probabilities = self.model.predict_proba(x_vec)[0]
        classes = self.model.classes_

        pred_idx = probabilities.argmax()
        pred_label = str(classes[pred_idx])
        confidence = float(probabilities[pred_idx])

        return pred_label, confidence

    @classmethod
    def create_default(cls) -> "ClassicalPTBRClassifier":
        texts = [t[0] for t in DEFAULT_TRAIN_CORPUS]
        labels = [t[1] for t in DEFAULT_TRAIN_CORPUS]
        inst = cls()
        inst.fit(texts, labels)
        return inst
