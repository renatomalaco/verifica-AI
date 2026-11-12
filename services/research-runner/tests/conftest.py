import json

import pytest
import respx

from research_runner.settings import ResearchSettings

GEMINI_BASE = "https://gemini.test"
JEV_BASE = "https://jev.test"
GEMINI = dict(
    GEMINI_API_KEY="k",
    GEMINI_BASE_URL=GEMINI_BASE,
    GEMINI_MODEL="gemini-x",
    GEMINI_PRICE_INPUT_USD_PER_1M=0.30,
    GEMINI_PRICE_OUTPUT_USD_PER_1M=2.50,
    GEMINI_PRICE_DATE="2026-11-01",
)
JEV = dict(
    AI_PROVIDER="jev",
    JEV_API_KEY="k",
    JEV_BASE_URL=JEV_BASE,
    JEV_PRICE_USD_PER_1K_CALLS=2.0,
    JEV_PRICE_DATE="2026-11-01",
)
GEMINI_CALL_USD = 0.0013  # 1000 input and 400 billed output tokens at the GEMINI prices above
JEV_CALL_USD = 0.002


@pytest.fixture(autouse=True)
def no_real_providers(monkeypatch):
    # The author's .env may hold real keys: unit tests must never reach a paid model.
    for name in ("GEMINI_API_KEY", "JEV_API_KEY"):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("AI_PROVIDER", "fake")


def settings(**overrides) -> ResearchSettings:
    return ResearchSettings(_env_file=None, **overrides)


class ModelStub:
    """A mocked provider endpoint: what it answers and what it was sent."""

    def __init__(self, route: respx.Route, reply) -> None:
        self.route = route
        self._reply = reply

    def answers(self, scam_probability: float) -> None:
        self.route.respond(json=self._reply(scam_probability))

    def fails_with(self, **failure) -> None:
        if "side_effect" in failure:
            self.route.mock(side_effect=failure["side_effect"])
            return
        self.route.respond(**failure)

    def sent_texts(self) -> list[str]:
        return [call.request.content.decode("utf-8") for call in self.route.calls]


def _gemini_reply(scam_probability: float) -> dict:
    answer = {
        "is_phishing": scam_probability,
        "requires_visual_inspection": 0.0,
        "persuasion": "urgencia",
    }
    return {
        "candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}],
        "usageMetadata": {
            "promptTokenCount": 1000,
            "candidatesTokenCount": 100,
            "thoughtsTokenCount": 300,
        },
    }


def _jev_reply(scam_probability: float) -> dict:
    return {
        "answers": {
            "is_phishing": {"probability": scam_probability},
            "persuasion": {"selected": "urgencia"},
        }
    }


@pytest.fixture
def gemini():
    with respx.mock(base_url=GEMINI_BASE, assert_all_called=False) as mock:
        yield ModelStub(mock.post("/v1beta/models/gemini-x:generateContent"), _gemini_reply)


@pytest.fixture
def jev():
    with respx.mock(base_url=JEV_BASE, assert_all_called=False) as mock:
        yield ModelStub(mock.post("/v1/systemone"), _jev_reply)


@pytest.fixture
def make_settings():
    return settings


@pytest.fixture
def gemini_env():
    return GEMINI


@pytest.fixture
def jev_env():
    return JEV
