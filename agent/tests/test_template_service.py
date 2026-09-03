import json
import zipfile

from resume_agent.services.template_service import TemplateService


def test_templates_are_global_and_apply_declared_hidden_fields(tmp_path):
    service = TemplateService(tmp_path)
    assert service.active_id() == "classic"
    service.set_active("minimal")
    assert service.active_id() == "minimal"
    assert "#2563eb" in service.css()

    archive = tmp_path / "custom.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("manifest.json", json.dumps({
            "id": "compact", "name": "紧凑模板", "description": "test", "unsupported": ["照片"]
        }))
        package.writestr("theme.css", ".header { color: red; }")
    service.import_zip(archive)
    service.set_active("compact")
    assert ".header .photo { display:none !important; }" in service.css()


def test_template_import_rejects_remote_css(tmp_path):
    service = TemplateService(tmp_path)
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("manifest.json", json.dumps({"id": "unsafe", "name": "Unsafe"}))
        package.writestr("theme.css", "@import url('https://example.com/style.css');")
    try:
        service.import_zip(archive)
    except Exception as exc:
        assert "远程资源" in str(exc)
    else:
        raise AssertionError("unsafe template was imported")
