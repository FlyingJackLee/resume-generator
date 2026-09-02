from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from resume_agent.errors import ResumeAgentError
from resume_agent.paths import RUNS_ROOT


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^\w]+", "_", value.casefold(), flags=re.UNICODE).strip("_")
    if not slug:
        raise ResumeAgentError("JD 标识必须包含英文字母或数字")
    return slug[:80]


def create_run(
    jd_label: str,
    jd: str,
    master_bytes: bytes,
    root: Path = RUNS_ROOT,
    company: str | None = None,
) -> Path:
    if not jd.strip():
        raise ResumeAgentError("JD 文本不能为空")
    run_id = f"run_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "jd.txt").write_text(jd.strip() + "\n", encoding="utf-8")
    metadata = {
        "run_id": run_id,
        "jd_label": jd_label,
        "company": company or None,
        "notes": "",
        "output_name": f"{safe_slug(jd_label)}_resume.yaml",
        "master_sha256": hashlib.sha256(master_bytes).hexdigest(),
        "created_at": datetime.now(UTC).isoformat(),
        "status": "INIT",
    }
    (run_dir / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    append_event(run_dir, **metadata)
    return run_dir


def write_target(run_dir: Path, filename: str, resume: dict[str, Any]) -> Path:
    target = run_dir / filename
    if target.parent != run_dir or target.suffix != ".yaml":
        raise ResumeAgentError("输出文件名不安全")
    target.write_text(
        yaml.safe_dump(resume, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return target


def read_metadata(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


def append_event(run_dir: Path, **fields: Any) -> None:
    event = {"timestamp": datetime.now(UTC).isoformat(), **fields}
    with (run_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events(run_dir: Path) -> list[dict[str, Any]]:
    events_path = run_dir / "events.jsonl"
    if not events_path.exists():
        return []
    lines = events_path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def update_metadata(run_dir: Path, **changes: Any) -> dict[str, Any]:
    metadata = read_metadata(run_dir)
    metadata.update(changes)
    metadata["updated_at"] = datetime.now(UTC).isoformat()
    temporary = run_dir / "run.json.tmp"
    temporary.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(run_dir / "run.json")
    append_event(run_dir, **{**changes, "run_id": metadata["run_id"]})
    return metadata


def write_json(run_dir: Path, filename: str, value: Any) -> Path:
    if Path(filename).name != filename or not filename.endswith(".json"):
        raise ResumeAgentError("JSON 产物文件名不安全")
    target = run_dir / filename
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def read_json(run_dir: Path, filename: str) -> Any:
    return json.loads((run_dir / filename).read_text(encoding="utf-8"))


def write_yaml(run_dir: Path, filename: str, value: Any) -> Path:
    if Path(filename).name != filename or not filename.endswith(".yaml"):
        raise ResumeAgentError("YAML 产物文件名不安全")
    target = run_dir / filename
    target.write_text(
        yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8"
    )
    return target


def read_yaml(run_dir: Path, filename: str) -> Any:
    return yaml.safe_load((run_dir / filename).read_text(encoding="utf-8"))
