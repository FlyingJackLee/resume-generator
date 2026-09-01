from __future__ import annotations

from typing import Any

from resume_agent.models import (
    HRReview,
    HiringEvaluation,
    JobProfile,
    MatchReport,
    ResumePatch,
    RewriteStrategy,
)
from resume_agent.services import load_master_resume, prepare_working_resume


class HappyProvider:
    def __init__(self):
        working = prepare_working_resume(load_master_resume())
        self.body = working["sections"][0]["body"]
        self.calls: list[str] = []

    def complete(self, *, system: str, user: str, output_type: type, temperature: float):
        self.calls.append(output_type.__name__)
        outputs: dict[type, dict[str, Any]] = {
            JobProfile: {
                "target_company": "Google",
                "target_role": "AI Agent Engineer",
                "seniority": "Senior",
                "requirements": [
                    {"id": "req_001", "category": "must_have", "statement": "Build AI agents", "weight": 100}
                ],
                "keywords": ["AI Agent", "LangGraph"],
            },
            MatchReport: {
                "matches": [
                    {
                        "requirement_id": "req_001",
                        "status": "full",
                        "fact_ids": ["fact_introduction_body"],
                        "confidence": 0.95,
                        "rationale": "Master Resume explicitly states AI Agent development.",
                    }
                ],
                "overall_summary": "Strong match",
            },
            HRReview: {
                "strengths": ["Agent engineering"],
                "weaknesses": ["Dense introduction"],
                "missing_keywords": [],
                "rewrite_priorities": ["Lead with agent delivery"],
            },
            RewriteStrategy: {
                "positioning": "AI Agent engineer with full-stack delivery experience",
                "safe_keywords": ["AI Agent", "LangGraph"],
                "forbidden_keywords": [],
                "actions": [
                    {
                        "action": "rewrite",
                        "target_path": "/sections/introduction/body",
                        "priority": 1,
                        "instruction": "Lead with AI Agent delivery",
                        "supported_by": ["fact_introduction_body"],
                    }
                ],
            },
            ResumePatch: {
                "operations": [
                    {
                        "op": "replace",
                        "path": "/sections/introduction/body",
                        "supported_by": ["fact_introduction_body"],
                        "reason": "Align positioning",
                        "value": {"zh": self.body["zh"], "en": self.body["en"]},
                    }
                ]
            },
            HiringEvaluation: {
                "scores": {
                    "jd_core_match": 28,
                    "relevant_experience": 18,
                    "technical_depth": 14,
                    "business_impact": 9,
                    "ats_keywords": 9,
                    "clarity": 9,
                    "credibility": 5,
                },
                "decision": "PASS",
                "strengths": ["Relevant"],
                "concerns": [],
                "feedback": [],
            },
        }
        return output_type.model_validate(outputs[output_type])

