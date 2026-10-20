"""FastAPI app factory for the Sentinel Control Center.

Security defaults (spec 06.1/3.4):
- bind 127.0.0.1 by default (uvicorn invocation, documented)
- restrictive CORS (localhost origins only)
- payload limit via middleware
- path traversal protection on file inputs
- secret redaction on all emitted payloads
- no AWS credentials ever exposed
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TypeVar, cast

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "Control Center API requires the `api` extra: "
        "pip install 'data-sentinel[api]'"
    ) from exc

from data_sentinel.core.contracts.enums import Severity

MAX_PAYLOAD = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_EXTS = {".json", ".log", ".txt", ".sql", ".yaml", ".yml", ".plan",
                     ".xml", ".csv", ".jsonl"}

API_VERSION = "v1"


def _safe_path(raw: str, roots: list[Path]) -> Path:
    """Resolve *raw* and require it to live under an allowed root."""
    p = Path(raw).expanduser().resolve()
    for root in roots:
        try:
            p.relative_to(root.resolve())
            return p
        except ValueError:
            continue
    raise HTTPException(403, f"path outside allowed roots: {raw}")


_T = TypeVar("_T")


def _redact(obj: _T) -> _T:
    """Best-effort secret redaction on outgoing payloads."""
    if isinstance(obj, dict):
        return cast(_T, {k: ("***" if _secretish(k) else _redact(v))
                         for k, v in obj.items()})
    if isinstance(obj, list):
        return cast(_T, [_redact(v) for v in obj])
    return obj


_SECRET_KEYS = {"password", "secret", "token", "access_key", "secret_key",
                "aws_secret", "private_key", "credential"}


def _secretish(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in _SECRET_KEYS)


class InvestigationCreate(BaseModel):
    problem: str = Field(min_length=1, max_length=4000)
    files: dict[str, str] = Field(default_factory=dict)


class InvestigationState:
    """In-memory investigation store — per-process, truthful about scope."""

    def __init__(self) -> None:
        self.reports: dict[str, Any] = {}
        self.events: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self.created: dict[str, float] = {}

    def emit(self, inv_id: str, event: str, data: dict[str, Any]) -> None:
        q = self.events.get(inv_id)
        if q is not None:
            q.put_nowait({"event": event, "data": _redact(data),
                          "ts": time.time()})


def create_app(allowed_roots: list[str] | None = None) -> FastAPI:
    roots = [Path(r) for r in (allowed_roots or
                               [str(Path.cwd()), str(Path.home() / ".cache")])]
    state = InvestigationState()
    app = FastAPI(title="Sentinel Control Center API", version=API_VERSION,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")

    app.add_middleware(
        CORSMiddleware, allow_origins=[
            "http://localhost:4200", "http://127.0.0.1:4200"],
        allow_methods=["GET", "POST"], allow_headers=["*"], max_age=600)

    @app.middleware("http")
    async def payload_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        length = request.headers.get("content-length")
        if length and int(length) > MAX_PAYLOAD:
            return JSONResponse({"detail": "payload too large"}, 413)
        return await call_next(request)

    # ---- health / capabilities ----

    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        from data_sentinel import __version__
        return {"status": "ok", "version": __version__, "api": API_VERSION}

    @app.get("/api/v1/capabilities")
    def capabilities() -> list[dict[str, Any]]:
        from data_sentinel.diagnostics.capabilities import all_descriptors
        return [c.model_dump(mode="json") for c in all_descriptors()]

    @app.get("/api/v1/tools")
    def tools() -> list[dict[str, Any]]:
        from data_sentinel.tools.registry import build_default_registry
        return build_default_registry().to_mcp_manifest()

    @app.get("/api/v1/agents")
    def agents() -> list[dict[str, Any]]:
        from data_sentinel.agents.specialists import specialist_descriptors
        return [d.model_dump(mode="json") for d in specialist_descriptors()]

    # ---- investigations ----

    @app.post("/api/v1/investigations", status_code=201)
    async def create_investigation(body: InvestigationCreate) -> dict[str, Any]:
        from data_sentinel.agents.investigator import investigate

        inv_id = f"inv-{secrets.token_hex(6)}"
        files: dict[str, str] = {}
        for tool_id, raw in body.files.items():
            p = _safe_path(raw, roots)
            if p.suffix.lower() not in ALLOWED_FILE_EXTS:
                raise HTTPException(
                    400, f"file type not allowed: {p.suffix}")
            if not p.is_file():
                raise HTTPException(404, f"file not found: {raw}")
            files[tool_id] = str(p)

        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        state.events[inv_id] = q
        state.created[inv_id] = time.time()

        async def _run() -> None:
            state.emit(inv_id, "INVESTIGATION_STARTED",
                       {"investigation_id": inv_id})
            try:
                rep = await asyncio.to_thread(
                    investigate, body.problem, files)
                rep.investigation_id = inv_id
                rep.report_id = inv_id
                state.reports[inv_id] = rep
                for t in rep.tools_used:
                    state.emit(inv_id, "TOOL_COMPLETED", {"tool": t})
                for h in rep.hypotheses_supported:
                    state.emit(inv_id, "HYPOTHESIS_CREATED",
                               h.model_dump(mode="json"))
                state.emit(inv_id, "INVESTIGATION_COMPLETED",
                           {"findings": len(rep.findings)})
            except Exception as exc:
                state.emit(inv_id, "INVESTIGATION_FAILED", {"error": str(exc)})
            finally:
                q.put_nowait({"event": "__end__", "data": {}, "ts": 0.0})

        asyncio.get_running_loop().create_task(_run())
        return {"investigation_id": inv_id, "status": "running"}

    @app.get("/api/v1/investigations")
    def list_investigations() -> list[dict[str, Any]]:
        return [{"investigation_id": i, "status": "completed",
                 "created": state.created.get(i)}
                for i in sorted(state.reports)]

    @app.get("/api/v1/investigations/{inv_id}")
    def get_investigation(inv_id: str) -> dict[str, Any]:
        rep = state.reports.get(inv_id)
        if rep is None:
            if inv_id in state.events:
                return {"investigation_id": inv_id, "status": "running"}
            raise HTTPException(404, "investigation not found")
        return _redact(rep.model_dump(mode="json"))

    @app.get("/api/v1/investigations/{inv_id}/stream")
    async def stream(inv_id: str) -> StreamingResponse:
        if inv_id not in state.events and inv_id not in state.reports:
            raise HTTPException(404, "investigation not found")

        async def gen() -> AsyncIterator[str]:
            q = state.events.get(inv_id)
            if q is None:
                yield 'event: INVESTIGATION_COMPLETED\ndata: {}\n\n'
                return
            while True:
                item = await q.get()
                if item["event"] == "__end__":
                    break
                yield (f"event: {item['event']}\n"
                       f"data: {json.dumps(item['data'])}\n\n")

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/v1/investigations/{inv_id}/graph")
    def investigation_graph(inv_id: str) -> dict[str, Any]:
        """Evidence graph for an investigation — delegates to core."""
        from dataclasses import asdict

        from data_sentinel.diagnostics.incident import build_incident_graph, context_from_hints
        rep = state.reports.get(inv_id)
        if rep is None:
            raise HTTPException(404, "investigation not found")
        hints = dict(rep.context.get("hints", {}))
        ctx = context_from_hints(hints)
        g = build_incident_graph(ctx, rep.findings, rep.evidence)
        return {
            "investigation_id": inv_id,
            "nodes": [asdict(n) for n in g.nodes.values()],
            "edges": [asdict(e) for e in g.edges],
        }

    # ---- analyzer-backed read endpoints (thin delegation) ----

    @app.post("/api/v1/analyze/{analyzer_id}")
    def analyze(analyzer_id: str, body: dict[str, str]) -> dict[str, Any]:
        """Run one existing analyzer on an uploaded file path.

        ``body``: {"file": "/abs/path"}. Delegates to the analyzer
        registry — no logic duplicated here.
        """
        from data_sentinel.core.contracts.agent import ToolInvocation
        from data_sentinel.tools.registry import (
            build_default_registry,
            execute_tool,
        )
        tool_id = f"sentinel.{analyzer_id}"
        reg = build_default_registry()
        try:
            reg.get(tool_id)
        except Exception:
            raise HTTPException(404, f"unknown analyzer: {analyzer_id}") from None
        raw = body.get("file")
        if not raw:
            raise HTTPException(400, "file is required")
        p = _safe_path(raw, roots)
        if not p.is_file():
            raise HTTPException(404, "file not found")
        res = execute_tool(ToolInvocation(
            invocation_id=f"api-{secrets.token_hex(4)}",
            tool_id=tool_id, input={"file": str(p)}))
        if not res.ok:
            raise HTTPException(422, res.error or "analysis failed")
        out: dict[str, Any] = res.output if isinstance(res.output, dict) else {}
        return _redact(out)

    @app.get("/api/v1/severities")
    def severities() -> list[str]:
        return [s.value for s in Severity]

    app.state.investigations = state
    return app
