import type { Assessment } from "@/types/assessment";
import { seedAssessments, findAssessment } from "@/data/seed-assessments";

const API_BASE = (import.meta.env.VITE_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");

// Client stubs. Swap each implementation with `fetch('/api/...')` against the
// future FastAPI backend. Signatures are stable so call sites do not change.

export async function listAssessments(): Promise<Assessment[]> {
  try {
    const res = await fetch(`${API_BASE}/assessments`);
    if (!res.ok) throw new Error(`Backend ${res.status}`);
    return (await res.json()) as Assessment[];
  } catch {
    return seedAssessments;
  }
}

export async function getAssessment(id: string): Promise<Assessment | undefined> {
  try {
    const res = await fetch(`${API_BASE}/assessments/${encodeURIComponent(id)}`);
    if (res.ok) return (await res.json()) as Assessment;
    if (res.status !== 404) throw new Error(`Backend ${res.status}`);
  } catch {
    // fall through to the local demo catalog for seed ids.
  }
  return findAssessment(id);
}

export async function recommend(_query: string): Promise<Assessment[]> {
  // Backend will replace this with a real recommendation call.
  return seedAssessments;
}
