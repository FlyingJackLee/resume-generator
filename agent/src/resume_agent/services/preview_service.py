from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from resume_agent.errors import ResumeAgentError
from resume_agent.paths import MASTER_RESUME_PATH, PROJECT_ROOT, TEMPLATES_ROOT
from resume_agent.services.template_service import TemplateService

_WEB_DIR = PROJECT_ROOT / "web"
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

from resume_render import load_data, render_html  # noqa: E402


def _render(path: Path, lang: str, show_page_guides: bool = False, for_file_export: bool = False) -> str:
    """渲染预览/导出 HTML。

    for_file_export=True 用于下载端点：HTML 会被 Chromium 以 file:// 打开导出
    PDF，而基础样式的字体与模板资源是相对/HTTP 路径，在 agent/data 下的落盘
    位置解析不到，导致 PDF 静默回退到系统字体。该模式把这些引用改为绝对
    file:// URL，保证导出 PDF 与预览使用同一套 webfont（分页位置才一致）。
    """
    if lang not in ("zh", "en"):
        raise ResumeAgentError("lang 必须是 zh 或 en")
    if for_file_export:
        css_override = TemplateService().css(
            asset_prefix=f"{TEMPLATES_ROOT.as_uri()}",
            base_asset_url=(PROJECT_ROOT / "web" / "assets").as_uri(),
        )
        photo_base = (PROJECT_ROOT / "web").as_uri()
    else:
        css_override = TemplateService().css(asset_prefix="/api/v1/resume/template-assets/")
        photo_base = ".."
    return render_html(
        load_data(path=path), lang,
        css_override=css_override,
        show_language_toggle=False,
        show_page_guides=show_page_guides,
        photo_base=photo_base,
    )


def render_master_preview(
    lang: str, master_path: Path = MASTER_RESUME_PATH, show_page_guides: bool = False
) -> str:
    return _render(master_path, lang, show_page_guides=show_page_guides)


def resolve_run_preview_source(run_dir: Path, metadata: dict[str, Any]) -> Path:
    """Which YAML file currently represents this run's preview-able resume."""
    if metadata.get("editor_draft"):
        draft_path = run_dir / "editor_resume.yaml"
        if draft_path.exists():
            return draft_path
    target_name = metadata.get("target_file")
    if target_name and (run_dir / target_name).exists():
        return run_dir / target_name
    candidate_path = run_dir / "candidate_resume.yaml"
    if candidate_path.exists():
        return candidate_path
    raise ResumeAgentError("这个 run 还没有可预览的简历内容")


def render_run_preview(
    run_dir: Path, metadata: dict[str, Any], lang: str, show_page_guides: bool = False
) -> str:
    return _render(resolve_run_preview_source(run_dir, metadata), lang, show_page_guides=show_page_guides)
