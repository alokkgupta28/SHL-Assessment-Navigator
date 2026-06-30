from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Assessment:
    id: str
    name: str
    url: str
    description: str
    category: str
    duration_minutes: int
    remote: bool
    adaptive: bool
    job_levels: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)

    def corpus_text(self) -> str:
        return " ".join([
            self.name, self.category, self.description,
            " ".join(self.skills), " ".join(self.job_levels),
        ])

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "url": self.url,
            "description": self.description, "category": self.category,
            "duration_minutes": self.duration_minutes, "remote": self.remote,
            "adaptive": self.adaptive, "job_levels": self.job_levels,
            "languages": self.languages, "skills": self.skills,
        }
