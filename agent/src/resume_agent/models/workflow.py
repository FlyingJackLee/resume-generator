from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobRequirement(StrictModel):
    id: str
    category: Literal["must_have", "preferred", "responsibility"]
    statement: str
    weight: int = Field(ge=1, le=100)


class JobProfile(StrictModel):
    target_company: str
    target_role: str
    seniority: str
    requirements: list[JobRequirement] = Field(min_length=1)
    keywords: list[str]

    @model_validator(mode="after")
    def unique_requirement_ids(self) -> "JobProfile":
        ids = [requirement.id for requirement in self.requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("requirement IDs 必须唯一")
        return self


class RequirementMatch(StrictModel):
    requirement_id: str
    status: Literal["full", "partial", "missing"]
    fact_ids: list[str]
    confidence: float = Field(ge=0, le=1)
    rationale: str


class MatchReport(StrictModel):
    matches: list[RequirementMatch]
    overall_summary: str


class HRReview(StrictModel):
    strengths: list[str]
    weaknesses: list[str]
    missing_keywords: list[str]
    rewrite_priorities: list[str]


class RewriteAction(StrictModel):
    action: Literal["promote", "rewrite", "reorder", "deprioritize", "preserve"]
    target_path: str
    priority: int = Field(ge=1, le=5)
    instruction: str
    supported_by: list[str]


class RewriteStrategy(StrictModel):
    positioning: str
    safe_keywords: list[str]
    forbidden_keywords: list[str]
    actions: list[RewriteAction]


class HiringScores(StrictModel):
    jd_core_match: int = Field(ge=0, le=30)
    relevant_experience: int = Field(ge=0, le=20)
    technical_depth: int = Field(ge=0, le=15)
    business_impact: int = Field(ge=0, le=10)
    ats_keywords: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    credibility: int = Field(ge=0, le=5)

    @property
    def total(self) -> int:
        return sum(self.model_dump().values())


class HiringEvaluation(StrictModel):
    scores: HiringScores
    decision: Literal["PASS", "REVISE"]
    strengths: list[str]
    concerns: list[str]
    feedback: list[str]

    @model_validator(mode="after")
    def decision_matches_score_shape(self) -> "HiringEvaluation":
        # Threshold enforcement belongs to deterministic workflow configuration.
        return self


class StrategyDecision(StrictModel):
    strategy: RewriteStrategy | None = None


class ManualEditRequest(StrictModel):
    patch: "ResumePatch"


from .patch import ResumePatch  # noqa: E402

ManualEditRequest.model_rebuild()
