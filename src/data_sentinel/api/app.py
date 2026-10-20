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
import contextlib
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
from data_sentinel.persistence.investigations import (
    DEFAULT_DB,
    InvestigationStore,
)
from data_sentinel.persistence.investigations import (
    State as InvState,
)

MAX_PAYLOAD = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_EXTS = {".json", ".log", ".txt", ".sql", ".yaml", ".yml", ".plan",
                     ".xml", ".csv", ".jsonl"}

API_VERSION = "v1"

_RATE_BUCKETS: dict[str, list[float]] = {}
_AUDIT_LOG: list[dict[str, Any]] = []

_TOKEN_TTL_S = 4 * 3600  # session tokens expire after 4h
_TOKEN_FILE = Path.home() / ".data-sentinel" / "session-token"


class SessionAuth:
    """Local-session bearer auth (§1.2).

    High-entropy token generated per server boot (or read from env /
    token file). Rotates via TTL — after expiry a fresh token is issued
    and old requests are rejected. No secrets in URLs or logs.
    """

    def __init__(self) -> None:
        self._token = self._load() or secrets.token_urlsafe(32)
        self._issued = time.time()
        self._persist()

    def _load(self) -> str | None:
        import os
        env = os.environ.get("DATA_SENTINEL_TOKEN")
        if env:
            return env
        try:
            return _TOKEN_FILE.read_text().strip() or None
        except OSError:
            return None

    def _persist(self) -> None:
        try:
            _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            _TOKEN_FILE.write_text(self._token)
            _TOKEN_FILE.chmod(0o600)
        except OSError:
            pass  # session-only token still works in-memory

    @property
    def token(self) -> str:
        if time.time() - self._issued > _TOKEN_TTL_S:
            self._token = secrets.token_urlsafe(32)
            self._issued = time.time()
            self._persist()
        return self._token

    def check(self, presented: str | None) -> bool:
        if not presented:
            return False
        return secrets.compare_digest(presented, self.token)


def _audit(client: str, path: str, status: int) -> None:
    """Append-only audit trail (bounded, in-memory)."""
    if len(_AUDIT_LOG) < 10_000:
        _AUDIT_LOG.append({"client": client, "path": path,
                           "status": status, "ts": time.time()})


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


# Credential fields — always masked (§1.5, schema-classified).
_CREDENTIAL_KEYS = {
    "password", "passwd", "secret", "access_key", "secret_key",
    "aws_secret_access_key", "aws_access_key_id", "private_key",
    "credential", "credentials", "token", "access_token", "refresh_token",
    "id_token", "session_token", "api_key", "apikey", "auth_token",
    "bearer_token", "client_secret",
}

# Usage/metric fields containing "token" that are NOT secrets.
_SAFE_TOKEN_KEYS = {
    "tokens_used", "token_usage", "input_tokens", "output_tokens",
    "token_budget", "tokens_per_second", "token_count", "max_tokens",
    "context_tokens", "total_tokens",
}


def _secretish(key: str) -> bool:
    k = key.lower()
    if k in _SAFE_TOKEN_KEYS:
        return False
    if k in _CREDENTIAL_KEYS:
        return True
    # substring fallback for unknown compound credential fields, e.g.
    # "db_password_hash" — but never bare "token*" metric suffixes.
    return any(s in k for s in ("password", "secret", "credential",
                                "private_key", "access_key"))


class InvestigationCreate(BaseModel):
    problem: str = Field(min_length=1, max_length=4000)
    files: dict[str, str] = Field(default_factory=dict)


class InvestigationState:
    """Persistent investigation state (§2) — SQLite-backed, with live
    queues only for subscribers currently attached."""

    def __init__(self, store: InvestigationStore | None = None) -> None:
        self.store = store or InvestigationStore()
        self.queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        # hydrate in-memory reports dict from persisted rows
        for rec in self.store.list_all():
            if rec.report is not None:
                pass  # reports read lazily via store.get()

    def emit(self, inv_id: str, event: str, data: dict[str, Any]) -> None:
        seq = self.store.emit(inv_id, event, _redact(data))
        q = self.queues.get(inv_id)
        if q is not None:
            q.put_nowait({"seq": seq, "event": event,
                          "data": _redact(data), "ts": time.time()})

    @property
    def reports(self) -> dict[str, Any]:
        return {}  # compat shim — real data via store

    @property
    def events(self) -> dict[str, asyncio.Queue[dict[str, Any]]]:
        return self.queues


