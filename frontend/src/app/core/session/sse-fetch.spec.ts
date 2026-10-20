import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpStreamError, readSseStream } from "./sse-fetch";

/** Build a `Response`-like object backed by a chunked ReadableStream. */
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

describe("readSseStream", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("sends the Authorization header and parses event/data frames", async () => {
    fetchSpy.mockResolvedValue(
      chunkedResponse([
        'event: TOOL_COMPLETED\ndata: {"tool":"x"}\n\n',
        'event: INVESTIGATION_COMPLETED\ndata: {}\n\n',
      ]),
    );

    const frames: Array<{ event: string; data: string }> = [];
    const controller = new AbortController();

    await readSseStream(
      {
        url: "http://api.local/stream",
        authorization: "Bearer tok-1",
        signal: controller.signal,
      },
      (frame) => frames.push(frame),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://api.local/stream",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer tok-1" }),
      }),
    );
    expect(frames).toEqual([
      { event: "TOOL_COMPLETED", data: '{"tool":"x"}', id: null },
      { event: "INVESTIGATION_COMPLETED", data: "{}", id: null },
    ]);
  });

  it("splits frames across chunk boundaries", async () => {
    fetchSpy.mockResolvedValue(
      chunkedResponse(["event: TOOL_C", 'OMPLETED\ndata: {"a":1}\n\n']),
    );

    const frames: Array<{ event: string; data: string }> = [];
    await readSseStream(
      { url: "http://api.local/stream", authorization: null, signal: new AbortController().signal },
      (frame) => frames.push(frame),
    );

    expect(frames).toEqual([
      { event: "TOOL_COMPLETED", data: '{"a":1}', id: null },
    ]);
  });

  it("sends Last-Event-ID when reconnecting and captures id: frames", async () => {
    fetchSpy.mockResolvedValue(
      chunkedResponse(["id: 42\nevent: TOOL_COMPLETED\ndata: {}\n\n"]),
    );

    const frames: Array<{ id: string | null }> = [];
    await readSseStream(
      {
        url: "http://api.local/stream",
        authorization: null,
        lastEventId: "41",
        signal: new AbortController().signal,
      },
      (frame) => frames.push(frame),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://api.local/stream",
      expect.objectContaining({
        headers: expect.objectContaining({ "Last-Event-ID": "41" }),
      }),
    );
    expect(frames[0]?.id).toBe("42");
  });

  it("omits the Authorization header when there is no token", async () => {
    fetchSpy.mockResolvedValue(chunkedResponse([]));
    await readSseStream(
      { url: "http://api.local/stream", authorization: null, signal: new AbortController().signal },
      () => undefined,
    );
    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["Authorization"]).toBeUndefined();
  });

  it("rejects with HttpStreamError on a non-2xx status", async () => {
    fetchSpy.mockResolvedValue(chunkedResponse([], 401));
    await expect(
      readSseStream(
        { url: "http://api.local/stream", authorization: "Bearer bad", signal: new AbortController().signal },
        () => undefined,
      ),
    ).rejects.toBeInstanceOf(HttpStreamError);
  });
});
