import { Injectable, inject } from "@angular/core";
import { Observable } from "rxjs";

import type { InvestigationStreamEvent } from "../../core/api.models";
import { HttpStreamError, readSseStream } from "../../core/session/sse-fetch";
import { SessionService } from "../../core/session/session.service";

/**
 * Named SSE events emitted by the backend on
 * `GET /api/v1/investigations/{id}/stream` (see api/app.py).
 */
const STREAM_EVENTS = new Set<string>([
  "INVESTIGATION_STARTED",
  "TOOL_COMPLETED",
  "HYPOTHESIS_CREATED",
  "INVESTIGATION_COMPLETED",
  "INVESTIGATION_FAILED",
]);

const TERMINAL_EVENTS = new Set<string>([
  "INVESTIGATION_COMPLETED",
  "INVESTIGATION_FAILED",
]);

/**
 * Authenticated SSE client for live investigation events (ADR-0014).
 *
 * `EventSource` cannot carry the `Authorization: Bearer <token>` header
 * the backend requires on every `/api/v1/*` route, so this service reads
 * the stream via `fetch` + `ReadableStream` (see `core/session/sse-fetch.ts`)
 * instead. The public API — `open(url): Observable<InvestigationStreamEvent>`
 * — is unchanged so `InvestigationDetailComponent` needs no changes.
 *
 * Reconnection carries `Last-Event-ID` when the backend has supplied an
 * `id:` frame. Backend contract note (ds-0101): the current
 * `/investigations/{id}/stream` handler does not emit `id:` frames, so
 * reconnects today replay from the start of the backend's buffered
 * history rather than resuming precisely — this client is ready for
 * `id:` support but cannot fabricate it.
 */
@Injectable({ providedIn: "root" })
export class InvestigationStreamService {
  private readonly session = inject(SessionService);

  open(url: string): Observable<InvestigationStreamEvent> {
    return new Observable<InvestigationStreamEvent>((subscriber) => {
      const controller = new AbortController();
      let lastEventId: string | null = null;
      let closed = false;

      const run = async (): Promise<void> => {
        try {
          await readSseStream(
            {
              url,
              authorization: this.session.authorizationHeader(),
              lastEventId,
              signal: controller.signal,
            },
            (frame) => {
              if (frame.id) lastEventId = frame.id;
              if (!STREAM_EVENTS.has(frame.event)) return;

              let data: Record<string, unknown> = {};
              try {
                const parsed: unknown = JSON.parse(frame.data);
                if (parsed && typeof parsed === "object") {
                  data = parsed as Record<string, unknown>;
                }
              } catch {
                data = { raw: frame.data };
              }

              subscriber.next({
                event: frame.event as InvestigationStreamEvent["event"],
                data,
                ts: Date.now(),
              });

              if (TERMINAL_EVENTS.has(frame.event)) {
                closed = true;
                controller.abort();
                subscriber.complete();
              }
            },
          );
          if (!closed) subscriber.complete();
        } catch (err) {
          if (closed || controller.signal.aborted) return;
          if (err instanceof HttpStreamError && err.status === 401) {
            // The interceptor path doesn't cover fetch(); mirror its
            // behavior for the stream so the session doesn't look "stuck".
            this.session.expire();
          }
          subscriber.error(err);
        }
      };

      void run();

      return () => {
        closed = true;
        controller.abort();
      };
    });
  }
}
