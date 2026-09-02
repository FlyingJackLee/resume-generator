from __future__ import annotations

import traceback
import logging
from pathlib import Path
from typing import Any

from resume_agent.agents import AgentNodes
from resume_agent.config import Settings
from resume_agent.errors import ResumeAgentError
from resume_agent.graph import build_analysis_graph, build_compile_graph
from resume_agent.models import ResumePatch, RewriteStrategy
from resume_agent.paths import MASTER_RESUME_PATH, RUNS_ROOT
from resume_agent.providers import StructuredProvider

from .diff_service import build_diff
from .fact_validator import validate_candidate
from .master_resume import load_master_resume, prepare_working_resume
from .patch_engine import apply_patch
from .run_store import (
    create_run,
    read_events,
    read_json,
    read_metadata,
    read_yaml,
    update_metadata,
    write_json,
    write_target,
    write_yaml,
)
from .strategy_validator import validate_strategy


logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(
        self,
        provider: StructuredProvider,
        settings: Settings,
        runs_root: Path = RUNS_ROOT,
        master_path: Path = MASTER_RESUME_PATH,
    ):
        self.settings = settings
        self.runs_root = runs_root
        self.master_path = master_path
        nodes = AgentNodes(provider, settings)
        self.nodes = nodes
        self.analysis_graph = build_analysis_graph(nodes)
        self.compile_graph = build_compile_graph(nodes)
        logger.debug("analysis graph topology:\n%s", self.analysis_graph.get_graph().draw_mermaid())
        logger.debug("compile graph topology:\n%s", self.compile_graph.get_graph().draw_mermaid())
        self._mark_stale_runs_interrupted()

    def _mark_stale_runs_interrupted(self) -> None:
        active = {
            "ANALYZING", "MATCHING", "HR_REVIEWING", "STRATEGIZING", "EDITING",
            "APPLYING_PATCH", "VALIDATING", "REVIEWING", "REVISING",
            "HIRING_REVIEWED", "FINALIZING",
        }
        if not self.runs_root.exists():
            return
        for run_dir in self.runs_root.iterdir():
            if run_dir.is_dir() and (run_dir / "run.json").exists():
                metadata = read_metadata(run_dir)
                if metadata.get("status") in active:
                    update_metadata(
                        run_dir,
                        status="INTERRUPTED",
                        stage="服务曾中断，可从本 run 重试",
                        error="服务在后台任务完成前停止",
                    )

    def resolve_run(self, run_id: str) -> Path:
        if not run_id.startswith("run_") or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for char in run_id):
            raise ResumeAgentError("run_id 不安全")
        run_dir = self.runs_root / run_id
        if not run_dir.is_dir():
            raise ResumeAgentError(f"run 不存在：{run_id}")
        return run_dir

    def create(self, jd_label: str, jd: str, company: str | None = None) -> dict[str, Any]:
        master_bytes = self.master_path.read_bytes()
        run_dir = create_run(jd_label, jd, master_bytes, root=self.runs_root, company=company)
        working = prepare_working_resume(load_master_resume(self.master_path))
        write_yaml(run_dir, "input_resume.yaml", working)
        return update_metadata(run_dir, status="ANALYZING")

    def _company_update(self, run_dir: Path, job_profile: dict[str, Any]) -> dict[str, Any]:
        if read_metadata(run_dir).get("company"):
            return {}
        target_company = (job_profile or {}).get("target_company")
        return {"company": target_company} if target_company else {}

    def analyze(self, run_id: str) -> None:
        run_dir = self.resolve_run(run_id)
        logger.info("analysis graph started run_id=%s", run_id)
        try:
            state = {
                "run_id": run_id,
                "original_resume": read_yaml(run_dir, "input_resume.yaml"),
                "job_description": (run_dir / "jd.txt").read_text(encoding="utf-8"),
                "iteration": 0,
                "max_iterations": self.settings.max_iterations,
                "status": "ANALYZING",
            }
            completed_artifacts = (
                ("job_profile", "job_profile.json"),
                ("match_report", "match_report.json"),
                ("hr_review", "hr_review.json"),
            )
            for key, filename in completed_artifacts:
                if (run_dir / filename).exists():
                    state[key] = read_json(run_dir, filename)
            if all(key in state for key, _ in completed_artifacts):
                update_metadata(
                    run_dir,
                    status="STRATEGIZING",
                    stage="Rewrite Strategy（断点续跑）",
                    progress_current=3,
                    progress_total=4,
                    **self._company_update(run_dir, state["job_profile"]),
                )
                update = self.nodes.build_strategy(state)
                write_json(run_dir, "rewrite_strategy.json", update["rewrite_strategy"])
                update_metadata(
                    run_dir,
                    status="WAITING_STRATEGY_APPROVAL",
                    stage="Human Gate ①：等待策略确认",
                    last_completed_node="build_strategy",
                    progress_current=4,
                    progress_total=4,
                )
                return
            artifacts = {
                "analyze_jd": ("job_profile", "job_profile.json"),
                "match_resume": ("match_report", "match_report.json"),
                "hr_review": ("hr_review", "hr_review.json"),
                "build_strategy": ("rewrite_strategy", "rewrite_strategy.json"),
            }
            next_stage = {
                "analyze_jd": "Resume Matcher",
                "match_resume": "HR Reviewer",
                "hr_review": "Rewrite Strategy",
                "build_strategy": "Human Gate ①",
            }
            completed = {"analyze_jd": 1, "match_resume": 2, "hr_review": 3, "build_strategy": 4}
            update_metadata(
                run_dir,
                status="ANALYZING",
                stage="JD Analyzer",
                progress_current=0,
                progress_total=4,
            )
            result = dict(state)
            for event in self.analysis_graph.stream(
                state,
                config={"tags": [run_id], "run_name": run_id},
                stream_mode="updates",
            ):
                for node_name, update in event.items():
                    logger.debug("langgraph event run_id=%s node=%s update=%s", run_id, node_name, update)
                    result.update(update)
                    key, filename = artifacts[node_name]
                    write_json(run_dir, filename, result[key])
                    extra = (
                        self._company_update(run_dir, result["job_profile"])
                        if node_name == "analyze_jd"
                        else {}
                    )
                    update_metadata(
                        run_dir,
                        status=update.get("status", "ANALYZING"),
                        stage=next_stage[node_name],
                        last_completed_node=node_name,
                        progress_current=completed[node_name],
                        progress_total=4,
                        **extra,
                    )
            update_metadata(
                run_dir,
                status="WAITING_STRATEGY_APPROVAL",
                stage="Human Gate ①：等待策略确认",
                progress_current=4,
                progress_total=4,
            )
            logger.info("analysis graph reached Human Gate 1 run_id=%s", run_id)
        except Exception as exc:
            logger.exception("analysis graph failed run_id=%s", run_id)
            self._fail(run_dir, exc)

    def retry_analysis(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if metadata["status"] not in {"FAILED", "INTERRUPTED"}:
            raise ResumeAgentError("只有失败或中断的分析 run 可以重试")
        error_path = run_dir / "error.json"
        if error_path.exists():
            error_path.replace(run_dir / "error.previous.json")
        if (run_dir / "hr_review.json").exists():
            stage, progress = "Rewrite Strategy（断点续跑）", 3
        elif (run_dir / "match_report.json").exists():
            stage, progress = "HR Reviewer（断点续跑）", 2
        elif (run_dir / "job_profile.json").exists():
            stage, progress = "Resume Matcher（断点续跑）", 1
        else:
            stage, progress = "JD Analyzer", 0
        return update_metadata(
            run_dir,
            status="ANALYZING",
            stage=stage,
            progress_current=progress,
            progress_total=4,
            error=None,
        )

    def retry_validation(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if metadata["status"] != "FAILED" or not (run_dir / "candidate_resume.yaml").exists():
            raise ResumeAgentError("当前 run 没有可重新校验的候选简历")
        error_path = run_dir / "error.json"
        if error_path.exists():
            error_path.replace(run_dir / "error.previous.json")
        return update_metadata(
            run_dir,
            status="VALIDATING",
            stage="Fact Validator（从候选版本继续）",
            error=None,
            progress_current=2,
            progress_total=4,
        )

    def validate_and_review(self, run_id: str) -> None:
        run_dir = self.resolve_run(run_id)
        try:
            master = read_yaml(run_dir, "input_resume.yaml")
            candidate = read_yaml(run_dir, "candidate_resume.yaml")
            validation = validate_candidate(master, candidate)
            write_json(run_dir, "validation.json", validation.model_dump())
            iteration = read_metadata(run_dir).get("iteration", self.settings.max_iterations)
            write_json(run_dir, f"validation_{iteration:02d}.json", validation.model_dump())
            if not validation.passed:
                write_json(
                    run_dir,
                    "error.json",
                    {"type": "FactValidationError", "message": "事实校验未通过", "issues": validation.model_dump()["issues"]},
                )
                update_metadata(run_dir, status="FAILED", stage="事实校验失败")
                return
            update_metadata(
                run_dir,
                status="REVIEWING",
                stage="Hiring Manager",
                progress_current=3,
                progress_total=4,
            )
            state = {
                "run_id": run_id,
                "original_resume": master,
                "candidate_resume": candidate,
                "job_profile": read_json(run_dir, "job_profile.json"),
                "iteration": iteration,
            }
            update = self.nodes.hiring_manager(state)
            evaluation = update["hiring_evaluation"]
            write_json(run_dir, "hiring_review.json", evaluation)
            write_json(run_dir, f"hiring_review_{iteration:02d}.json", evaluation)
            update_metadata(
                run_dir,
                status="WAITING_FINAL_APPROVAL",
                stage="Human Gate ②：等待最终确认",
                hiring_score=evaluation["total_score"],
                progress_current=4,
                progress_total=4,
            )
        except Exception as exc:
            logger.exception("validation resume failed run_id=%s", run_id)
            self._fail(run_dir, exc)

    def approve_strategy(
        self, run_id: str, override: RewriteStrategy | None = None
    ) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if metadata["status"] != "WAITING_STRATEGY_APPROVAL":
            raise ResumeAgentError("当前状态不能批准策略")
        strategy = override.model_dump() if override else read_json(run_dir, "rewrite_strategy.json")
        parsed = RewriteStrategy.model_validate(strategy)
        validate_strategy(parsed, read_yaml(run_dir, "input_resume.yaml"))
        write_json(run_dir, "approved_strategy.json", strategy)
        return update_metadata(run_dir, status="EDITING")

    def revise_strategy(self, run_id: str, strategy: RewriteStrategy) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if metadata["status"] != "WAITING_STRATEGY_APPROVAL":
            raise ResumeAgentError("当前状态不能修改策略")
        validate_strategy(strategy, read_yaml(run_dir, "input_resume.yaml"))
        write_json(run_dir, "rewrite_strategy.json", strategy.model_dump())
        return read_metadata(run_dir)

    def compile(self, run_id: str) -> None:
        run_dir = self.resolve_run(run_id)
        logger.info("compile graph started run_id=%s", run_id)
        try:
            state = {
                "run_id": run_id,
                "original_resume": read_yaml(run_dir, "input_resume.yaml"),
                "job_description": (run_dir / "jd.txt").read_text(encoding="utf-8"),
                "job_profile": read_json(run_dir, "job_profile.json"),
                "approved_strategy": read_json(run_dir, "approved_strategy.json"),
                "iteration": 0,
                "max_iterations": self.settings.max_iterations,
                "status": "EDITING",
            }
            update_metadata(
                run_dir,
                status="EDITING",
                stage="Resume Editor",
                iteration=1,
                progress_current=0,
                progress_total=4,
            )
            result = dict(state)
            for event in self.compile_graph.stream(
                state,
                config={"recursion_limit": 30, "tags": [run_id], "run_name": run_id},
                stream_mode="updates",
            ):
                for node_name, update in event.items():
                    logger.debug("langgraph event run_id=%s node=%s update=%s", run_id, node_name, update)
                    result.update(update)
                    iteration = result.get("iteration", 0)
                    if node_name == "edit_resume":
                        write_json(run_dir, f"edit_{iteration:02d}.patch.json", result["editor_patch"])
                        stage, progress = "Patch Engine", 2
                    elif node_name == "apply_patch":
                        write_yaml(run_dir, f"candidate_{iteration:02d}.yaml", result["candidate_resume"])
                        stage, progress = "Fact Validator", 3
                    elif node_name == "validate_facts":
                        write_json(run_dir, f"validation_{iteration:02d}.json", result["fact_validation"])
                        if result["fact_validation"]["passed"]:
                            stage, progress = "Hiring Manager", 4
                        else:
                            stage, progress = "Resume Editor 返工", 1
                    elif node_name == "hiring_manager":
                        write_json(run_dir, f"hiring_review_{iteration:02d}.json", result["hiring_evaluation"])
                        if result["hiring_evaluation"]["decision"] == "REVISE" and iteration < self.settings.max_iterations:
                            stage, progress = "Resume Editor 返工", 1
                        else:
                            stage, progress = "Human Gate ②", 4
                    elif node_name == "validation_failed":
                        stage, progress = "事实校验失败", 4
                    else:
                        stage, progress = "Human Gate ②：等待最终确认", 4
                    event_status = update.get("status", result.get("status", "EDITING"))
                    if node_name in {"final_ready", "validation_failed"}:
                        event_status = "FINALIZING"
                    update_metadata(
                        run_dir,
                        status=event_status,
                        stage=stage,
                        last_completed_node=node_name,
                        iteration=iteration,
                        progress_current=progress,
                        progress_total=4,
                    )
            write_json(run_dir, "edit.patch.json", result["editor_patch"])
            write_yaml(run_dir, "candidate_resume.yaml", result["candidate_resume"])
            write_json(run_dir, "validation.json", result["fact_validation"])
            if result.get("hiring_evaluation"):
                write_json(run_dir, "hiring_review.json", result["hiring_evaluation"])
            patch = ResumePatch.model_validate(result["editor_patch"])
            diff = build_diff(state["original_resume"], result["candidate_resume"], patch)
            write_json(run_dir, "final_diff.json", diff)
            write_json(run_dir, "all_operations.json", patch.model_dump()["operations"])
            update_metadata(
                run_dir,
                status=result["status"],
                iteration=result["iteration"],
                hiring_score=(result.get("hiring_evaluation") or {}).get("total_score"),
                stage=(
                    "Human Gate ②：等待最终确认"
                    if result["status"] == "WAITING_FINAL_APPROVAL"
                    else "事实校验失败"
                ),
            )
            if result["status"] == "FAILED":
                write_json(
                    run_dir,
                    "error.json",
                    {
                        "type": "FactValidationError",
                        "message": "事实校验在最大返工次数后仍未通过",
                        "issues": result["fact_validation"]["issues"],
                    },
                )
            logger.info("compile graph finished run_id=%s status=%s", run_id, result["status"])
        except Exception as exc:
            logger.exception("compile graph failed run_id=%s", run_id)
            self._fail(run_dir, exc)

    @staticmethod
    def _merge_operations(
        existing: list[dict[str, Any]], new_ops: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        by_path = {op["path"]: op for op in existing}
        for op in new_ops:
            by_path[op["path"]] = op
        return list(by_path.values())

    def manual_edit(self, run_id: str, patch: ResumePatch) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if metadata["status"] != "WAITING_FINAL_APPROVAL":
            raise ResumeAgentError("当前状态不能手动修改")
        master = read_yaml(run_dir, "input_resume.yaml")
        candidate = read_yaml(run_dir, "candidate_resume.yaml")
        revised = apply_patch(candidate, patch, restore_source=master)
        validation = validate_candidate(master, revised)
        write_json(run_dir, "manual_edit.patch.json", patch.model_dump())
        write_yaml(run_dir, "candidate_resume.yaml", revised)
        write_json(run_dir, "validation.json", validation.model_dump())

        existing_ops = read_json(run_dir, "all_operations.json") if (run_dir / "all_operations.json").exists() else []
        merged_ops = self._merge_operations(existing_ops, patch.model_dump()["operations"])
        write_json(run_dir, "all_operations.json", merged_ops)
        combined_patch = ResumePatch.model_validate({"operations": merged_ops})
        diff = build_diff(master, revised, combined_patch)
        write_json(run_dir, "final_diff.json", diff)

        status = "WAITING_FINAL_APPROVAL" if validation.passed else "FAILED"
        return update_metadata(run_dir, status=status)

    def approve_final(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if metadata["status"] != "WAITING_FINAL_APPROVAL":
            raise ResumeAgentError("当前状态不能批准最终版本")
        validation = read_json(run_dir, "validation.json")
        if not validation.get("passed"):
            raise ResumeAgentError("Fact Validator 未通过，禁止导出")
        candidate = read_yaml(run_dir, "candidate_resume.yaml")
        target = write_target(run_dir, metadata["output_name"], candidate)
        return update_metadata(run_dir, status="COMPLETED", target_file=target.name, stage="已批准导出")

    def reject_final(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        if read_metadata(run_dir)["status"] != "WAITING_FINAL_APPROVAL":
            raise ResumeAgentError("当前状态不能拒绝最终版本")
        return update_metadata(run_dir, status="REJECTED", stage="已拒绝")

    def restore_original(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        if read_metadata(run_dir)["status"] != "WAITING_FINAL_APPROVAL":
            raise ResumeAgentError("当前状态不能恢复原始版本")
        master = read_yaml(run_dir, "input_resume.yaml")
        validation = validate_candidate(master, master)
        write_yaml(run_dir, "candidate_resume.yaml", master)
        write_json(run_dir, "validation.json", validation.model_dump())
        write_json(run_dir, "final_diff.json", [])
        write_json(run_dir, "all_operations.json", [])
        return read_metadata(run_dir)

    def get(self, run_id: str) -> dict[str, Any]:
        metadata = read_metadata(self.resolve_run(run_id))
        metadata["langsmith_trace_url"] = self.settings.langsmith_project_url or None
        return metadata

    def get_diff(self, run_id: str) -> Any:
        return read_json(self.resolve_run(run_id), "final_diff.json")

    def update_notes(self, run_id: str, notes: str) -> dict[str, Any]:
        return update_metadata(self.resolve_run(run_id), notes=notes)

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        return read_events(self.resolve_run(run_id))

    def list_runs(self, page: int = 1, page_size: int | None = None) -> dict[str, Any]:
        if not self.runs_root.exists():
            results: list[dict[str, Any]] = []
        else:
            results = [
                read_metadata(path)
                for path in self.runs_root.iterdir()
                if path.is_dir() and (path / "run.json").exists()
            ]
        results.sort(key=lambda item: item["created_at"], reverse=True)
        total = len(results)
        if page_size is None:
            items = results
        else:
            start = (page - 1) * page_size
            items = results[start : start + page_size]
        return {"items": items, "total": total, "page": page, "page_size": page_size or total}

    @staticmethod
    def _fail(run_dir: Path, exc: Exception) -> None:
        write_json(
            run_dir,
            "error.json",
            {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
        )
        update_metadata(run_dir, status="FAILED", stage="运行失败", error=str(exc))
