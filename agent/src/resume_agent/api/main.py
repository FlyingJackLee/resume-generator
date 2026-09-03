from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from threading import Thread
from typing import Annotated, Callable

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from resume_agent.config import get_settings
from resume_agent.errors import ResumeAgentError
from resume_agent.logging_config import configure_logging
from resume_agent.models import ManualEditRequest, RewriteStrategy, StrategyDecision
from resume_agent.providers import OpenAICompatibleProvider
from resume_agent.services.catalog import editable_catalog
from resume_agent.services.master_resume import collect_facts
from resume_agent.services.preview_service import render_master_preview, render_run_preview
from resume_agent.services.resume_labels import path_label as _path_label
from resume_agent.services.run_store import read_json, read_yaml
from resume_agent.services.workflow_service import WorkflowService


logger = logging.getLogger(__name__)

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

AUTO_APPROVE_POLL_SECONDS = 30

TERMINAL_STATUSES = {"COMPLETED", "FAILED", "INTERRUPTED", "REJECTED"}

ARTIFACT_FILES = {
    "job_profile": "job_profile.json",
    "match_report": "match_report.json",
    "hr_review": "hr_review.json",
    "rewrite_strategy": "rewrite_strategy.json",
    "validation": "validation.json",
    "hiring_review": "hiring_review.json",
    "final_diff": "final_diff.json",
    "error": "error.json",
}


class CreateRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jd_label: str = Field(min_length=1, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    job_description: str = Field(min_length=20, max_length=100_000)


class NotesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    notes: str = Field(default="", max_length=20_000)


class EditorDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(default="在线编辑草稿", min_length=1, max_length=120)


class EditorDraftUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resume: dict


class EditorConflictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str


class EditorPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(default="发布版本", min_length=1, max_length=200)


@lru_cache
def default_service() -> WorkflowService:
    settings = get_settings()
    configure_logging(settings)
    return WorkflowService(OpenAICompatibleProvider(settings), settings)


async def get_workflow() -> WorkflowService:
    return default_service()


ServiceDep = Annotated[WorkflowService, Depends(get_workflow)]


def create_app(service_factory: Callable[[], WorkflowService] | None = None) -> FastAPI:
    def launch(target, run_id: str) -> None:
        Thread(target=target, args=(run_id,), daemon=True, name=f"resume-{run_id}").start()

    def current_workflow() -> WorkflowService:
        return service_factory() if service_factory is not None else default_service()

    async def auto_approve_loop() -> None:
        while True:
            await asyncio.sleep(AUTO_APPROVE_POLL_SECONDS)
            try:
                workflow = current_workflow()
                for run_id in workflow.auto_approve_timed_out_gates():
                    launch(workflow.compile, run_id)
            except Exception:
                logger.exception("auto-approve scheduler tick failed")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = asyncio.create_task(auto_approve_loop())
        try:
            yield
        finally:
            task.cancel()

    app = FastAPI(title="AI Resume Compiler", version="1.1", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if service_factory is not None:
        async def override_workflow() -> WorkflowService:
            return service_factory()

        app.dependency_overrides[get_workflow] = override_workflow

    @app.exception_handler(ResumeAgentError)
    async def resume_error(_: Request, exc: ResumeAgentError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.post("/api/v1/resume/runs", status_code=202)
    async def create_run(payload: CreateRunRequest, workflow: ServiceDep):
        metadata = workflow.create(payload.jd_label, payload.job_description, payload.company)
        launch(workflow.analyze, metadata["run_id"])
        return metadata

    @app.post("/api/v1/resume/editor-drafts", status_code=201)
    async def create_editor_draft(payload: EditorDraftRequest, workflow: ServiceDep):
        return workflow.get_or_create_editor_draft(payload.label)

    @app.get("/api/v1/resume/editor-drafts/{run_id}")
    async def get_editor_draft(run_id: str, workflow: ServiceDep):
        return workflow.get_editor_draft(run_id)

    @app.put("/api/v1/resume/editor-drafts/{run_id}")
    async def update_editor_draft(
        run_id: str, payload: EditorDraftUpdateRequest, workflow: ServiceDep
    ):
        return workflow.update_editor_draft(run_id, payload.resume)

    @app.get("/api/v1/resume/editor-drafts/{run_id}/versions")
    async def editor_versions(run_id: str, workflow: ServiceDep):
        return workflow.editor_versions(run_id)

    @app.get("/api/v1/resume/editor-drafts/{run_id}/external-change")
    async def editor_external_change(run_id: str, workflow: ServiceDep):
        return workflow.editor_external_change(run_id)

    @app.post("/api/v1/resume/editor-drafts/{run_id}/external-change")
    async def resolve_editor_external_change(
        run_id: str, payload: EditorConflictRequest, workflow: ServiceDep
    ):
        return workflow.resolve_editor_external_change(run_id, payload.action)

    @app.post("/api/v1/resume/editor-drafts/{run_id}/publish")
    async def publish_editor_draft(
        run_id: str, payload: EditorPublishRequest, workflow: ServiceDep
    ):
        return workflow.publish_editor_draft(run_id, payload.message)

    @app.post("/api/v1/resume/editor-drafts/{run_id}/rollback/{version_id}")
    async def rollback_editor_version(run_id: str, version_id: str, workflow: ServiceDep):
        return workflow.rollback_editor_version(run_id, version_id)

    @app.get("/api/v1/resume/editor-drafts/{run_id}/download/{format}/{lang}")
    async def download_editor_draft(run_id: str, format: str, lang: str, workflow: ServiceDep):
        if format not in {"html", "pdf"} or lang not in {"zh", "en"}:
            raise ResumeAgentError("仅支持下载中文或英文的 HTML / PDF")
        run_dir = workflow.resolve_run(run_id)
        resume = workflow.get_editor_draft(run_id)
        from resume_agent.services.preview_service import _render
        html_path = run_dir / f"resume.{lang}.html"
        html_path.write_text(_render(run_dir / "editor_resume.yaml", lang), encoding="utf-8")
        if format == "html":
            return FileResponse(html_path, filename=f"resume.{lang}.html", media_type="text/html")
        from resume_render import localize
        from build import export_pdf
        pdf_path = run_dir / f"resume.{lang}.pdf"
        export_pdf(html_path, pdf_path, localize(resume["meta"]["footer_label"], lang))
        return FileResponse(pdf_path, filename=f"resume.{lang}.pdf", media_type="application/pdf")

    @app.get("/api/v1/resume/runs")
    async def list_runs(workflow: ServiceDep, page: int = 1, page_size: int = 20):
        return workflow.list_runs(page=page, page_size=page_size)

    @app.get("/api/v1/resume/runs/{run_id}")
    async def get_run(run_id: str, workflow: ServiceDep):
        return workflow.get(run_id)

    @app.get("/api/v1/resume/runs/{run_id}/events")
    async def get_run_events(run_id: str, workflow: ServiceDep):
        return workflow.get_events(run_id)

    @app.get("/api/v1/resume/runs/{run_id}/artifacts")
    async def get_run_artifacts(run_id: str, workflow: ServiceDep):
        run_dir = workflow.resolve_run(run_id)
        return {
            key: read_json(run_dir, filename) if (run_dir / filename).exists() else None
            for key, filename in ARTIFACT_FILES.items()
        }

    @app.get("/api/v1/resume/runs/{run_id}/stream")
    async def stream_run(run_id: str, request: Request, workflow: ServiceDep):
        workflow.resolve_run(run_id)  # validates run_id and raises if unknown/unsafe

        async def event_source():
            seen = 0
            idle_seconds = 0.0
            while True:
                if await request.is_disconnected():
                    return
                events = workflow.get_events(run_id)
                if len(events) > seen:
                    for event in events[seen:]:
                        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    seen = len(events)
                    idle_seconds = 0.0
                if events and str(events[-1].get("status", "")) in TERMINAL_STATUSES:
                    return
                # Human Gate waits can sit idle for many minutes with nothing new to
                # send; without a periodic ping, browsers/proxies silently drop the
                # connection and the frontend never learns the gate was resolved.
                if idle_seconds >= 15.0:
                    yield ": keep-alive\n\n"
                    idle_seconds = 0.0
                await asyncio.sleep(0.4)
                idle_seconds += 0.4

        return StreamingResponse(event_source(), media_type="text/event-stream")

    @app.get("/api/v1/resume/runs/{run_id}/structure")
    async def get_run_structure(run_id: str, workflow: ServiceDep, source: str = "input"):
        run_dir = workflow.resolve_run(run_id)
        if source == "candidate":
            if not (run_dir / "candidate_resume.yaml").exists():
                raise ResumeAgentError("这个 run 还没有候选简历，无法按候选版本取结构")
            resume = read_yaml(run_dir, "candidate_resume.yaml")
        elif source == "input":
            resume = read_yaml(run_dir, "input_resume.yaml")
        else:
            raise ResumeAgentError("source 必须是 input 或 candidate")
        catalog = editable_catalog(resume)
        for item in catalog:
            item["label"] = _path_label(resume, item["path"])
        return catalog

    @app.get("/api/v1/resume/runs/{run_id}/facts")
    async def get_run_facts(run_id: str, workflow: ServiceDep):
        run_dir = workflow.resolve_run(run_id)
        resume = read_yaml(run_dir, "input_resume.yaml")
        return collect_facts(resume)

    @app.post("/api/v1/resume/runs/{run_id}/notes")
    async def set_run_notes(run_id: str, payload: NotesRequest, workflow: ServiceDep):
        return workflow.update_notes(run_id, payload.notes)

    @app.get("/preview/{token}", response_class=HTMLResponse)
    async def preview(token: str, workflow: ServiceDep, lang: str = "zh"):
        if token == "master":
            return render_master_preview(lang)
        run_dir = workflow.resolve_run(token)
        metadata = workflow.get(token)
        return render_run_preview(run_dir, metadata, lang)

    @app.post("/api/v1/resume/runs/{run_id}/retry", status_code=202)
    async def retry_run(run_id: str, workflow: ServiceDep):
        metadata = workflow.retry_analysis(run_id)
        if metadata["status"] == "EDITING":
            launch(workflow.compile, run_id)
        else:
            launch(workflow.analyze, run_id)
        return metadata

    @app.post("/api/v1/resume/runs/{run_id}/retry-validation", status_code=202)
    async def retry_validation(run_id: str, workflow: ServiceDep):
        metadata = workflow.retry_validation(run_id)
        launch(workflow.validate_and_review, run_id)
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

    @app.get("/")
    async def root():
        return {"message": "API only — SPA dev server: cd agent/frontend && pnpm dev"}

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("resume_agent.api.main:app", host="127.0.0.1", port=8010, reload=False)
