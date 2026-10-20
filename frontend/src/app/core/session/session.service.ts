import { Injectable, computed, inject, signal } from "@angular/core";
import { catchError, map, of } from "rxjs";
import type { Observable } from "rxjs";

import { ApiService } from "../api.service";

const STORAGE_TOKEN_KEY = "ds-session-token";
const STORAGE_ESTABLISHED_KEY = "ds-session-established-at";

/**
 * Backend session TTL (bearer_auth middleware, src/data_sentinel/api/app.py
 * §1.2): tokens are accepted for 4 hours from issuance. The API does not
 * return an explicit expiry alongside 401 responses (reported as a backend
 * contract gap in ds-0101), so the client tracks "established at" + this
 * constant and treats expiry honestly: once elapsed, the session is cleared
 * client-side even before the server actually rejects the token.
 */
export const SESSION_TTL_MS = 4 * 60 * 60 * 1000;

export type SessionStatus = "unknown" | "authenticated" | "expired" | "unauthenticated";

/**
 * Bearer-token session state (ADR-0014). The token lives in
 * `sessionStorage` only — never in the URL, query string, or
 * `localStorage` — and is cleared on tab close, logout, 401, or TTL
 * elapse. `establish()` is the only way to populate the token, and it
 * always validates against a real authenticated endpoint first so a
 * bad token is never persisted.
 */
@Injectable({ providedIn: "root" })
export class SessionService {
  private readonly api = inject(ApiService);

  private readonly _token = signal<string | null>(readStoredToken());
  private readonly _establishedAt = signal<number | null>(readStoredEstablishedAt());
  private readonly _expired = signal(false);

  /** Current bearer token, or `null` when there is no active session. */
  readonly token = this._token.asReadonly();

  /** `true` once a token is present and the client-side TTL has not elapsed. */
  readonly isAuthenticated = computed(() => {
    if (this._expired()) return false;
    return this._token() !== null && !this.isExpiredAt(this._establishedAt());
  });

  /** Absolute time (ms epoch) the current session will stop being honored. */
  readonly expiresAt = computed<number | null>(() => {
    const establishedAt = this._establishedAt();
    return establishedAt === null ? null : establishedAt + SESSION_TTL_MS;
  });

  /** `true` once a session existed and has since expired (client TTL or 401). */
  readonly isExpired = this._expired.asReadonly();

  constructor() {
    // A token restored from a previous tab/reload may already be past its
    // client-side TTL — treat it as expired rather than silently valid.
    if (this._token() !== null && this.isExpiredAt(this._establishedAt())) {
      this.clear();
      this._expired.set(true);
    }
  }

  /**
   * Validate `token` against `GET /api/v1/capabilities` (requires a real
   * bearer token) and, only on success, persist it to `sessionStorage` and
   * mark the session established "now". Never stores on failure.
   */
  establish(token: string): Observable<boolean> {
    const trimmed = token.trim();
    if (!trimmed) return of(false);
    return this.api.validateToken(trimmed).pipe(
      map(() => {
        this.persist(trimmed);
        return true;
      }),
      catchError(() => of(false)),
    );
  }

  /** Current bearer header value, or `null` when unauthenticated. */
  authorizationHeader(): string | null {
    const token = this._token();
    return token ? `Bearer ${token}` : null;
  }

  /** Called by the interceptor on a 401, and by the gate on manual logout. */
  clear(): void {
    this._token.set(null);
    this._establishedAt.set(null);
    try {
      sessionStorage.removeItem(STORAGE_TOKEN_KEY);
      sessionStorage.removeItem(STORAGE_ESTABLISHED_KEY);
    } catch {
      /* storage unavailable — non-fatal */
    }
  }

  /** Clear the session and record that it ended because it expired. */
  expire(): void {
    this.clear();
    this._expired.set(true);
  }

  /** Dismiss the "expired" banner once the user starts a new attempt. */
  acknowledgeExpiry(): void {
    this._expired.set(false);
  }

  private persist(token: string): void {
    this._expired.set(false);
    const establishedAt = Date.now();
    this._token.set(token);
    this._establishedAt.set(establishedAt);
    try {
      sessionStorage.setItem(STORAGE_TOKEN_KEY, token);
      sessionStorage.setItem(STORAGE_ESTABLISHED_KEY, String(establishedAt));
    } catch {
      /* storage unavailable — session still works for this page life */
    }
  }

  private isExpiredAt(establishedAt: number | null): boolean {
    if (establishedAt === null) return false;
    return Date.now() - establishedAt >= SESSION_TTL_MS;
  }
}

function readStoredToken(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_TOKEN_KEY);
  } catch {
    return null;
  }
}

function readStoredEstablishedAt(): number | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_ESTABLISHED_KEY);
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}
