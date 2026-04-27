type StreamHandler = (event: any) => void;

export async function consumeEventStream(response: Response, onEvent: StreamHandler) {
  if (!response.body) throw new Error("No response stream available");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex).trimEnd();
      buffer = buffer.slice(newlineIndex + 1);

      if (line.startsWith("data: ")) {
        const raw = line.slice(6);
        if (raw.trim()) {
          try {
            onEvent(JSON.parse(raw));
          } catch {
            // Ignore malformed messages and keep the stream alive.
          }
        }
      }

      newlineIndex = buffer.indexOf("\n");
    }
  }
}

