/**
 * Chat API client.
 *
 * Hits the FastAPI backend (`POST /chat`). The backend URL is configurable
 * via `VITE_API_BASE` (defaults to http://localhost:8000 for local dev).
 * Responses are validated minimally — Pydantic validates on the server.
 */
import type { Assessment } from "@/types/assessment";

const API_BASE = (import.meta.env.VITE_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");

export type ChatRole = "user" | "assistant";

export interface BackendMessage {
  role: ChatRole;
  content: string;
}

export interface BackendRecommendation {
  id: string;
  name: string;
  url: string;
  duration_minutes: number;
  remote: boolean;
  adaptive: boolean;
  job_levels: string[];
  languages: string[];
  skills: string[];
  category: string;
  score: number;
  reasons: string[];
}

export interface BackendChatResponse {
  session_id: string;
  reply: string;
  need_clarification: boolean;
  clarifying_question: string | null;
  recommendations: BackendRecommendation[];
  comparison: unknown;
  state: Record<string, unknown>;
  safety: { blocked: boolean; reason: string | null };
}

export async function postChat(
  body: {
    session_id: string;
    messages: BackendMessage[];
    mode?: "recommend" | "refine" | "compare";
    compare_ids?: string[];
  },
  signal?: AbortSignal,
): Promise<BackendChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Backend ${res.status}: ${text.slice(0, 200) || res.statusText}`);
  }
  return (await res.json()) as BackendChatResponse;
}

/** Map a backend recommendation onto the UI's Assessment shape. */
export function recToAssessment(r: BackendRecommendation): Assessment {
  return {
    id: r.id,
    name: r.name,
    category: r.category || "Assessment",
    durationMinutes: r.duration_minutes,
    // Backend job_levels are free-form; cast for the union type.
    jobLevels: (r.job_levels as Assessment["jobLevels"]) ?? [],
    adaptive: r.adaptive,
    remote: r.remote,
    languages: r.languages ?? [],
    skills: r.skills ?? [],
    description: r.reasons?.join(" • ") || "",
    officialUrl: r.url,
  };
}
