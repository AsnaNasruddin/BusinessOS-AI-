import httpx

from app.llm.base import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    ProviderNotConfiguredError,
    ToolCall,
    ToolSpec,
)


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float,
        response_format: dict | None = None,
        tools: list[ToolSpec] | None = None,
    ) -> LLMResponse:
        payload = {
            "model": model,
            "messages": [_to_ollama_message(m) for m in messages],
            "options": {"temperature": temperature},
            "stream": False,
        }
        # Ollama's /api/chat accepts a JSON Schema directly as `format`,
        # constraining the model's output to conform to it — this is what
        # makes Phase 7's WorkflowPlan a real structured output instead of a
        # "please return JSON" instruction the model might ignore.
        if response_format is not None:
            payload["format"] = response_format
        # OpenAI-compatible function-calling shape — llama3.1 supports it
        # natively, which is what makes a real tool-calling loop possible
        # without a separate framework.
        if tools:
            payload["tools"] = [_to_ollama_tool(t) for t in tools]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise ProviderNotConfiguredError(
                f"Can't reach Ollama at {self._base_url} — is it running?"
            ) from exc

        response.raise_for_status()
        data = response.json()
        message = data["message"]
        tokens_used = data.get("prompt_eval_count", 0) + data.get("eval_count", 0) or None

        tool_calls = None
        raw_tool_calls = message.get("tool_calls")
        if raw_tool_calls:
            # Ollama doesn't assign call ids the way OpenAI does — synthesize
            # stable ones so the executor loop has something to echo back in
            # the follow-up "tool" role message.
            tool_calls = [
                ToolCall(
                    id=f"call_{i}",
                    name=call["function"]["name"],
                    arguments=call["function"].get("arguments", {}),
                )
                for i, call in enumerate(raw_tool_calls)
            ]

        return LLMResponse(
            content=message.get("content", ""),
            model=model,
            tokens_used=tokens_used,
            tool_calls=tool_calls,
        )


def _to_ollama_message(message: LLMMessage) -> dict:
    out: dict = {"role": message.role, "content": message.content}
    if message.tool_calls:
        out["tool_calls"] = [
            {"function": {"name": tc.name, "arguments": tc.arguments}} for tc in message.tool_calls
        ]
    if message.role == "tool" and message.name:
        out["name"] = message.name
    return out


def _to_ollama_tool(tool: ToolSpec) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }
