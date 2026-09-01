from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from threading import Thread
from typing import Annotated, Callable

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, Field

from resume_agent.config import get_settings
from resume_agent.errors import ResumeAgentError
from resume_agent.logging_config import configure_logging
from resume_agent.models import ManualEditRequest, ResumePatch, RewriteStrategy, StrategyDecision
from resume_agent.paths import PROJECT_ROOT
from resume_agent.providers import OpenAICompatibleProvider
from resume_agent.services.run_store import read_json
from resume_agent.services.master_resume import collect_facts
from resume_agent.services.run_store import read_yaml
from resume_agent.services.workflow_service import WorkflowService


TEMPLATES = Jinja2Templates(directory=PROJECT_ROOT / "agent" / "templates")


def _localized(value):
    if isinstance(value, dict):
        return value.get("zh") or value.get("en") or ""
    return str(value or "")


def _path_label(resume: dict, path: str) -> str:
    parts = path.strip("/").split("/")
    if len(parts) < 2:
        return path
    section = next((item for item in resume["sections"] if item.get("id") == parts[1]), None)
    if not section:
        return path
    labels = [_localized(section.get("title"))]
    if "rows" in parts:
        index = parts.index("rows")
        if len(parts) > index + 1:
            row = next((item for item in section.get("rows", []) if item.get("id") == parts[index + 1]), None)
            if row:
                labels.append(_localized(row.get("label")))
    if "entries" in parts:
        index = parts.index("entries")
        if len(parts) > index + 1:
            entry = next((item for item in section.get("entries", []) if item.get("id") == parts[index + 1]), None)
            if entry:
                labels.append(_localized(entry.get("title") or entry.get("org")))
                for collection in ("items", "responsibilities"):
                    if collection in parts and parts[-1] != collection:
                        item = next((value for value in entry.get(collection, []) if value.get("id") == parts[-1]), None)
                        if item:
                            labels.append(_localized(item)[:42] + "…")
            if parts[-1] == "summary":
                labels.append("项目简介")
    if parts[-1] == "body":
        labels.append("正文")
    return " › ".join(filter(None, labels))


def _split_keywords(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,，\n]", value) if item.strip()]


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jd_label: str = Field(min_length=1, max_length=120)
    job_description: str = Field(min_length=20, max_length=100_000)


@lru_cache
def default_service() -> WorkflowService:
    settings = get_settings()
    configure_logging(settings)
    return WorkflowService(OpenAICompatibleProvider(settings), settings)


async def get_workflow() -> WorkflowService:
    return default_service()


ServiceDep = Annotated[WorkflowService, Depends(get_workflow)]


