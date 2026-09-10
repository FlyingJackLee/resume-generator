from __future__ import annotations

import traceback
import logging
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from langsmith import traceable

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
from .resume_import import IMPORT_SYSTEM_PROMPT, ParsedResume, extract_upload, normalize_resume, source_language_hint
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


def _trace_run_input(inputs: dict[str, Any]) -> dict[str, str]:
    """Keep the custom workflow span useful without duplicating resume/JD text."""
    return {"run_id": str(inputs.get("run_id", ""))}


def _trace_empty_output(_: Any) -> dict[str, str]:
    # Graph and LLM child spans contain their own diagnostic information. The
    # enclosing service span only represents lifecycle and duration.
    return {}


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

    def _editor_draft_dir(self) -> Path | None:
        if not self.runs_root.exists():
            return None
        drafts = [
            path for path in self.runs_root.iterdir()
            if path.is_dir() and (path / "run.json").exists()
            and read_metadata(path).get("editor_draft")
        ]
        return max(drafts, key=lambda path: read_metadata(path).get("created_at", ""), default=None)

    def get_or_create_editor_draft(self, label: str = "在线编辑草稿") -> dict[str, Any]:
        existing = self._editor_draft_dir()
        if existing:
            return read_metadata(existing)
        master_bytes = self.master_path.read_bytes()
        run_dir = create_run(
            label,
            "用于在线编辑的个人简历草稿。",
            master_bytes,
            root=self.runs_root,
        )
        write_yaml(run_dir, "editor_resume.yaml", load_master_resume(self.master_path))
        metadata = update_metadata(
            run_dir,
            status="COMPLETED",
            stage="在线编辑草稿",
            editor_draft=True,
            draft_base_sha256=hashlib.sha256(master_bytes).hexdigest(),
        )
        self._append_editor_version(run_dir, load_master_resume(self.master_path), "初始版本")
        return metadata

    # Backwards-compatible name while callers migrate to the singleton draft API.
    create_editor_draft = get_or_create_editor_draft

    def _versions_path(self, run_dir: Path) -> Path:
        return run_dir / "editor_versions.json"

    def _versions(self, run_dir: Path) -> list[dict[str, Any]]:
        return read_json(run_dir, "editor_versions.json") if self._versions_path(run_dir).exists() else []

    def _append_editor_version(self, run_dir: Path, resume: dict[str, Any], message: str) -> dict[str, Any]:
        versions = self._versions(run_dir)
        version_id = f"v{len(versions) + 1:03d}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        filename = f"editor_version_{version_id}.yaml"
        write_yaml(run_dir, filename, resume)
        version = {
            "id": version_id,
            "filename": filename,
            "message": message,
            "created_at": datetime.now(UTC).isoformat(),
        }
        versions.append(version)
        write_json(run_dir, "editor_versions.json", versions)
        return version

    @staticmethod
    def _editable_filename(metadata: dict[str, Any]) -> str:
        """Which YAML file free-form editing reads/writes for this run.

        The singleton editor draft always owns editor_resume.yaml. A COMPLETED
        run is editable in place on its own exported target_file — there is no
        publish gate for it, unlike the draft, since there is no shared
        baseline underneath it to protect. Every other run state (still being
        processed by the agent pipeline, or awaiting Gate② approval) is not
        editable this way at all.
        """
        if metadata.get("editor_draft"):
            return "editor_resume.yaml"
        if metadata.get("status") == "COMPLETED" and metadata.get("target_file"):
            return metadata["target_file"]
        raise ResumeAgentError("该 run 当前不支持在线编辑")

    def get_editor_draft(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        return read_yaml(run_dir, self._editable_filename(read_metadata(run_dir)))

    def update_editor_draft(self, run_id: str, resume: dict[str, Any]) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        filename = self._editable_filename(metadata)
        if not isinstance(resume.get("meta"), dict) or not isinstance(resume.get("sections"), list):
            raise ResumeAgentError("简历必须包含 meta 对象和 sections 数组")
        # Render before committing so a malformed edit never replaces the last usable copy.
        from .preview_service import _render

        candidate = run_dir / "editor_save.preview.yaml"
        write_yaml(run_dir, candidate.name, resume)
        try:
            _render(candidate, "zh")
            _render(candidate, "en")
            candidate.replace(run_dir / filename)
        finally:
            if candidate.exists():
                candidate.unlink()
        if metadata.get("editor_draft"):
            return update_metadata(run_dir, stage="在线编辑草稿", editor_draft=True)
        return update_metadata(run_dir, stage="已手动编辑")

    def has_approved_snapshot(self, run_id: str) -> bool:
        return (self.resolve_run(run_id) / "approved_snapshot.yaml").exists()

    def restore_approved_snapshot(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if metadata.get("status") != "COMPLETED":
            raise ResumeAgentError("当前状态不能恢复批准时版本")
        snapshot_path = run_dir / "approved_snapshot.yaml"
        if not snapshot_path.exists():
            raise ResumeAgentError("这个 run 没有可恢复的批准快照")
        write_yaml(run_dir, metadata["target_file"], read_yaml(run_dir, "approved_snapshot.yaml"))
        return update_metadata(run_dir, stage="已恢复批准时版本")

    @traceable(
        name="Resume import",
        run_type="chain",
        process_inputs=lambda inputs: {
            "run_id": str(inputs.get("run_id", "")),
            "filename": str(inputs.get("filename", "")),
            "upload_bytes": len(inputs.get("payload", b"")),
        },
        process_outputs=lambda output: {
            "source_languages": output.get("source_languages", []),
            "warning_count": len(output.get("warnings", [])),
        },
    )
    def import_editor_resume(self, run_id: str, filename: str, payload: bytes) -> dict[str, Any]:
        """Imports into the editable draft only; it never changes the Master Resume."""
        run_dir = self.resolve_run(run_id)
        if not read_metadata(run_dir).get("editor_draft"):
            raise ResumeAgentError("该 run 不是在线编辑草稿")
        suffix = Path(filename).suffix.lower()
        (run_dir / f"source_upload{suffix}").write_bytes(payload)
        text, yaml_resume, extraction_method = extract_upload(
            filename,
            payload,
            ocr_max_pages=self.settings.ocr_max_pages,
            scan_parser=self.settings.scan_parser,
            mineru_api_base_url=self.settings.mineru_api_base_url,
            mineru_api_token=self.settings.mineru_api_token,
            mineru_model_version=self.settings.mineru_model_version,
            mineru_timeout_seconds=self.settings.mineru_timeout_seconds,
        )
        if yaml_resume is not None and isinstance(yaml_resume.get("meta"), dict) and isinstance(yaml_resume.get("sections"), list):
            parsed = ParsedResume(resume=yaml_resume, source_languages=["zh", "en"])
        else:
            if yaml_resume is not None:
                text = json.dumps(yaml_resume, ensure_ascii=False)
            if not text:
                raise ResumeAgentError("上传文件不包含可解析内容")
            parsed = self.nodes.provider.complete(system=IMPORT_SYSTEM_PROMPT, user=f"Extract this resume:\n\n{text[:120_000]}", output_type=ParsedResume, temperature=0)
            detected = source_language_hint(text)
            if detected:
                parsed.source_languages = detected
        resume = normalize_resume(parsed.resume, parsed.source_languages)
        self.update_editor_draft(run_id, resume)
        self._append_editor_version(run_dir, resume, f"从 {filename} 导入")
        return {
            "resume": resume,
            "source_languages": parsed.source_languages,
            "warnings": parsed.warnings,
            "extraction_method": extraction_method,
        }

    def editor_versions(self, run_id: str) -> list[dict[str, Any]]:
        run_dir = self.resolve_run(run_id)
        if not read_metadata(run_dir).get("editor_draft"):
            raise ResumeAgentError("该 run 不是在线编辑草稿")
        return self._versions(run_dir)

    def editor_external_change(self, run_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        metadata = read_metadata(run_dir)
        if not metadata.get("editor_draft"):
            raise ResumeAgentError("该 run 不是在线编辑草稿")
        current_sha = hashlib.sha256(self.master_path.read_bytes()).hexdigest()
        return {"changed": current_sha != metadata.get("draft_base_sha256"), "master_sha256": current_sha}

    def resolve_editor_external_change(self, run_id: str, action: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        if action not in {"reload", "keep"}:
            raise ResumeAgentError("action 必须是 reload 或 keep")
        master_bytes = self.master_path.read_bytes()
        if action == "reload":
            write_yaml(run_dir, "editor_resume.yaml", load_master_resume(self.master_path))
        return update_metadata(run_dir, draft_base_sha256=hashlib.sha256(master_bytes).hexdigest())

    def publish_editor_draft(self, run_id: str, message: str = "发布版本") -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        if not read_metadata(run_dir).get("editor_draft"):
            raise ResumeAgentError("该 run 不是在线编辑草稿")
        resume = read_yaml(run_dir, "editor_resume.yaml")
        # Verify both language versions before making the one allowed Master mutation.
        from .preview_service import _render
        _render(run_dir / "editor_resume.yaml", "zh")
        _render(run_dir / "editor_resume.yaml", "en")
        self._append_editor_version(run_dir, resume, message)
        temp = self.master_path.with_suffix(".yaml.publish.tmp")
        # write_yaml intentionally only permits run artifacts, so use an atomic write here.
        import yaml
        temp.write_text(yaml.safe_dump(resume, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
        temp.replace(self.master_path)
        return update_metadata(
            run_dir,
            draft_base_sha256=hashlib.sha256(self.master_path.read_bytes()).hexdigest(),
            stage="已发布到 Master Resume",
            editor_draft=True,
        )

    def rollback_editor_version(self, run_id: str, version_id: str) -> dict[str, Any]:
        run_dir = self.resolve_run(run_id)
        version = next((item for item in self._versions(run_dir) if item["id"] == version_id), None)
        if not version:
            raise ResumeAgentError("版本不存在")
        resume = read_yaml(run_dir, version["filename"])
        write_yaml(run_dir, "editor_resume.yaml", resume)
        return self.publish_editor_draft(run_id, f"回退至 {version_id}")

    def _company_update(self, run_dir: Path, job_profile: dict[str, Any]) -> dict[str, Any]:
        if read_metadata(run_dir).get("company"):
            return {}
        target_company = (job_profile or {}).get("target_company")
        return {"company": target_company} if target_company else {}

    @traceable(
        name="Resume analysis workflow",
        run_type="chain",
        process_inputs=_trace_run_input,
        process_outputs=_trace_empty_output,
    )
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
                config={
                    "tags": ["resume-analysis", run_id],
                    "run_name": f"Resume analysis · {run_id}",
                    "metadata": {"resume_run_id": run_id, "workflow": "analysis"},
                },
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
        if (run_dir / "approved_strategy.json").exists():
            # Gate ① 已经批准过，只是 compile 阶段本身失败（比如 Editor 越权）——从已批准的
            # 策略重新 compile，不重新生成策略、不用再走一次 Gate①
            return update_metadata(
                run_dir,
                status="EDITING",
                stage="Resume Editor（重试编译）",
                progress_current=0,
                progress_total=4,
                error=None,
            )
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

    def auto_approve_timed_out_gates(self) -> list[str]:
        """Scan every run for a Human Gate wait that has sat past
        settings.auto_approve_minutes and approve it automatically.

        Gate ①（策略）超时后直接原样接受 AI 生成的策略——没有质量分数可参考，超时本身就是
        唯一信号。Gate ②（最终版本）超时后只有 hiring_score 已经达到 hiring_threshold 才会
        自动批准；分数不够的 run 无论等多久都不会被自动处理，继续留给人工。auto_approve_minutes
        <= 0 表示整个功能关闭。

        Returns the run_ids that were auto-approved at Gate ① and now need
        compile() launched in the background — Gate ② needs no further work
        since approve_final() finishes synchronously.
        """
        minutes = self.settings.auto_approve_minutes
        if minutes <= 0 or not self.runs_root.exists():
            return []
        threshold = timedelta(minutes=minutes)
        now = datetime.now(UTC)
        needs_compile: list[str] = []
        for run_dir in self.runs_root.iterdir():
            if not (run_dir.is_dir() and (run_dir / "run.json").exists()):
                continue
            metadata = read_metadata(run_dir)
            status = metadata.get("status")
            if status not in ("WAITING_STRATEGY_APPROVAL", "WAITING_FINAL_APPROVAL"):
                continue
            updated_at = metadata.get("updated_at")
            if not updated_at or now - datetime.fromisoformat(updated_at) < threshold:
                continue
            run_id = metadata["run_id"]
            try:
                if status == "WAITING_STRATEGY_APPROVAL":
                    self.approve_strategy(run_id)
                    needs_compile.append(run_id)
                elif (metadata.get("hiring_score") or 0) >= self.settings.hiring_threshold:
                    self.approve_final(run_id)
            except ResumeAgentError:
                logger.exception("auto-approve failed run_id=%s", run_id)
        return needs_compile

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

    @traceable(
        name="Resume rewrite workflow",
        run_type="chain",
        process_inputs=_trace_run_input,
        process_outputs=_trace_empty_output,
    )
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
                config={
                    "recursion_limit": 30,
                    "tags": ["resume-rewrite", run_id],
                    "run_name": f"Resume rewrite · {run_id}",
                    "metadata": {"resume_run_id": run_id, "workflow": "rewrite"},
                },
                stream_mode="updates",
            ):
                for node_name, update in event.items():
                    logger.debug("langgraph event run_id=%s node=%s update=%s", run_id, node_name, update)
                    result.update(update)
                    iteration = result.get("iteration", 0)
                    if node_name == "edit_resume":
                        write_json(run_dir, f"edit_{iteration:02d}.patch.json", result["editor_patch"])
                        if result.get("patch_validation", {}).get("passed", True):
                            stage, progress = "Patch Engine", 2
                        else:
                            stage, progress = "Resume Editor 返工", 1
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
                    elif node_name == "patch_validation_failed":
                        stage, progress = "策略校验失败", 4
                    else:
                        stage, progress = "Human Gate ②：等待最终确认", 4
                    event_status = update.get("status", result.get("status", "EDITING"))
                    if node_name in {"final_ready", "validation_failed", "patch_validation_failed"}:
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
            if not result.get("patch_validation", {}).get("passed", True):
                # edit_resume never produced a strategy-compliant patch within max_iterations —
                # apply_patch/validate_facts never ran, so there is no candidate_resume or
                # fact_validation to persist. Surface the structural issues instead.
                write_json(run_dir, "edit.patch.json", result["editor_patch"])
                update_metadata(
                    run_dir,
                    status="FAILED",
                    iteration=result["iteration"],
                    stage="策略校验失败",
                )
                write_json(
                    run_dir,
                    "error.json",
                    {
                        "type": "StrategyComplianceError",
                        "message": "Resume Editor 多次尝试后，仍未能在批准的策略范围内完成这次改写",
                        "issues": result["patch_validation"]["issues"],
                    },
                )
                logger.info("compile graph finished run_id=%s status=FAILED (strategy compliance)", run_id)
                return
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
        # A one-level undo for later free-form edits: what the AI actually produced
        # and you approved, frozen at the moment of approval.
        write_yaml(run_dir, "approved_snapshot.yaml", candidate)
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
