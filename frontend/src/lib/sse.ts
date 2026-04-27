// Minimal SSE helper for chat streaming. Full implementation in Phase 3.

export type SSEHandler = (event: { data: string; event?: string }) => void;

export async function streamSSE(url: string, init: RequestInit, onEvent: SSEHandler): Promise<void> {
  const res = await fetch(url, init);
  if (!res.body) throw new Error("No SSE body");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";
    for (const part of parts) {
      const lines = part.split("\n");
      let data = "";
      let eventName: string | undefined;
      for (const line of lines) {
        if (line.startsWith("data:")) data += line.slice(5).trimStart() + "\n";
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
      }
      if (data) onEvent({ data: data.trimEnd(), event: eventName });
    }
  }
}
