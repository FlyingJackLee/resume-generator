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
    ValidationIssue,
)
from resume_agent.prompts import PromptRepository
from resume_agent.providers import StructuredProvider
from resume_agent.services.catalog import editable_catalog
from resume_agent.services.master_resume import collect_facts
from resume_agent.services.resume_labels import path_label
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
            "patch_validation": state.get("patch_validation"),
        }
        previous_patch = state.get("editor_patch")
        previous_patch_block = (
            f"PREVIOUS_PATCH (your own last attempt — reuse every operation whose path\n"
            f"PREVIOUS_FEEDBACK did not flag exactly as-is, byte-for-byte including\n"
            f"supported_by; only regenerate operations for paths the feedback flagged):\n"
            f"{_json(previous_patch)}\n\n"
            if previous_patch
            else ""
        )
        patch = self.provider.complete(
            system=self.prompts.load("resume_editor"),
            user=(
                f"APPROVED_STRATEGY:\n{_json(state['approved_strategy'])}\n\n"
                f"EDITABLE_CATALOG:\n{_json(editable_catalog(state['original_resume']))}\n\n"
                f"MASTER_WORKING_COPY:\n{yaml.safe_dump(state['original_resume'], allow_unicode=True, sort_keys=False)}\n\n"
                f"{previous_patch_block}"
                f"PREVIOUS_FEEDBACK:\n{_json(feedback)}"
            ),
            output_type=ResumePatch,
            temperature=0.2,
        )
        strategy = RewriteStrategy.model_validate(state["approved_strategy"])
        allowed = {action.target_path: set(action.supported_by) for action in strategy.actions}
        issues: list[ValidationIssue] = []
        for operation in patch.operations:
            label = path_label(state["original_resume"], operation.path)
            if operation.path not in allowed:
                issues.append(
                    ValidationIssue(
                        code="P01",
                        severity="critical",
                        path=operation.path,
                        message=f"Editor 想修改「{label}」，但这个字段不在批准的策略范围内",
                    )
                )
                continue
            disallowed = sorted(set(operation.supported_by) - allowed[operation.path])
            if disallowed:
                issues.append(
                    ValidationIssue(
                        code="P02",
                        severity="critical",
                        path=operation.path,
                        message=f"Editor 给「{label}」引用了未获批准的事实来源",
                    )
                )
        iteration = state.get("iteration", 0) + 1
        if issues:
            logger.warning(
                "edit_resume patch violated approved strategy run_id=%s iteration=%s issues=%s",
                state.get("run_id"),
                iteration,
                [issue.model_dump() for issue in issues],
            )
            return {
                "editor_patch": patch.model_dump(),
                "patch_validation": {"passed": False, "issues": [issue.model_dump() for issue in issues]},
                "iteration": iteration,
                "status": "REVISING",
            }
        self._completed("edit_resume", patch)
        return {
            "editor_patch": patch.model_dump(),
            "patch_validation": {"passed": True, "issues": []},
            "iteration": iteration,
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
