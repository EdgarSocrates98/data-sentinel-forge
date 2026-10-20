/**
 * Minimal authenticated SSE client built on `fetch` + `ReadableStream`
 * (ADR-0014). `EventSource` cannot send an `Authorization` header, which
 * is mandatory on every `/api/v1/*` route per the backend bearer-auth
 * middleware — so streaming consumers read the response body directly
 * and parse the `text/event-stream` framing themselves.
 *
 * Supports reconnection via `Last-Event-ID` when the caller tracks the
 * last seen frame id — the backend emits `id: <seq>` on every frame and
 * honors `Last-Event-ID` by replaying only events after that sequence.
 */

export interface SseFrame {
  event: string;
  data: string;
  id: string | null;
}

export interface SseFetchInit {
  /** Full request URL. */
  url: string;
  /** Value for the `Authorization` header, or `null` to omit it. */
  authorization: string | null;
  /** Last frame id seen on a previous connection attempt, if any. */
  lastEventId?: string | null;
  signal: AbortSignal;
}

/**
 * Opens a fetch-based SSE connection and invokes `onFrame` for every
 * complete `event:`/`data:`/`id:` block as it arrives. Resolves when the
 * stream ends cleanly (server closes the body); rejects on network
 * failure, non-2xx status, or abort.
 */
export async function readSseStream(
  init: SseFetchInit,
  onFrame: (frame: SseFrame) => void,
): Promise<void> {
  const headers: Record<string, string> = { Accept: "text/event-stream" };
  if (init.authorization) headers["Authorization"] = init.authorization;
  if (init.lastEventId) headers["Last-Event-ID"] = init.lastEventId;

  const response = await fetch(init.url, {
    headers,
    signal: init.signal,
    credentials: "omit",
  });

  if (!response.ok) {
    throw new HttpStreamError(response.status);
  }
  if (!response.body) {
    throw new Error("SSE response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line; keep any trailing
      // partial frame in the buffer for the next chunk.
      let boundary: number;
      while ((boundary = buffer.indexOf("\n\n")) !== -1) {
        const rawFrame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const frame = parseFrame(rawFrame);
        if (frame) onFrame(frame);
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/** Raised when the API responds with a non-2xx status for the stream. */
export class HttpStreamError extends Error {
  constructor(readonly status: number) {
    super(`SSE stream request failed with status ${status}`);
  }
}

function parseFrame(raw: string): SseFrame | null {
  let event = "message";
  let id: string | null = null;
  const dataLines: string[] = [];

  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    } else if (line.startsWith("id:")) {
      id = line.slice("id:".length).trim();
    }
    // Lines starting with ":" are comments/keep-alives — ignored.
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n"), id };
}
