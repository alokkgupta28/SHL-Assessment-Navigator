from __future__ import annotations

from ..schemas import Constraints, ConversationState


def _merge_list(a: list, b: list) -> list:
    seen = set()
    out = []
    for x in (a or []) + (b or []):
        key = x.lower() if isinstance(x, str) else x
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def merge(prev: ConversationState, new: ConversationState) -> ConversationState:
    pc, nc = prev.constraints, new.constraints
    merged_constraints = Constraints(
        duration_max=nc.duration_max if nc.duration_max is not None else pc.duration_max,
        remote=nc.remote if nc.remote is not None else pc.remote,
        adaptive=nc.adaptive if nc.adaptive is not None else pc.adaptive,
        languages=_merge_list(pc.languages, nc.languages),
        job_levels=_merge_list(pc.job_levels, nc.job_levels),
    )
    return ConversationState(
        role=new.role or prev.role,
        experience=new.experience or prev.experience,
        industry=new.industry or prev.industry,
        programming_language=_merge_list(prev.programming_language, new.programming_language),
        leadership=new.leadership if new.leadership is not None else prev.leadership,
        communication=new.communication if new.communication is not None else prev.communication,
        technical_skills=_merge_list(prev.technical_skills, new.technical_skills),
        personality=new.personality if new.personality is not None else prev.personality,
        assessment_types=_merge_list(prev.assessment_types, new.assessment_types),
        constraints=merged_constraints,
    )
