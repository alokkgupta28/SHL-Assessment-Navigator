// UI-only streaming simulation. Token-aware so it reads like a real LLM stream:
// emits word-sized chunks with jittered delays and slightly longer pauses on
// punctuation and newlines. Replace with a real SSE/fetch reader later.

const TOKEN_RE = /(\s+|[^\s]+)/g;

function pauseFor(token: string, base: number) {
  if (/\n/.test(token)) return base * 4;
  if (/[.!?]/.test(token)) return base * 3;
  if (/[,;:]/.test(token)) return base * 2;
  if (/^\s+$/.test(token)) return base * 0.4;
  // word — scale with length
  return base + Math.min(token.length, 8) * 2;
}

export async function* streamText(
  text: string,
  opts: { delayMs?: number; signal?: AbortSignal } = {},
): AsyncGenerator<string> {
  const { delayMs = 12, signal } = opts;
  const tokens = text.match(TOKEN_RE) ?? [text];
  for (const tok of tokens) {
    if (signal?.aborted) return;
    yield tok;
    const jitter = 0.7 + Math.random() * 0.6;
    await new Promise((r) => setTimeout(r, pauseFor(tok, delayMs) * jitter));
  }
}
