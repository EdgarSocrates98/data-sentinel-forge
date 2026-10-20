import { Injectable } from "@angular/core";
import { Observable } from "rxjs";

import type { InvestigationStreamEvent } from "../../core/api.models";

/**
 * Named SSE events emitted by the backend on
 * `GET /api/v1/investigations/{id}/stream` (see api/app.py).
 */
const STREAM_EVENTS = [
  "INVESTIGATION_STARTED",
  "TOOL_COMPLETED",
  "HYPOTHESIS_CREATED",
  "INVESTIGATION_COMPLETED",
  "INVESTIGATION_FAILED",
] as const;

const TERMINAL_EVENTS = new Set<string>([
  "INVESTIGATION_COMPLETED",
  "INVESTIGATION_FAILED",
]);

/**
 * Thin `EventSource` wrapper so the SSE stream is injectable and
 * mockable in specs. Completes after a terminal event; errors when the
 * connection drops or `EventSource` is unavailable.
 */
@Injectable({ providedIn: "root" })
export class InvestigationStreamService {
  open(url: string): Observable<InvestigationStreamEvent> {
    return new Observable<InvestigationStreamEvent>((subscriber) => {
      if (typeof EventSource === "undefined") {
        subscriber.error(new Error("EventSource unavailable"));
        return undefined;
      }
      const source = new EventSource(url);
      const listeners: Array<[string, EventListener]> = [];

      for (const name of STREAM_EVENTS) {
        const listener: EventListener = (raw) => {
          const msg = raw as MessageEvent<string>;
          let data: Record<string, unknown> = {};
          try {
            const parsed: unknown = JSON.parse(msg.data);
            if (parsed && typeof parsed === "object") {
              data = parsed as Record<string, unknown>;
            }
          } catch {
            data = { raw: msg.data };
          }
          subscriber.next({ event: name, data, ts: Date.now() });
          if (TERMINAL_EVENTS.has(name)) {
            source.close();
            subscriber.complete();
          }
        };
        source.addEventListener(name, listener);
        listeners.push([name, listener]);
      }

      source.onerror = () => {
        // EventSource auto-reconnects; surface the failure and let the
        // subscriber decide (detail page offers manual refresh).
        if (source.readyState === EventSource.CLOSED) {
          subscriber.error(new Error("stream closed"));
        } else {
          subscriber.error(new Error("stream error"));
        }
      };

      return () => {
        for (const [name, listener] of listeners) {
          source.removeEventListener(name, listener);
        }
        source.close();
      };
    });
  }
}
