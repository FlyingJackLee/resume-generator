from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from resume_agent.errors import ResumeAgentError
from resume_agent.paths import MASTER_RESUME_PATH, PROJECT_ROOT

_WEB_DIR = PROJECT_ROOT / "web"
if str(_WEB_DIR) not in sys.path:
    sys.path.insert(0, str(_WEB_DIR))

from resume_render import load_data, render_html  # noqa: E402


def _render(path: Path, lang: str) -> str:
    if lang not in ("zh", "en"):
        raise ResumeAgentError("lang 必须是 zh 或 en")
    return render_html(load_data(path=path), lang)


def render_master_preview(lang: str, master_path: Path = MASTER_RESUME_PATH) -> str:
    return _render(master_path, lang)


def render_run_preview(run_dir: Path, metadata: dict[str, Any], lang: str) -> str:
    if metadata.get("editor_draft"):
        draft_path = run_dir / "editor_resume.yaml"
        if draft_path.exists():
            return _render(draft_path, lang)
    target_name = metadata.get("target_file")
    if target_name and (run_dir / target_name).exists():
        return _render(run_dir / target_name, lang)
    candidate_path = run_dir / "candidate_resume.yaml"
    if candidate_path.exists():
        return _render(candidate_path, lang)
    raise ResumeAgentError("这个 run 还没有可预览的简历内容")
