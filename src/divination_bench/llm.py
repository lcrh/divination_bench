"""Minimal OpenRouter chat client with retries and an offline mock provider."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from .store import append_line, now_iso

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
MOCK_PREFIX = "mock/"


@dataclass
class ChatResult:
    text: str
    usage: dict | None
    model: str


@dataclass
class DecisionResult:
    answers: dict
    usage: dict | None
    model: str
    raw: dict


class DecisionError(ValueError):
    """A Decisions response that lacks a usable typed answer."""


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
        ledger_path: str | Path | None = None,
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.reasoning_effort = reasoning_effort
        self.budget_usd = budget_usd
        self.ledger_path = ledger_path
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
        self._require_key()
        self._check_budget()
        result = self._chat_remote(model, messages, temperature, max_tokens, seed)
        self._record(model, result.usage)
        return result

    def decide(self, model: str, state: object, questions: dict) -> DecisionResult:
        """One OpenRouter Decisions call: typed questions about `state`, answered with
        probabilities instead of text (e.g. TypeSafe Jev)."""
        if model.startswith(MOCK_PREFIX):
            return _mock_decide(model, state, questions)
        self._require_key()
        self._check_budget()
        body = {"model": model, "state": state, "questions": questions}
        data = self._post(DECISIONS_URL, body)
        usage = data.get("usage")
        self._record(model, usage)
        answers = data.get("answers")
        if not isinstance(answers, dict):
            raise DecisionError(f"{model}: response has no answers object")
        for key, q in questions.items():
            a = answers.get(key)
            if not isinstance(a, dict) or a.get("type") != q["type"]:
                raise DecisionError(f"{model}: missing or mistyped answer for {key!r}")
        return DecisionResult(answers, usage, data.get("model", model), data)

    def _require_key(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Export it, or use a 'mock/...' model for dry runs."
            )

    def _record(self, model: str, usage: dict | None) -> None:
        cost = float((usage or {}).get("cost") or 0.0)
        with self._lock:
            self.spent_usd += cost
        if self.ledger_path is not None:
            append_line(
                self.ledger_path,
                json.dumps({"model": model, "cost": cost, "created_at": now_iso()}),
            )

    @retry(
        retry=retry_if_exception(_retryable),
        wait=wait_exponential(multiplier=2, min=4, max=120),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def _post(self, url: str, body: dict) -> dict:
        resp = self._http.post(url, json=body, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"OpenRouter error for {body['model']}: {data['error']}")
        return data

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/lcrh/divination_bench",
            "X-Title": "divination-bench",
        }

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
        resp = self._http.post(OPENROUTER_URL, json=body, headers=self._headers())
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


def ledger_cost(path: str | Path) -> float:
    """Total cost of every paid call recorded in a spend ledger, including calls whose
    output was later discarded (parse failures, retries)."""
    path = Path(path)
    if not path.exists():
        return 0.0
    return sum(
        float(json.loads(line).get("cost") or 0.0)
        for line in path.read_text().splitlines()
        if line.strip()
    )


def _mock_decide(model: str, state: object, questions: dict) -> DecisionResult:
    """Deterministic Choice / Score answers shaped like the live API's."""
    blob = json.dumps(state, sort_keys=True)
    answers = {}
    for key, q in questions.items():
        h = int(hashlib.sha256((model + key + blob).encode()).hexdigest(), 16)
        if q["type"] == "choice":
            options = sorted(q["criteria"])
            weights = [
                1 + int(hashlib.sha256((str(h) + o).encode()).hexdigest(), 16) % 7
                for o in options
            ]
            probs = {o: w / sum(weights) for o, w in zip(options, weights, strict=True)}
            answers[key] = {
                "type": "choice",
                "choice": max(probs, key=probs.__getitem__),
                "probabilities": probs,
                "confidence": 0.5,
            }
            continue
        n = len(q["criteria"])
        top = h % n
        probs = {str(i): 0.0 for i in range(n)}
        probs[str(top)] = 0.8
        probs[str((top + 1) % n)] = 0.2
        answers[key] = {
            "type": "score",
            "score": sum(int(i) * p for i, p in probs.items()),
            "probabilities": probs,
            "legend": {str(i): c for i, c in enumerate(q["criteria"])},
            "confidence": 0.6,
        }
    raw = {"model": model, "answers": answers, "usage": {"mock": True}}
    return DecisionResult(answers, {"mock": True}, model, raw)


def _mock_chat(model: str, messages: list[dict]) -> ChatResult:
    """Deterministic canned output so the full pipeline runs without an API key.

    The system prompt of each pipeline stage contains a `[[MOCK:<kind>]]` marker
    telling the mock which output format to produce.
    """
    prompt = "\n".join(m["content"] for m in messages)
    h = int(hashlib.sha256((model + prompt).encode()).hexdigest(), 16)
    if "[[MOCK:probe]]" in prompt:
        text = '{"knows_outcome": "no", "stated_answer": null, "training_cutoff_guess": "mock"}'
    else:
        text = (
            "<reading>The signs point to upheaval followed by consolidation (mock reading).</reading>\n"
            "<prediction>The incumbent position holds, narrowly. (mock prediction)</prediction>\n"
            f"<answer>{'Yes' if h % 2 else 'No'}</answer>"
        )
    return ChatResult(text=text, usage={"mock": True}, model=model)
