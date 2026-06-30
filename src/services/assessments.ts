import type { Assessment } from "@/types/assessment";
import { seedAssessments, findAssessment } from "@/data/seed-assessments";

// Client stubs. Swap each implementation with `fetch('/api/...')` against the
// future FastAPI backend. Signatures are stable so call sites do not change.

export async function listAssessments(): Promise<Assessment[]> {
  return seedAssessments;
}

export async function getAssessment(id: string): Promise<Assessment | undefined> {
  return findAssessment(id);
}

export async function recommend(_query: string): Promise<Assessment[]> {
  // Backend will replace this with a real recommendation call.
  return seedAssessments;
}
