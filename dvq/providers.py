"""Provider-agnostic model access.

litellm is the default backend: one async interface over Anthropic, OpenAI,
Google, DeepSeek, Mistral, and Meta's Llama (via Together/Fireworks). Vals AI's
model-library is a drop-in alternative (`uv sync --extra vals`); the internal
`Completion` shape is the seam that keeps the harness independent of either.

Structured output is done the portable way: ask for JSON, validate with
pydantic, retry once on a parse failure. That is the instructor/Pydantic pattern
by hand, and it works across every provider rather than only the ones with a
native JSON mode.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Completion:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


async def complete(
    model: str,
    system: str,
    user: str,
    image_b64: Optional[str] = None,
    max_tokens: int = 1600,
    temperature: float = 0.0,
) -> Completion:
    """One model call. `model` is a litellm id like 'anthropic/claude-sonnet-4-5'
    or 'openai/gpt-5.5'. `image_b64` (PNG, no data-uri prefix) enables the vision judge."""
    import litellm

    content: list | str
    if image_b64:
        content = [
            {"type": "text", "text": user},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
        ]
    else:
        content = user

    messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
    t0 = time.perf_counter()
    resp = await litellm.acompletion(model=model, messages=messages, max_tokens=max_tokens, temperature=temperature)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    tokens_in = getattr(usage, "prompt_tokens", 0) or 0
    tokens_out = getattr(usage, "completion_tokens", 0) or 0
    try:
        cost = litellm.completion_cost(completion_response=resp) or 0.0
    except Exception:
        cost = 0.0
    return Completion(text=text, model=model, tokens_in=tokens_in, tokens_out=tokens_out,
                      cost_usd=float(cost), latency_ms=latency_ms)
