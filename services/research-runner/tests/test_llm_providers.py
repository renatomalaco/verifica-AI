import pytest

from research_runner.infrastructure.llm_providers import providers_from_settings

ENVELOPE = "<untrusted_inspection_data>manda um pix urgente</untrusted_inspection_data>"


def test_without_keys_no_model_is_called_and_the_reason_is_kept(make_settings):
    providers = providers_from_settings(make_settings())
    assert providers.pure_vlm is None
    assert providers.triage is None
    assert "GEMINI_API_KEY" in providers.pure_vlm_missing


def test_a_key_without_prices_does_not_run_because_the_cost_would_be_unmeasured(make_settings):
    providers = providers_from_settings(make_settings(GEMINI_API_KEY="k"))
    assert providers.pure_vlm is None
    assert "GEMINI_PRICE_INPUT_USD_PER_1M" in providers.pure_vlm_missing
    assert "GEMINI_PRICE_DATE" in providers.pure_vlm_missing


def test_gemini_with_prices_runs_mode_2_and_describes_model_and_price_date(make_settings, gemini_env):
    providers = providers_from_settings(make_settings(**gemini_env))
    assert providers.pure_vlm.description == {
        "provider": "gemini",
        "model": "gemini-x",
        "input_usd_per_1m": 0.30,
        "output_usd_per_1m": 2.50,
        "price_date": "2026-11-01",
    }
    # The triage provider follows AI_PROVIDER, exactly as ai-gateway does.
    assert providers.triage is None
    assert "AI_PROVIDER" in providers.triage_missing


def test_ai_provider_gemini_also_drives_the_cascade_triage(make_settings, gemini_env):
    providers = providers_from_settings(make_settings(**gemini_env, AI_PROVIDER="gemini"))
    assert providers.triage.description["model"] == "gemini-x"


def test_jev_needs_its_key_and_a_price_per_call(make_settings, jev_env):
    unpriced = providers_from_settings(make_settings(AI_PROVIDER="jev", JEV_API_KEY="k"))
    priced = providers_from_settings(make_settings(**jev_env))

    assert unpriced.triage is None
    assert "JEV_PRICE_USD_PER_1K_CALLS" in unpriced.triage_missing
    assert priced.triage.description == {
        "provider": "jev",
        "model": "jev-latest",
        "usd_per_1k_calls": 2.0,
        "price_date": "2026-11-01",
    }


def test_pause_between_model_calls_is_configurable(make_settings):
    assert providers_from_settings(make_settings(RESEARCH_LLM_PAUSE_SECONDS=6.5)).pause_seconds == 6.5


async def test_a_gemini_call_returns_the_answer_and_its_measured_cost(make_settings, gemini_env, gemini):
    gemini.answers(0.97)
    answer, cost = await providers_from_settings(make_settings(**gemini_env)).pure_vlm.call(ENVELOPE)
    assert answer.is_phishing == 0.97
    assert cost == pytest.approx(0.0013)  # 1000 input and 400 output tokens


async def test_a_jev_call_costs_its_price_per_call(make_settings, jev_env, jev):
    jev.answers(0.2)
    answer, cost = await providers_from_settings(make_settings(**jev_env)).triage.call(ENVELOPE)
    assert answer.is_phishing == 0.2
    assert cost == pytest.approx(0.002)


def test_empty_price_lines_copied_from_env_example_mean_not_set(make_settings):
    providers = providers_from_settings(
        make_settings(GEMINI_API_KEY="k", GEMINI_PRICE_INPUT_USD_PER_1M="", JEV_PRICE_USD_PER_1K_CALLS="")
    )
    assert "GEMINI_PRICE_INPUT_USD_PER_1M" in providers.pure_vlm_missing
