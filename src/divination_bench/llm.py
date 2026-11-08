"""Minimal OpenRouter chat client with retries and an offline mock provider."""

from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MOCK_PREFIX = "mock/"


@dataclass
class ChatResult:
    text: str
    usage: dict | None
    model: str


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (408, 409, 429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.TransportError, EmptyResponseError))


class EmptyResponseError(RuntimeError):
    pass


class BudgetExceededError(RuntimeError):
    pass


class LLMClient:
    """Thread-safe; share one instance across worker threads so the budget is global."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 600.0,
        reasoning_effort: str | None = None,
        budget_usd: float | None = None,
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.reasoning_effort = reasoning_effort
        self.budget_usd = budget_usd
        self.spent_usd = 0.0
        self._lock = threading.Lock()
        self._http = httpx.Client(timeout=timeout)

    def _check_budget(self) -> None:
        if self.budget_usd is not None and self.spent_usd >= self.budget_usd:
            raise BudgetExceededError(
                f"Budget of ${self.budget_usd:.2f} reached (spent ${self.spent_usd:.2f})"
            )

    def chat(
        self,
        model: str,
        messages: list[dict],
        *,
        temperature: float | None = None,
        max_tokens: int = 8000,
        seed: int | None = None,
    ) -> ChatResult:
        if model.startswith(MOCK_PREFIX):
            return _mock_chat(model, messages)
        if model.endswith(":online"):
            raise ValueError(
                f"{model}: web search would leak outcomes; use the plain model ID"
            )
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Export it, or use a 'mock/...' model for dry runs."
            )
        self._check_budget()
        result = self._chat_remote(model, messages, temperature, max_tokens, seed)
        cost = (result.usage or {}).get("cost") or 0.0
        with self._lock:
            self.spent_usd += float(cost)
        return result

    @retry(
        retry=retry_if_exception(_retryable),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def _chat_remote(
        self, model, messages, temperature, max_tokens, seed
    ) -> ChatResult:
        body: dict = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "usage": {"include": True},
        }
        if temperature is not None:
            body["temperature"] = temperature
        if seed is not None:
            body["seed"] = seed
        if self.reasoning_effort:
            body["reasoning"] = {"effort": self.reasoning_effort}
        resp = self._http.post(
            OPENROUTER_URL,
            json=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/lcrh/divination_bench",
                "X-Title": "divination-bench",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"OpenRouter error for {model}: {data['error']}")
        text = (data["choices"][0]["message"].get("content") or "").strip()
        if not text:
            raise EmptyResponseError(f"Empty completion from {model}")
        return ChatResult(
            text=text, usage=data.get("usage"), model=data.get("model", model)
        )


def _mock_chat(model: str, messages: list[dict]) -> ChatResult:
    """Deterministic canned output so the full pipeline runs without an API key.

    The system prompt of each pipeline stage contains a `[[MOCK:<kind>]]` marker
    telling the mock which output format to produce.
    """
    prompt = "\n".join(m["content"] for m in messages)
    h = int(hashlib.sha256((model + prompt).encode()).hexdigest(), 16)
    if "[[MOCK:judge]]" in prompt:
        labels = sorted(
            {
                line.split("]")[0][1:]
                for line in prompt.splitlines()
                if line.startswith("[Item ")
            }
        )
        order = sorted(
            labels, key=lambda lab: hashlib.sha256((lab + str(h)).encode()).hexdigest()
        )
        items = ",".join(
            f'{{"label": "{lab}", "rank": {i + 1}, "score": {max(0, 9 - 3 * i)}, '
            f'"rationale": "mock rationale"}}'
            for i, lab in enumerate(order)
        )
        text = f'{{"ranking": [{items}]}}'
    elif "[[MOCK:probe]]" in prompt:
        text = '{"knows_outcome": "no", "stated_answer": null, "training_cutoff_guess": "mock"}'
    else:
        text = (
            "<reading>The signs point to upheaval followed by consolidation (mock reading).</reading>\n"
            "<prediction>The incumbent position holds, narrowly. (mock prediction)</prediction>\n"
            f"<answer>{'Yes' if h % 2 else 'No'}</answer>"
        )
    return ChatResult(text=text, usage={"mock": True}, model=model)
