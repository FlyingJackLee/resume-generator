from __future__ import annotations

import json
import logging
from typing import Any

import yaml

from resume_agent.config import Settings
from resume_agent.errors import ResumeAgentError
from resume_agent.models import (
    HRReview,
    HiringEvaluation,
    JobProfile,
    MatchReport,
    ResumePatch,
    RewriteStrategy,
)
from resume_agent.prompts import PromptRepository
from resume_agent.providers import StructuredProvider
from resume_agent.services.catalog import editable_catalog
from resume_agent.services.master_resume import collect_facts
from resume_agent.services.strategy_validator import validate_strategy


logger = logging.getLogger(__name__)


def _json(value: Any) -> str:
    if isinstance(value, dict):
        payload = value
    elif hasattr(value, "model_dump"):
        payload = value.model_dump()
    else:
        payload = value
    return json.dumps(payload, ensure_ascii=False, indent=2)


class AgentNodes:
    def __init__(
        self,
        provider: StructuredProvider,
        settings: Settings,
        prompts: PromptRepository | None = None,
    ):
        self.provider = provider
        self.settings = settings
        self.prompts = prompts or PromptRepository()

    @staticmethod
    def _completed(node: str, output: Any) -> None:
        logger.info("node completed: %s", node)
        logger.debug("node output %s:\n%s", node, _json(output))

    def analyze_jd(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info("node started: analyze_jd run_id=%s", state.get("run_id"))
        profile = self.provider.complete(
            system=self.prompts.load("jd_analyzer"),
            user=f"<UNTRUSTED_JOB_DESCRIPTION>\n{state['job_description']}\n</UNTRUSTED_JOB_DESCRIPTION>",
            output_type=JobProfile,
            temperature=0.1,
        )
        self._completed("analyze_jd", profile)
        return {"job_profile": profile.model_dump(), "status": "MATCHING"}

    def match_resume(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info("node started: match_resume run_id=%s", state.get("run_id"))
        facts = collect_facts(state["original_resume"])
        report = self.provider.complete(
            system=self.prompts.load("resume_matcher"),
            user=f"JOB_PROFILE:\n{_json(state['job_profile'])}\n\nIMMUTABLE_FACTS:\n{_json(facts)}",
            output_type=MatchReport,
            temperature=0.1,
        )
        requirement_ids = {
            requirement["id"] for requirement in state["job_profile"]["requirements"]
        }
        result_ids = {match.requirement_id for match in report.matches}
        if result_ids != requirement_ids or len(report.matches) != len(result_ids):
            raise ResumeAgentError("Matcher 必须且只能覆盖 JobProfile 中的全部 requirement IDs")
        fact_ids = set(facts)
        for match in report.matches:
            unknown = set(match.fact_ids) - fact_ids
            if unknown:
                raise ResumeAgentError(f"Matcher 引用了不存在的 facts：{sorted(unknown)}")
            if match.status == "missing" and match.fact_ids:
                raise ResumeAgentError("missing requirement 不得绑定 facts")
        self._completed("match_resume", report)
        return {"match_report": report.model_dump(), "status": "HR_REVIEWING"}

    def hr_review(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info("node started: hr_review run_id=%s", state.get("run_id"))
        review = self.provider.complete(
            system=self.prompts.load("hr_reviewer"),
            user=(
                f"JOB_PROFILE:\n{_json(state['job_profile'])}\n\n"
                f"MATCH_REPORT:\n{_json(state['match_report'])}\n\n"
                f"CURRENT_RESUME:\n{yaml.safe_dump(state['original_resume'], allow_unicode=True, sort_keys=False)}"
            ),
            output_type=HRReview,
            temperature=0.2,
        )
        self._completed("hr_review", review)
        return {"hr_review": review.model_dump(), "status": "STRATEGIZING"}

    def build_strategy(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info("node started: build_strategy run_id=%s", state.get("run_id"))
        facts = collect_facts(state["original_resume"])
        catalog = editable_catalog(state["original_resume"])
        strategy = self.provider.complete(
            system=self.prompts.load("rewrite_strategy"),
            user=(
                f"JOB_PROFILE:\n{_json(state['job_profile'])}\n\n"
                f"HR_REVIEW:\n{_json(state['hr_review'])}\n\n"
                f"EDITABLE_CATALOG:\n{_json(catalog)}\n\nFACTS:\n{_json(facts)}"
            ),
            output_type=RewriteStrategy,
            temperature=0.2,
        )
        validate_strategy(strategy, state["original_resume"])
        self._completed("build_strategy", strategy)
        return {
            "rewrite_strategy": strategy.model_dump(),
            "status": "WAITING_STRATEGY_APPROVAL",
        }

    def edit_resume(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info(
            "node started: edit_resume run_id=%s iteration=%s",
            state.get("run_id"),
            state.get("iteration", 0) + 1,
        )
        feedback = {
            "fact_validation": state.get("fact_validation"),
            "hiring_evaluation": state.get("hiring_evaluation"),
        }
        patch = self.provider.complete(
            system=self.prompts.load("resume_editor"),
            user=(
                f"APPROVED_STRATEGY:\n{_json(state['approved_strategy'])}\n\n"
                f"EDITABLE_CATALOG:\n{_json(editable_catalog(state['original_resume']))}\n\n"
                f"MASTER_WORKING_COPY:\n{yaml.safe_dump(state['original_resume'], allow_unicode=True, sort_keys=False)}\n\n"
                f"PREVIOUS_FEEDBACK:\n{_json(feedback)}"
            ),
            output_type=ResumePatch,
            temperature=0.2,
        )
        strategy = RewriteStrategy.model_validate(state["approved_strategy"])
        allowed = {action.target_path: set(action.supported_by) for action in strategy.actions}
        for operation in patch.operations:
            if operation.path not in allowed:
                raise ResumeAgentError(f"Editor 偏离 approved_strategy：{operation.path}")
            if set(operation.supported_by) - allowed[operation.path]:
                raise ResumeAgentError(f"Editor 使用了策略未批准的 facts：{operation.path}")
        self._completed("edit_resume", patch)
        return {
            "editor_patch": patch.model_dump(),
            "iteration": state.get("iteration", 0) + 1,
            "status": "APPLYING_PATCH",
        }

    def hiring_manager(self, state: dict[str, Any]) -> dict[str, Any]:
        logger.info(
            "node started: hiring_manager run_id=%s iteration=%s",
            state.get("run_id"),
            state.get("iteration"),
        )
        evaluation = self.provider.complete(
            system=self.prompts.load("hiring_manager"),
            user=(
                f"JOB_PROFILE:\n{_json(state['job_profile'])}\n\n"
                f"CANDIDATE_RESUME:\n{yaml.safe_dump(state['candidate_resume'], allow_unicode=True, sort_keys=False)}"
            ),
            output_type=HiringEvaluation,
            temperature=0.1,
        )
        decision = "PASS" if evaluation.scores.total >= self.settings.hiring_threshold else "REVISE"
        payload = evaluation.model_dump()
        payload["decision"] = decision
        payload["total_score"] = evaluation.scores.total
        self._completed("hiring_manager", payload)
        return {"hiring_evaluation": payload, "status": "HIRING_REVIEWED"}
