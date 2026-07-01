from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Role = Literal["user", "assistant", "system"]
Mode = Literal["recommend", "compare", "refine"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(..., min_length=1, max_length=4_000)

    @field_validator("content")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be blank")
        return v


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128,
                            pattern=r"^[A-Za-z0-9_\-:.]+$")
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=32)
    mode: Mode = "recommend"
    compare_ids: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("compare_ids")
    @classmethod
    def _validate_ids(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        for item in v:
            if not item or len(item) > 128:
                raise ValueError("compare_ids entries must be 1-128 chars")
            if item in seen:
                raise ValueError(f"compare_ids contains duplicate: {item}")
            seen.add(item)
        return v




class Constraints(BaseModel):
    duration_max: Optional[int] = None
    remote: Optional[bool] = None
    adaptive: Optional[bool] = None
    languages: list[str] = Field(default_factory=list)
    job_levels: list[str] = Field(default_factory=list)


class ConversationState(BaseModel):
    role: Optional[str] = None
    experience: Optional[str] = None
    industry: Optional[str] = None
    programming_language: list[str] = Field(default_factory=list)
    leadership: Optional[bool] = None
    communication: Optional[bool] = None
    technical_skills: list[str] = Field(default_factory=list)
    personality: Optional[bool] = None
    assessment_types: list[str] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)


class Recommendation(BaseModel):
    id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=256)
    url: str = Field(..., max_length=1024)
    duration_minutes: int = Field(..., ge=0, le=600)
    remote: bool
    adaptive: bool
    job_levels: list[str] = Field(..., max_length=16)
    languages: list[str] = Field(..., max_length=64)
    skills: list[str] = Field(..., max_length=64)
    category: str = Field(..., max_length=128)
    score: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(..., min_length=1, max_length=8)

    @field_validator("reasons")
    @classmethod
    def _strip_blank_reasons(cls, v: list[str]) -> list[str]:
        out = [r.strip()[:400] for r in v if r and r.strip()]
        if not out:
            raise ValueError("reasons must contain at least one non-empty entry")
        return out




class AssessmentResponse(BaseModel):
    id: str
    name: str
    category: str
    durationMinutes: int
    remote: bool
    adaptive: bool
    jobLevels: list[str]
    languages: list[str]
    skills: list[str]
    description: str
    officialUrl: str


class ComparisonCell(BaseModel):
    id: str
    name: str
    duration_minutes: int
    remote: bool
    adaptive: bool
    job_levels: list[str]
    languages: list[str]
    skills: list[str]
    category: str
    description: str
    url: str


class Comparison(BaseModel):
    items: list[ComparisonCell]
    features: list[str]


class Safety(BaseModel):
    blocked: bool = False
    reason: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    need_clarification: bool = False
    clarifying_question: Optional[str] = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    comparison: Optional[Comparison] = None
    state: ConversationState = Field(default_factory=ConversationState)
    safety: Safety = Field(default_factory=Safety)

    @field_validator("recommendations")
    @classmethod
    def _dedup_recommendations(cls, v: list[Recommendation]) -> list[Recommendation]:
        # Defence in depth: even if the engine dedupes, the public envelope
        # must never ship two cards with the same id.
        seen: set[str] = set()
        out: list[Recommendation] = []
        for r in v:
            if r.id in seen:
                continue
            seen.add(r.id)
            out.append(r)
        return out



class HealthResponse(BaseModel):
    status: str
    catalog_size: int
    model: str
    version: str = "1.1.0"
    uptime_seconds: float = 0.0

