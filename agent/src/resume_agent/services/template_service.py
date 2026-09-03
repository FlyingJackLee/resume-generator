from __future__ import annotations

import json
import io
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

from resume_agent.errors import ResumeAgentError
from resume_agent.paths import PROJECT_ROOT, TEMPLATES_ROOT

BASE_CSS = (PROJECT_ROOT / "web" / "styles" / "awesome-cv.css").read_text(encoding="utf-8")
BUILTINS = {
    "classic": {"name": "经典简历", "description": "当前 Awesome CV 风格", "theme": ""},
    "minimal": {"name": "现代极简", "description": "克制留白与蓝色强调", "theme": """
:root { --awesome:#2563eb; --rule:#dbe3ee; --text:#263341; } .header { text-align:left; border-bottom:2px solid var(--awesome); padding-bottom:12px; } .header .contacts { justify-content:flex-start; margin-left:0; } .section-title::after { display:none; } .section-title { font-size:12.5pt; text-transform:uppercase; letter-spacing:.06em; } .entry { margin-bottom:12px; } .photo { border-radius:50% !important; }
"""},
    "sidebar": {"name": "专业侧栏", "description": "深色个人信息区与高对比内容", "theme": """
:root { --awesome:#0f766e; --text:#263238; --darktext:#102a43; } .page { border-left:1.9cm solid #123047; padding-left:1cm; position:relative; } .header { text-align:left; } .header .name .first,.header .name .last { color:#123047; } .header .contacts { justify-content:flex-start; margin-left:0; } .section-title { color:#0f766e; font-size:13pt; } .section-title::after { background:#0f766e; } .photo { left:-2.65cm; right:auto !important; border-radius:50% !important; width:1.55cm !important; height:1.55cm !important; }
"""},
}
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,48}$")
HIDE_RULES = {
    "照片": ".header .photo",
    "联系方式 / 社交链接": ".header .contacts",
    "个人介绍": ".section:has(.paragraph)",
    "技能": ".section:has(.skills)",
    "教育": ".section.edu",
    "项目简介": ".entry-summary",
    "项目职责": ".responsibilities-title, .entry:has(.responsibilities-title) .entry-items",
    "链接": ".entry-link",
}


class TemplateService:
    def __init__(self, root: Path = TEMPLATES_ROOT):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def settings_path(self) -> Path:
        return self.root / "active.json"

    def active_id(self) -> str:
        if not self.settings_path.exists():
            return "classic"
        return json.loads(self.settings_path.read_text(encoding="utf-8")).get("template_id", "classic")

    def set_active(self, template_id: str) -> dict[str, Any]:
        template = self.get(template_id)
        self.settings_path.write_text(json.dumps({"template_id": template_id}, ensure_ascii=False), encoding="utf-8")
        return template

    def get(self, template_id: str) -> dict[str, Any]:
        if template_id in BUILTINS:
            return {"id": template_id, "builtin": True, "unsupported": [], **BUILTINS[template_id]}
        manifest = self.root / template_id / "manifest.json"
        if not manifest.exists():
            raise ResumeAgentError("模板不存在")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return {"id": template_id, "builtin": False, "unsupported": [], "name": template_id, "description": "自定义样式", **data}

    def list(self) -> list[dict[str, Any]]:
        templates = [self.get(template_id) for template_id in BUILTINS]
        for directory in self.root.iterdir():
            if directory.is_dir() and (directory / "manifest.json").exists():
                templates.append(self.get(directory.name))
        active = self.active_id()
        return [{**template, "active": template["id"] == active} for template in templates]

    def css(self, template_id: str | None = None, asset_prefix: str | None = None) -> str:
        template = self.get(template_id or self.active_id())
        if template["builtin"]:
            theme = template.get("theme", "")
        else:
            theme = (self.root / template["id"] / "theme.css").read_text(encoding="utf-8")
            if asset_prefix:
                theme = re.sub(
                    r"url\((['\"]?)assets/([^)'\"\s]+)\1\)",
                    lambda match: f"url('{asset_prefix}{template['id']}/assets/{match.group(2)}')",
                    theme,
                )
        hidden = "\n".join(f"{HIDE_RULES[item]} {{ display:none !important; }}" for item in template.get("unsupported", []) if item in HIDE_RULES)
        return BASE_CSS + "\n" + theme + "\n" + hidden

    def import_zip(self, archive: Path) -> dict[str, Any]:
        with zipfile.ZipFile(archive) as package:
            names = package.namelist()
            if "manifest.json" not in names or "theme.css" not in names:
                raise ResumeAgentError("模板包必须包含 manifest.json 和 theme.css")
            if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
                raise ResumeAgentError("模板包包含不安全路径")
            manifest = json.loads(package.read("manifest.json"))
            template_id = str(manifest.get("id", ""))
            if not SAFE_ID.fullmatch(template_id) or template_id in BUILTINS:
                raise ResumeAgentError("模板 ID 无效或与内置模板冲突")
            css = package.read("theme.css").decode("utf-8")
            if "@import" in css.lower() or re.search(r"url\(\s*['\"]?https?://", css, re.I):
                raise ResumeAgentError("模板不允许远程资源或 @import")
            target = self.root / template_id
            if target.exists():
                raise ResumeAgentError("已有相同 ID 的模板")
            target.mkdir()
            package.extractall(target)
        return self.get(template_id)

    def delete(self, template_id: str) -> None:
        if template_id in BUILTINS:
            raise ResumeAgentError("内置模板不可删除")
        if template_id == self.active_id():
            raise ResumeAgentError("请先切换到其他模板")
        target = self.root / template_id
        if not target.is_dir():
            raise ResumeAgentError("模板不存在")
        shutil.rmtree(target)

    def rename(self, template_id: str, name: str) -> dict[str, Any]:
        if template_id in BUILTINS:
            raise ResumeAgentError("内置模板不可重命名")
        template = self.get(template_id)
        manifest_path = self.root / template_id / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["name"] = name.strip()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.get(template_id)

    def copy(self, source_id: str, target_id: str, name: str) -> dict[str, Any]:
        if not SAFE_ID.fullmatch(target_id) or target_id in BUILTINS or (self.root / target_id).exists():
            raise ResumeAgentError("新模板 ID 无效或已存在")
        source = self.get(source_id)
        target = self.root / target_id
        target.mkdir()
        if source["builtin"]:
            (target / "theme.css").write_text(source.get("theme", ""), encoding="utf-8")
            manifest = {"id": target_id, "name": name, "description": f"从 {source['name']} 复制", "unsupported": []}
        else:
            shutil.copytree(self.root / source_id, target, dirs_exist_ok=True)
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            manifest.update({"id": target_id, "name": name})
        (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.get(target_id)

    def export_zip(self, template_id: str) -> bytes:
        template = self.get(template_id)
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED) as package:
            if template["builtin"]:
                manifest = {"id": template_id, "name": template["name"], "description": template["description"], "unsupported": []}
                package.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                package.writestr("theme.css", template.get("theme", ""))
            else:
                root = self.root / template_id
                for file in root.rglob("*"):
                    if file.is_file():
                        package.write(file, file.relative_to(root).as_posix())
        return payload.getvalue()
