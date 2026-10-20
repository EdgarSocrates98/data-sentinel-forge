"""Model provider abstraction (§3.3, §3.4).

Core depends only on the ModelProvider protocol. Providers are OPTIONAL:
offline profile never requires one. LocalProvider targets an Ollama-
compatible localhost HTTP endpoint (stdlib urllib only); StubProvider is
the deterministic test/dev provider.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Protocol, runtime_checkable

from data_sentinel.core.contracts.agent import ModelRequest, ModelResponse


class ProviderError(RuntimeError):
    pass


@runtime_checkable
class ModelProvider(Protocol):
    name: str

    def complete(self, req: ModelRequest) -> ModelResponse: ...

    def available(self) -> bool: ...


class StubProvider:
    """Deterministic echo provider for tests and offline runs."""

    name = "stub"

    def available(self) -> bool:
        return True

    def complete(self, req: ModelRequest) -> ModelResponse:
        approx = max(1, len(req.prompt) // 4)
        text = ("[stub] provider determinístico — sem LLM real. "
                f"prompt_chars={len(req.prompt)}")
        return ModelResponse(text=text, tokens_in=approx,
                             tokens_out=len(text) // 4,
                             model_id="stub", stop_reason="end")


class LocalProvider:
    """Ollama-compatible local endpoint (http://localhost:11434)."""

    name = "local"

    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "llama3.1", timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(  # noqa: S310 — localhost fixo
                    f"{self.base_url}/api/tags", timeout=3) as r:
                return bool(r.status == 200)
        except Exception:
            return False

    def complete(self, req: ModelRequest) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": req.model_id or self.model,
            "prompt": f"{req.system}\n\n{req.prompt}".strip(),
            "stream": False,
            "options": {"temperature": req.temperature,
                        "num_predict": req.max_tokens},
        }
        data = json.dumps(payload).encode()
        try:
            http_req = urllib.request.Request(  # noqa: S310
                f"{self.base_url}/api/generate", data=data,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(  # noqa: S310 — localhost only
                    http_req, timeout=self.timeout) as r:
                body = json.loads(r.read().decode())
        except Exception as exc:
            raise ProviderError(f"local provider falhou: {exc}") from exc
        return ModelResponse(
            text=body.get("response", ""),
            tokens_in=body.get("prompt_eval_count") or 0,
            tokens_out=body.get("eval_count") or 0,
            model_id=req.model_id or self.model,
            stop_reason="end" if body.get("done") else "length")


_PROVIDERS: dict[str, type[ModelProvider]] = {
    "stub": StubProvider,
    "local": LocalProvider,
}


def get_provider(name: str = "stub", **kw: Any) -> ModelProvider:
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ProviderError(f"provider desconhecido: {name}")
    return cls(**kw)


def route_profile(profile: str) -> str:
    """§3.4 — map routing profile to provider requirement.

    offline  -> none (deterministic only)
    economy  -> local only when needed
    balanced -> local allowed, budget-capped
    deep     -> local allowed, larger budgets (still capped)
    """
    return {
        "offline": "none",
        "economy": "optional-local",
        "balanced": "local",
        "deep": "local",
    }.get(profile, "none")
