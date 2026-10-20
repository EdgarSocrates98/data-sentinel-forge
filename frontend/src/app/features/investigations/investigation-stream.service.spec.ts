import { provideHttpClient } from "@angular/common/http";
import {
  HttpTestingController,
  provideHttpClientTesting,
} from "@angular/common/http/testing";
import { TestBed } from "@angular/core/testing";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { SessionService } from "../../core/session/session.service";
import type { InvestigationStreamEvent } from "../../core/api.models";
import { InvestigationStreamService } from "./investigation-stream.service";

function chunkedResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder();
  let i = 0;
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (i < chunks.length) {
        controller.enqueue(encoder.encode(chunks[i]));
        i += 1;
      } else {
        controller.close();
      }
    },
  });
  return new Response(stream, { status });
}

describe("InvestigationStreamService (fetch-based SSE)", () => {
  let service: InvestigationStreamService;
  let session: SessionService;
  let http: HttpTestingController;
  let fetchSpy: MockInstance<typeof fetch>;

  beforeEach(() => {
    sessionStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(InvestigationStreamService);
    session = TestBed.inject(SessionService);
    http = TestBed.inject(HttpTestingController);
    fetchSpy = vi.spyOn(globalThis, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    http.verify();
    sessionStorage.clear();
  });

  /** Establish a real session via HttpClient (not the fetch-mocked SSE path). */
  function establishSession(token: string): void {
    session.establish(token).subscribe();
    http.expectOne((r) => r.url.endsWith("/capabilities")).flush([]);
  }

  it("attaches the Authorization header from the active session", async () => {
    establishSession("tok-1");
    fetchSpy.mockResolvedValue(
      chunkedResponse([
        'event: INVESTIGATION_COMPLETED\ndata: {}\n\n',
      ]),
    );

    const events: InvestigationStreamEvent[] = [];
    await new Promise<void>((resolve) => {
      service.open("http://api.local/investigations/1/stream").subscribe({
        next: (e) => events.push(e),
        complete: resolve,
      });
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://api.local/investigations/1/stream",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer tok-1" }),
      }),
    );
    expect(events.map((e) => e.event)).toEqual(["INVESTIGATION_COMPLETED"]);
  });

  it("completes the observable on a terminal event", async () => {
    fetchSpy.mockResolvedValue(
      chunkedResponse([
        'event: TOOL_COMPLETED\ndata: {"tool":"x"}\n\n',
        'event: INVESTIGATION_COMPLETED\ndata: {}\n\n',
      ]),
    );

    const events: InvestigationStreamEvent[] = [];
    let completed = false;
    await new Promise<void>((resolve) => {
      service.open("http://api.local/stream").subscribe({
        next: (e) => events.push(e),
        complete: () => {
          completed = true;
          resolve();
        },
      });
    });

    expect(completed).toBeTrue();
    expect(events.map((e) => e.event)).toEqual([
      "TOOL_COMPLETED",
      "INVESTIGATION_COMPLETED",
    ]);
  });

  it("expires the session and errors the observable on a 401 stream response", async () => {
    establishSession("tok-1");
    fetchSpy.mockResolvedValue(chunkedResponse([], 401));

    let error: unknown;
    await new Promise<void>((resolve) => {
      service.open("http://api.local/stream").subscribe({
        error: (err) => {
          error = err;
          resolve();
        },
      });
    });

    expect(error).toBeTruthy();
    expect(session.isAuthenticated()).toBeFalse();
    expect(session.isExpired()).toBeTrue();
  });

  it("unsubscribing aborts the underlying fetch", async () => {
    let aborted = false;
    fetchSpy.mockImplementation(
      (url: string | URL | Request, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            aborted = true;
            reject(new DOMException("aborted", "AbortError"));
          });
        }),
    );

    const sub = service.open("http://api.local/stream").subscribe();
    sub.unsubscribe();
    // allow the microtask queue to process the abort listener
    await Promise.resolve();
    expect(aborted).toBeTrue();
  });
});
