"""Conversation engine — consultant-style orchestrator.

Responsibilities:
1. Safety scan (block out-of-scope before anything else).
2. Maintain per-session memory: state, slot confidences, pinned shortlist,
   clarification budget, turn count, last clarification slot.
3. Classify per-turn intent (initial / refine_* / compare / explain_diff /
   confirm / meta_question / out_of_scope).
4. Route:
   - compare       -> build_comparison
   - refine_drop/add/replace -> mutate pinned shortlist via refinement.py
   - refine_tighten / initial -> full retrieve + rank
   - explain_diff  -> short LLM-grounded diff reply, keep shortlist
   - confirm       -> lock & confirm shortlist, no new questions
   - out_of_scope  -> polite redirect, keep shortlist
5. Confidence-based clarification gate (clarifier.decide).
6. Grounding: every Recommendation.id MUST exist in the in-memory catalog.
7. Hard 8-turn cap: never ask on the last turn; always commit.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field

from ..catalog.models import Assessment
from ..comparison.engine import build as build_comparison
from ..config import Settings
from ..llm.gemini import GeminiClient
from ..llm.prompts import DIFF_SYSTEM, EXPLAINER_SYSTEM
from ..observability.logging import get_logger
from ..ranking.ranker import build_reasons, rank
from ..retrieval.hybrid import HybridRetriever
from ..safety import scan
from ..schemas import (
    ChatRequest,
    ChatResponse,
    ConversationState,
    Recommendation,
    Safety,
)
from . import clarifier, extractor, intent, refinement
from .session_store import SessionStore
from .slots import SlotMeta

log = get_logger("shl.engine")


TURN_HARD_CAP = 8
MAX_SHORTLIST = 8


@dataclass
class SessionMemory:
    state: ConversationState = field(default_factory=ConversationState)
    meta: SlotMeta = field(default_factory=SlotMeta)
    pinned_ids: list[str] = field(default_factory=list)
    turn_count: int = 0
    clarifications_asked: int = 0
    last_question_slot: str | None = None
    locked: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


class ConversationEngine:
    def __init__(
        self,
        catalog: list[Assessment],
        retriever: HybridRetriever,
        settings: Settings,
        llm: GeminiClient | None,
    ):
        self.catalog = catalog
        self.by_id: dict[str, Assessment] = {a.id: a for a in catalog}
        self.retriever = retriever
        self.settings = settings
        self.llm = llm
        self.sessions: SessionStore[SessionMemory] = SessionStore(
            max_sessions=settings.session_max,
            ttl_seconds=settings.session_ttl_seconds,
            factory=SessionMemory,
        )

    # ---------- session helpers ----------

    def _session(self, sid: str) -> SessionMemory:
        return self.sessions.get(sid)


    def _ground(self, ids: list[str]) -> list[Assessment]:
        """Strict grounding: only ids that exist in the catalog."""
        seen: set[str] = set()
        out: list[Assessment] = []
        for i in ids:
            a = self.by_id.get(i)
            if a is not None and i not in seen:
                seen.add(i)
                out.append(a)
        return out

    def _recs(self, mem: SessionMemory) -> list[Recommendation]:
        items = self._ground(mem.pinned_ids)
        return [self._to_rec(mem.state, a, score=1.0) for a in items]

    def _to_rec(self, state: ConversationState, a: Assessment, score: float) -> Recommendation:
        return Recommendation(
            id=a.id, name=a.name, url=a.url,
            duration_minutes=a.duration_minutes, remote=a.remote, adaptive=a.adaptive,
            job_levels=a.job_levels, languages=a.languages, skills=a.skills,
            category=a.category, score=round(float(score), 4),
            reasons=build_reasons(state, a),
        )

    # ---------- entry point ----------

    def handle(self, req: ChatRequest) -> ChatResponse:
        # Per-session lock prevents two concurrent requests on the same
        # session_id from corrupting turn counts / pinned shortlist.
        mem = self._session(req.session_id)
        t0 = time.perf_counter()
        with mem.lock:
            resp = self._handle_locked(req, mem)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        log.info(
            "turn",
            extra={
                "session_id": req.session_id,
                "turn": mem.turn_count,
                "n_recs": len(resp.recommendations),
                "need_clarification": resp.need_clarification,
                "safety_blocked": resp.safety.blocked,
                "latency_ms": latency_ms,
                "mode": req.mode,
            },
        )
        return resp


    def _handle_locked(self, req: ChatRequest, mem: SessionMemory) -> ChatResponse:
        # 1) Safety guard — block before any state mutation.
        verdict = scan(req.messages)
        if verdict.blocked:
            return ChatResponse(
                session_id=req.session_id,
                reply=verdict.refusal or "Request blocked.",
                need_clarification=False, clarifying_question=None,
                recommendations=[], comparison=None,
                state=mem.state, safety=Safety(blocked=True, reason=verdict.reason),
            )

        mem.turn_count += 1


        last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")

        # 2) Update state from this user turn.
        if last_user:
            mem.state = extractor.extract(mem.state, last_user, self.llm, mem.meta)

        # 3) Classify intent for routing.
        it = intent.classify(
            last_user,
            has_pinned=bool(mem.pinned_ids),
            mode_hint=req.mode,
            compare_ids=req.compare_ids,
        )
        log.debug(
            "intent_classified",
            extra={"intent": it.intent, "has_pinned": bool(mem.pinned_ids)},
        )


        # 4) Out-of-scope redirect (legal / regulatory / medical).
        if it.intent == "out_of_scope":
            reply = ("That's outside what I can advise on — I help shortlist assessments, "
                     "not interpret legal or regulatory obligations. Your legal or compliance team "
                     "is the right resource. The current shortlist stands.")
            return self._respond(req, mem, reply, recs=self._recs(mem))

        # 5) Explicit comparison.
        if it.intent == "compare":
            ids = req.compare_ids or mem.pinned_ids[:2]
            grounded_ids = [a.id for a in self._ground(ids)]
            comp = build_comparison(grounded_ids, self.catalog) if grounded_ids else None
            reply = "Side-by-side comparison." if comp else "I need at least two valid assessments to compare."
            return ChatResponse(
                session_id=req.session_id, reply=reply,
                need_clarification=False, clarifying_question=None,
                recommendations=[], comparison=comp, state=mem.state, safety=Safety(),
            )

        # 6) Diff explanation between two pinned items (e.g. "what's the diff between X and Y?").
        if it.intent == "explain_diff" and len(mem.pinned_ids) >= 2:
            reply = self._explain_diff(last_user, mem)
            return self._respond(req, mem, reply, recs=self._recs(mem))

        # 7) Meta-question (why is this in here / is it redundant) — keep shortlist, short answer.
        if it.intent == "meta_question" and mem.pinned_ids:
            reply = ("Each item is in the shortlist for a distinct reason — see the per-item "
                     "rationale on the right. Tell me which one you want to drop or replace and I'll update it.")
            return self._respond(req, mem, reply, recs=self._recs(mem))

        # 8) Confirmation — lock and close.
        if it.intent == "confirm" and mem.pinned_ids:
            mem.locked = True
            reply = "Confirmed. Final shortlist locked."
            return self._respond(req, mem, reply, recs=self._recs(mem))

        # 9) Structural refinement on an existing shortlist.
        if mem.pinned_ids and it.intent in {"refine_drop", "refine_add", "refine_replace"}:
            new_ids = list(mem.pinned_ids)
            if it.intent == "refine_drop":
                new_ids = refinement.drop_from(new_ids, it.drop_terms, self.catalog)
            elif it.intent == "refine_add":
                new_ids = refinement.add_to(new_ids, it.add_terms, self.catalog, max_size=MAX_SHORTLIST)
            elif it.intent == "refine_replace":
                new_ids = refinement.replace_in(new_ids, it.replace_pairs, self.catalog)
            mem.pinned_ids = self._dedup(new_ids)
            reply = self._compose_reply(mem, refinement_mode=True)
            return self._respond(req, mem, reply, recs=self._recs(mem))

        # 10) Tighten constraints on existing shortlist → re-filter via re-rank.
        if mem.pinned_ids and it.intent == "refine_tighten":
            ranked = rank(
                mem.state,
                [(self.by_id[i], 1.0) for i in mem.pinned_ids if i in self.by_id],
                top_k=MAX_SHORTLIST,
            )
            # Apply hard constraints from state again
            filtered = self._apply_hard_constraints(ranked, mem.state)
            if filtered:
                mem.pinned_ids = [a.id for a, _ in filtered]
            reply = self._compose_reply(mem, refinement_mode=True)
            return self._respond(req, mem, reply, recs=self._recs(mem))

        # 11) Initial / fresh retrieval path. Clarify if decision-critical info missing.
        gap = clarifier.decide(
            mem.state, mem.meta,
            turn_count=mem.turn_count,
            clarifications_asked=mem.clarifications_asked,
            last_question_slot=mem.last_question_slot,
            has_any_recommendations=bool(mem.pinned_ids),
        )
        # Hard cap: never ask on the final turn.
        if mem.turn_count >= TURN_HARD_CAP:
            gap.need = False

        if gap.need:
            mem.clarifications_asked += 1
            mem.last_question_slot = gap.slot_key
            return ChatResponse(
                session_id=req.session_id,
                reply=gap.question or "Could you tell me more?",
                need_clarification=True,
                clarifying_question=gap.question,
                recommendations=self._recs(mem),  # keep prior list visible if any
                comparison=None, state=mem.state, safety=Safety(),
            )

        # Run retrieval + rank
        candidates, diag = self.retriever.search(mem.state, return_diagnostics=True)
        log.info(
            "retrieval",
            extra={
                "query": diag.query[:200],
                "n_candidates": len(candidates),
                "confidence": round(diag.confidence, 3),
                "cross_encoder_used": diag.cross_encoder_used,
            },
        )

        ranked = rank(mem.state, candidates, top_k=MAX_SHORTLIST)
        # Hard duration budget at the *presentation* layer: retrieval keeps
        # near-misses for recall, but a user who said "under 45 min" should
        # never see a 60-min card. Fall back to ranked if filtering empties.
        hard = self._apply_hard_constraints(ranked, mem.state)
        if hard:
            ranked = hard
        mem.pinned_ids = [a.id for a, _ in ranked]

        reply = self._compose_reply(mem, refinement_mode=False)
        return self._respond(req, mem, reply, recs=[self._to_rec(mem.state, a, s) for a, s in ranked])


    # ---------- helpers ----------

    @staticmethod
    def _dedup(ids: list[str]) -> list[str]:
        seen, out = set(), []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    @staticmethod
    def _apply_hard_constraints(
        ranked: list[tuple[Assessment, float]],
        state: ConversationState,
    ) -> list[tuple[Assessment, float]]:
        c = state.constraints
        out = []
        for a, s in ranked:
            if c.duration_max is not None and a.duration_minutes > c.duration_max:
                continue
            if c.remote is True and not a.remote:
                continue
            if c.adaptive is True and not a.adaptive:
                continue
            if c.languages:
                wanted = {l.lower() for l in c.languages}
                if not (wanted & {l.lower() for l in a.languages}):
                    continue
            out.append((a, s))
        return out

    def _explain_diff(self, user_text: str, mem: SessionMemory) -> str:
        items = self._ground(mem.pinned_ids[:2])
        if self.llm is not None and len(items) == 2:
            try:
                payload = self.llm.json(
                    DIFF_SYSTEM,
                    json.dumps({
                        "question": user_text,
                        "items": [
                            {"name": a.name, "category": a.category,
                             "duration_minutes": a.duration_minutes, "skills": a.skills,
                             "description": a.description}
                            for a in items
                        ],
                    }),
                )
                reply = (payload.get("reply") or "").strip()
                if reply:
                    return reply
            except Exception:
                pass
        # Deterministic fallback.
        if len(items) == 2:
            a, b = items
            return (f"{a.name} ({a.category}, {a.duration_minutes} min) and "
                    f"{b.name} ({b.category}, {b.duration_minutes} min) measure different signals — "
                    f"see the per-item rationale.")
        return "I'd need both items pinned to compare them in detail."

    def _compose_reply(self, mem: SessionMemory, *, refinement_mode: bool) -> str:
        items = self._ground(mem.pinned_ids)
        if not items:
            return ("I couldn't find a strong match in the SHL catalog for those criteria. "
                    "Tell me more about the role or what you want to measure.")

        # Honesty about catalog coverage (e.g. Rust has no dedicated test).
        missing_notes = self._catalog_coverage_notes(mem)

        if self.llm is not None:
            try:
                payload = self.llm.json(
                    EXPLAINER_SYSTEM,
                    json.dumps({
                        "state": mem.state.model_dump(),
                        "refinement": refinement_mode,
                        "missing_coverage": missing_notes,
                        "items": [
                            {"id": a.id, "name": a.name, "category": a.category,
                             "duration_minutes": a.duration_minutes, "skills": a.skills,
                             "remote": a.remote, "adaptive": a.adaptive,
                             "job_levels": a.job_levels, "languages": a.languages}
                            for a in items
                        ],
                    }),
                )
                reply = (payload.get("reply") or "").strip()
                if reply:
                    return reply
            except Exception:
                pass

        # Deterministic fallback reply.
        head = ("Updated shortlist." if refinement_mode
                else f"Here are {len(items)} SHL assessments that match your criteria.")
        if missing_notes:
            head += " Note: " + " ".join(missing_notes)
        return head

    def _catalog_coverage_notes(self, mem: SessionMemory) -> list[str]:
        """Flag user-named skills that have no obvious catalog match."""
        notes: list[str] = []
        wanted = (mem.state.programming_language or []) + (mem.state.technical_skills or [])
        if not wanted or not self.catalog:
            return notes
        corpus = " ".join(a.corpus_text().lower() for a in self.catalog)
        for s in wanted:
            if s and s.lower() not in corpus:
                notes.append(f"SHL's catalog doesn't currently include a {s}-specific test.")
        return notes[:2]

    def _respond(
        self,
        req: ChatRequest,
        mem: SessionMemory,
        reply: str,
        *,
        recs: list[Recommendation],
    ) -> ChatResponse:
        return ChatResponse(
            session_id=req.session_id,
            reply=reply,
            need_clarification=False,
            clarifying_question=None,
            recommendations=recs,
            comparison=None,
            state=mem.state,
            safety=Safety(),
        )
