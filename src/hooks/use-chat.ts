import { useCallback, useRef, useState } from "react";
import type { ChatMessage, ChatStatus } from "@/types/chat";
import type { Assessment } from "@/types/assessment";
import { streamText } from "@/lib/mock-stream";
import {
  postChat,
  recToAssessment,
  type BackendMessage,
} from "@/services/chat-api";

const uid = () => Math.random().toString(36).slice(2, 11);
const sid = () => `sess_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;

interface State {
  messages: ChatMessage[];
  status: ChatStatus;
  error: string | null;
  recommendations: Assessment[];
  clarifying: string | null;
}

export function useChat() {
  const [s, setS] = useState<State>({
    messages: [], status: "idle", error: null, recommendations: [], clarifying: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const sessionId = useRef<string>(sid());
  const history = useRef<BackendMessage[]>([]);
  const lastUserText = useRef<string | null>(null);

  const patch = (p: Partial<State>) => setS((cur) => ({ ...cur, ...p }));
  const patchMsg = (id: string, fn: (m: ChatMessage) => ChatMessage) =>
    setS((cur) => ({ ...cur, messages: cur.messages.map((m) => (m.id === id ? fn(m) : m)) }));

  const run = useCallback(async (text: string) => {
    lastUserText.current = text;
    const assistantId = uid();
    setS((cur) => ({
      ...cur,
      error: null,
      status: "thinking",
      messages: [...cur.messages, {
        id: assistantId, role: "assistant", content: "", createdAt: Date.now(), streaming: true,
      }],
    }));

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      // Append the user turn we just sent to the rolling history.
      const turn: BackendMessage = { role: "user", content: text };
      const messages = [...history.current, turn];

      const resp = await postChat(
        { session_id: sessionId.current, messages, mode: "recommend" },
        ctrl.signal,
      );

      // Persist this round-trip in the rolling history for the next turn.
      history.current = [...messages, { role: "assistant", content: resp.reply }];

      const recs = (resp.recommendations ?? []).map(recToAssessment);
      patch({ status: "streaming", recommendations: recs, clarifying: resp.clarifying_question });

      // Token-paced reveal of the real backend reply. Replaces the prior
      // canned text — content here is always grounded server output.
      let acc = "";
      for await (const chunk of streamText(resp.reply, { signal: ctrl.signal })) {
        acc += chunk;
        patchMsg(assistantId, (m) => ({ ...m, content: acc }));
      }
      patchMsg(assistantId, (m) => ({ ...m, streaming: false }));
      patch({ status: "idle" });
    } catch (e) {
      if (ctrl.signal.aborted) {
        patchMsg(assistantId, (m) => ({ ...m, streaming: false }));
        patch({ status: "idle" });
        return;
      }
      patchMsg(assistantId, (m) => ({ ...m, streaming: false }));
      const msg = e instanceof Error ? e.message : "Something went wrong.";
      patch({
        status: "error",
        error: `${msg}. Is the backend running at ${import.meta.env.VITE_API_BASE ?? "http://localhost:8000"}?`,
      });
    }
  }, []);

  const send = useCallback(async (text: string) => {
    const userMsg: ChatMessage = { id: uid(), role: "user", content: text, createdAt: Date.now() };
    setS((cur) => ({ ...cur, messages: [...cur.messages, userMsg] }));
    await run(text);
  }, [run]);

  const regenerate = useCallback(async () => {
    if (!lastUserText.current) return;
    // Drop the most recent assistant message + its history entry, then re-run.
    setS((cur) => {
      const idx = [...cur.messages].reverse().findIndex((m) => m.role === "assistant");
      if (idx === -1) return cur;
      const realIdx = cur.messages.length - 1 - idx;
      return { ...cur, messages: cur.messages.slice(0, realIdx) };
    });
    if (history.current.length && history.current[history.current.length - 1].role === "assistant") {
      history.current = history.current.slice(0, -1);
    }
    await run(lastUserText.current);
  }, [run]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    patch({ status: "idle" });
    setS((cur) => ({ ...cur, messages: cur.messages.map((m) => (m.streaming ? { ...m, streaming: false } : m)) }));
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    sessionId.current = sid();
    history.current = [];
    lastUserText.current = null;
    setS({ messages: [], status: "idle", error: null, recommendations: [], clarifying: null });
  }, []);

  return {
    messages: s.messages,
    status: s.status,
    error: s.error,
    recommendations: s.recommendations,
    clarifying: s.clarifying,
    send, stop, reset, regenerate,
  };
}