def create_app(allowed_roots: list[str] | None = None,
               *, require_auth: bool = True,
               db_path: Path | str | None = None,
               store: InvestigationStore | None = None) -> FastAPI:
    roots = [Path(r) for r in (allowed_roots or
                               [str(Path.cwd()), str(Path.home() / ".cache")])]
    state = InvestigationState(
        store=store or InvestigationStore(db_path or DEFAULT_DB))
    auth = SessionAuth()
    _LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "testclient",
                    "testserver"}
    app = FastAPI(title="Sentinel Control Center API", version=API_VERSION,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")

    app.add_middleware(
        CORSMiddleware, allow_origins=[
            "http://localhost:4200", "http://127.0.0.1:4200"],
        allow_methods=["GET", "POST"], allow_headers=["*"], max_age=600)

    @app.middleware("http")
    async def local_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Host/Origin guards — DNS rebinding + CSRF defense (§1.2)."""
        host = (request.headers.get("host") or "").split(":")[0].lower()
        if host and host not in _LOCAL_HOSTS and require_auth:
            _audit("?", request.url.path, 403)
            return JSONResponse({"detail": "non-local host rejected"}, 403)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin:
                o_host = origin.split("//")[-1].split(":")[0].lower()
                if o_host not in _LOCAL_HOSTS:
                    _audit("?", request.url.path, 403)
                    return JSONResponse(
                        {"detail": "cross-origin mutation rejected"}, 403)
        return await call_next(request)

    @app.middleware("http")
    async def bearer_auth(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Bearer session auth on /api/v1/* except health/docs (§1.2)."""
        path = request.url.path
        open_paths = {"/api/v1/health", "/api/docs",
                      "/api/openapi.json", "/api/docs/oauth2-redirect"}
        if (require_auth and path.startswith("/api/v1")
                and path not in open_paths):
            header = request.headers.get("authorization", "")
            presented = header.removeprefix("Bearer ").strip() \
                if header.lower().startswith("bearer") else None
            if not auth.check(presented):
                client = (request.client.host
                          if request.client else "unknown")
                _audit(client, path, 401)
                return JSONResponse({"detail": "unauthorized"}, 401)
        return await call_next(request)

    @app.middleware("http")
    async def payload_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        length = request.headers.get("content-length")
        if length and int(length) > MAX_PAYLOAD:
            return JSONResponse({"detail": "payload too large"}, 413)
        return await call_next(request)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Token-bucket per client — 120 req/min, local API scope."""
        client = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = _RATE_BUCKETS.setdefault(client, [])
        bucket[:] = [t for t in bucket if now - t < 60.0]
        if len(bucket) >= 120:
            _audit(client, request.url.path, 429)
            return JSONResponse({"detail": "rate limit exceeded"}, 429)
        bucket.append(now)
        response = await call_next(request)
        _audit(client, request.url.path, response.status_code)
        return response

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
        state.queues[inv_id] = q
        state.store.create(inv_id, body.problem)
        state.store.transition(inv_id, InvState.QUEUED)

        async def _run() -> None:
            state.emit(inv_id, "INVESTIGATION_STARTED",
                       {"investigation_id": inv_id})
            try:
                state.store.transition(inv_id, InvState.RUNNING)
                rep = await asyncio.to_thread(
                    investigate, body.problem, files)
                rep.investigation_id = inv_id
                rep.report_id = inv_id
                state.store.save_report(
                    inv_id, rep.model_dump(mode="json"))
                for t in rep.tools_used:
                    state.emit(inv_id, "TOOL_COMPLETED", {"tool": t})
                for h in rep.hypotheses_supported:
                    state.emit(inv_id, "HYPOTHESIS_CREATED",
                               h.model_dump(mode="json"))
                state.store.transition(inv_id, InvState.COMPLETED)
                state.emit(inv_id, "INVESTIGATION_COMPLETED",
                           {"findings": len(rep.findings)})
            except Exception as exc:
                with contextlib.suppress(ValueError):
                    state.store.transition(inv_id, InvState.FAILED)
                state.emit(inv_id, "INVESTIGATION_FAILED",
                           {"error": str(exc)})
            finally:
                q.put_nowait({"event": "__end__", "data": {}, "ts": 0.0})

        asyncio.get_running_loop().create_task(_run())
        return {"investigation_id": inv_id, "status": "running"}

    @app.get("/api/v1/investigations")
    def list_investigations() -> list[dict[str, Any]]:
        return [{"investigation_id": r.investigation_id,
                 "status": r.state.value.lower(),
                 "created": r.created_at, "updated": r.updated_at,
                 "problem": r.problem}
                for r in state.store.list_all()]

    @app.get("/api/v1/investigations/{inv_id}")
    def get_investigation(inv_id: str) -> dict[str, Any]:
        rec = state.store.get(inv_id)
        if rec is None:
            raise HTTPException(404, "investigation not found")
        if rec.report is None:
            return {"investigation_id": inv_id,
                    "status": rec.state.value.lower()}
        report = dict(rec.report)
        report["status"] = rec.state.value.lower()
        return _redact(report)

    @app.get("/api/v1/investigations/{inv_id}/stream")
    async def stream(request: Request, inv_id: str) -> StreamingResponse:
        if state.store.get(inv_id) is None:
            raise HTTPException(404, "investigation not found")
        last_id = request.headers.get("last-event-id")
        after = int(last_id) if last_id and last_id.isdigit() else 0

        async def gen() -> AsyncIterator[str]:
            # replay persisted events first (§2.4)
            for e in state.store.events(inv_id, after_seq=after):
                yield (f"id: {e['seq']}\nevent: {e['event']}\n"
                       f"data: {json.dumps(e['data'])}\n\n")
            rec = state.store.get(inv_id)
            if rec is not None and rec.state in {
                    InvState.COMPLETED, InvState.FAILED,
                    InvState.CANCELLED}:
                return
            q = state.queues.get(inv_id)
            if q is None:
                return
            while True:
                item = await q.get()
                if item["event"] == "__end__":
                    break
                yield (f"id: {item['seq']}\nevent: {item['event']}\n"
                       f"data: {json.dumps(item['data'])}\n\n")

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/v1/investigations/{inv_id}/graph")
    def investigation_graph(inv_id: str) -> dict[str, Any]:
        """Evidence graph for an investigation — delegates to core."""
        from dataclasses import asdict

        from data_sentinel.core.contracts.agent import InvestigationReport
        from data_sentinel.diagnostics.incident import build_incident_graph, context_from_hints
        rec = state.store.get(inv_id)
        if rec is None or rec.report is None:
            raise HTTPException(404, "investigation not found")
        rep = InvestigationReport.model_validate(rec.report)
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
    app.state.auth = auth
    return app
