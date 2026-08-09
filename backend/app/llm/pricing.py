"""Cost estimation for the LLM layer (Phase 8 — `WorkflowRun.total_cost_usd`
had been hardcoded to 0.0 since Phase 4, since nothing ever computed a real
figure). Ollama is local and free by construction — everything routed
through it costs exactly $0 always, not an approximation of a small
number. Cloud providers get a real, if approximate, estimate: blended
per-1,000-token rates, since Ollama's own /api/chat response (the only
place tokens_used is populated today) reports one combined prompt+eval
count rather than separate input/output counts to price individually.
Rates below are order-of-magnitude, current as of when this was written —
meant for a realistic dashboard figure, not a billing-accurate one."""

_BLENDED_RATE_PER_1K_TOKENS: dict[tuple[str, str], float] = {
    ("anthropic", "claude-haiku"): 0.0015,
    ("anthropic", "claude-sonnet"): 0.009,
    ("openai", "gpt-4o-mini"): 0.00035,
    ("openai", "gpt-4o"): 0.0075,
    ("groq", "llama3.1-8b"): 0.0002,
}


def estimate_cost_usd(provider: str, model: str, tokens_used: int | None) -> float:
    if provider == "ollama" or not tokens_used:
        return 0.0
    rate = _BLENDED_RATE_PER_1K_TOKENS.get((provider, model))
    if rate is None:
        # An unrecognized cloud model — report no cost rather than guess
        # at a rate, same "don't fake a number" principle as everywhere
        # else tokens_used/cost tracking has been built in this project.
        return 0.0
    return round(tokens_used / 1000 * rate, 6)
