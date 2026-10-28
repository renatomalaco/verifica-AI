from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


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

    def scam_probability(self, text: str) -> float:
        if not self._is_fitted:
            raise RuntimeError("Classifier must be fitted before calling scam_probability.")
        probabilities = self.model.predict_proba(self.vectorizer.transform([text]))[0]
        return float(dict(zip(self.model.classes_, probabilities)).get("GOLPE", 0.0))
