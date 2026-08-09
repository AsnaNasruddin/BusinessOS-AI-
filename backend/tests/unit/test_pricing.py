from app.llm.pricing import estimate_cost_usd


def test_ollama_is_always_free():
    assert estimate_cost_usd("ollama", "llama3.1:8b", 50_000) == 0.0


def test_no_tokens_means_no_cost():
    assert estimate_cost_usd("anthropic", "claude-haiku", None) == 0.0
    assert estimate_cost_usd("anthropic", "claude-haiku", 0) == 0.0


def test_known_cloud_model_gets_a_real_estimate():
    cost = estimate_cost_usd("anthropic", "claude-haiku", 2000)
    assert cost == 0.003  # 2 * 0.0015


def test_unrecognized_cloud_model_reports_no_cost_rather_than_guessing():
    assert estimate_cost_usd("openai", "some-future-model", 5000) == 0.0