def create_app(service_factory: Callable[[], WorkflowService] | None = None) -> FastAPI:
    app = FastAPI(title="AI Resume Compiler", version="1.1")
    if service_factory is not None:
        async def override_workflow() -> WorkflowService:
            return service_factory()

        app.dependency_overrides[get_workflow] = override_workflow

    @app.exception_handler(ResumeAgentError)
    async def resume_error(_: Request, exc: ResumeAgentError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def launch(target, run_id: str) -> None:
        Thread(target=target, args=(run_id,), daemon=True, name=f"resume-{run_id}").start()

    @app.post("/api/v1/resume/runs", status_code=202)
    async def create_run(payload: CreateRunRequest, workflow: ServiceDep):
        metadata = workflow.create(payload.jd_label, payload.job_description)
        launch(workflow.analyze, metadata["run_id"])
        return metadata

    @app.get("/api/v1/resume/runs/{run_id}")
    async def get_run(run_id: str, workflow: ServiceDep):
        return workflow.get(run_id)

    @app.post("/api/v1/resume/runs/{run_id}/retry", status_code=202)
    async def retry_run(run_id: str, workflow: ServiceDep):
        metadata = workflow.retry_analysis(run_id)
        launch(workflow.analyze, run_id)
        return metadata

    @app.post("/api/v1/resume/runs/{run_id}/approve-strategy", status_code=202)
    async def approve_strategy(
        run_id: str, decision: StrategyDecision, workflow: ServiceDep
    ):
        metadata = workflow.approve_strategy(run_id, decision.strategy)
        launch(workflow.compile, run_id)
        return metadata

    @app.post("/api/v1/resume/runs/{run_id}/revise-strategy")
    async def revise_strategy(run_id: str, strategy: RewriteStrategy, workflow: ServiceDep):
        return workflow.revise_strategy(run_id, strategy)

    @app.post("/api/v1/resume/runs/{run_id}/manual-edit")
    async def manual_edit(run_id: str, request: ManualEditRequest, workflow: ServiceDep):
        return workflow.manual_edit(run_id, request.patch)

    @app.post("/api/v1/resume/runs/{run_id}/approve-final")
    async def approve_final(run_id: str, workflow: ServiceDep):
        return workflow.approve_final(run_id)

    @app.post("/api/v1/resume/runs/{run_id}/reject-final")
    async def reject_final(run_id: str, workflow: ServiceDep):
        return workflow.reject_final(run_id)

    @app.post("/api/v1/resume/runs/{run_id}/restore-original")
    async def restore_original(run_id: str, workflow: ServiceDep):
        return workflow.restore_original(run_id)

    @app.get("/api/v1/resume/runs/{run_id}/diff")
    async def get_diff(run_id: str, workflow: ServiceDep):
        return workflow.get_diff(run_id)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request, workflow: ServiceDep):
        return TEMPLATES.TemplateResponse(
            request=request, name="index.html", context={"runs": workflow.list_runs()}
        )

    @app.post("/ui/runs")
    async def ui_create(
        workflow: ServiceDep,
        jd_label: Annotated[str, Form()],
        job_description: Annotated[str, Form()],
    ):
        metadata = workflow.create(jd_label, job_description)
        launch(workflow.analyze, metadata["run_id"])
        return RedirectResponse(f"/runs/{metadata['run_id']}/view", status_code=303)

    @app.get("/runs/{run_id}/view", response_class=HTMLResponse)
    async def run_view(request: Request, run_id: str, workflow: ServiceDep):
        metadata = workflow.get(run_id)
        run_dir = workflow.resolve_run(run_id)
        raw_artifacts = {}
        parsed_artifacts = {}
        for name in ("rewrite_strategy", "validation", "hiring_review", "final_diff", "error"):
            path = run_dir / f"{name}.json"
            if path.exists() and (name != "error" or metadata["status"] in {"FAILED", "INTERRUPTED"}):
                parsed_artifacts[name] = read_json(run_dir, path.name)
                raw_artifacts[name] = json.dumps(parsed_artifacts[name], ensure_ascii=False, indent=2)
        resume = read_yaml(run_dir, "input_resume.yaml")
        facts = collect_facts(resume)
        strategy_view = None
        if "rewrite_strategy" in parsed_artifacts:
            strategy_view = parsed_artifacts["rewrite_strategy"]
            for index, action in enumerate(strategy_view["actions"]):
                action["index"] = index
                action["target_label"] = _path_label(resume, action["target_path"])
                action["evidence"] = [
                    _localized(facts[fact_id]["statement"])
                    for fact_id in action["supported_by"]
                    if fact_id in facts
                ]
        diff_view = []
        for item in parsed_artifacts.get("final_diff", []):
            view = dict(item)
            view["target_label"] = _path_label(resume, item["path"])
            view["original_text"] = _localized(item.get("original")) or "（无）"
            view["revised_text"] = _localized(item.get("revised")) or "（已隐藏）"
            view["evidence"] = [
                _localized(facts[fact_id]["statement"])
                for fact_id in item.get("supported_by", [])
                if fact_id in facts
            ]
            diff_view.append(view)
        return TEMPLATES.TemplateResponse(
            request=request,
            name="run.html",
            context={
                "run": metadata,
                "artifacts": raw_artifacts,
                "strategy": strategy_view,
                "validation": parsed_artifacts.get("validation"),
                "hiring": parsed_artifacts.get("hiring_review"),
                "diff": diff_view,
                "error": parsed_artifacts.get("error"),
            },
        )

    @app.post("/ui/runs/{run_id}/approve-strategy")
    async def ui_approve_strategy(run_id: str, workflow: ServiceDep):
        workflow.approve_strategy(run_id)
        launch(workflow.compile, run_id)
        return RedirectResponse(f"/runs/{run_id}/view", status_code=303)

    @app.post("/ui/runs/{run_id}/retry")
    async def ui_retry(run_id: str, workflow: ServiceDep):
        workflow.retry_analysis(run_id)
        launch(workflow.analyze, run_id)
        return RedirectResponse(f"/runs/{run_id}/view", status_code=303)

    @app.post("/ui/runs/{run_id}/revise-strategy")
    async def ui_revise_strategy(
        request: Request,
        run_id: str,
        workflow: ServiceDep,
    ):
        try:
            form = await request.form()
            original = RewriteStrategy.model_validate(
                read_json(workflow.resolve_run(run_id), "rewrite_strategy.json")
            )
            actions = []
            for index, action in enumerate(original.actions):
                if f"keep_{index}" not in form:
                    continue
                payload = action.model_dump()
                payload["priority"] = int(str(form.get(f"priority_{index}", action.priority)))
                payload["instruction"] = str(
                    form.get(f"instruction_{index}", action.instruction)
                ).strip()
                actions.append(payload)
            strategy = RewriteStrategy.model_validate(
                {
                    "positioning": str(form.get("positioning", original.positioning)).strip(),
                    "safe_keywords": _split_keywords(str(form.get("safe_keywords", ""))),
                    "forbidden_keywords": _split_keywords(str(form.get("forbidden_keywords", ""))),
                    "actions": actions,
                }
            )
        except Exception as exc:
            raise ResumeAgentError(f"策略表单无效：{exc}") from exc
        workflow.revise_strategy(run_id, strategy)
        return RedirectResponse(f"/runs/{run_id}/view", status_code=303)

    @app.post("/ui/runs/{run_id}/approve-final")
    async def ui_approve_final(run_id: str, workflow: ServiceDep):
        workflow.approve_final(run_id)
        return RedirectResponse(f"/runs/{run_id}/view", status_code=303)

    @app.post("/ui/runs/{run_id}/manual-edit")
    async def ui_manual_edit(
        run_id: str,
        workflow: ServiceDep,
        patch_json: Annotated[str, Form()],
    ):
        try:
            patch = ResumePatch.model_validate_json(patch_json)
        except Exception as exc:
            raise ResumeAgentError(f"Patch JSON 无效：{exc}") from exc
        workflow.manual_edit(run_id, patch)
        return RedirectResponse(f"/runs/{run_id}/view", status_code=303)

    @app.post("/ui/runs/{run_id}/reject-final")
    async def ui_reject_final(run_id: str, workflow: ServiceDep):
        workflow.reject_final(run_id)
        return RedirectResponse(f"/runs/{run_id}/view", status_code=303)

    @app.post("/ui/runs/{run_id}/restore-original")
    async def ui_restore_original(run_id: str, workflow: ServiceDep):
        workflow.restore_original(run_id)
        return RedirectResponse(f"/runs/{run_id}/view", status_code=303)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("resume_agent.api.main:app", host="127.0.0.1", port=8010, reload=False)
