import pytest

from resume_agent.errors import ResumeAgentError
from resume_agent.services import resume_import
from resume_agent.services.resume_import import extract_local_ocr, extract_mineru_api, has_meaningful_resume_text, normalize_resume, source_language_hint


def test_single_language_import_never_fills_the_missing_translation():
    source = {
        "meta": {"name": {"zh": "张三", "en": "Zhang San"}, "position": {"zh": "工程师", "en": "Engineer"}},
        "sections": [{"type": "paragraph", "title": {"zh": "简介", "en": "Introduction"}, "body": {"zh": "负责平台开发", "en": "Built the platform"}}],
    }
    result = normalize_resume(source, ["zh"])
    assert result["meta"]["name"] == {"zh": "张三", "en": ""}
    assert result["sections"][0]["body"] == {"zh": "负责平台开发", "en": ""}


def test_import_normalizes_a_single_bullet_object_to_an_array():
    source = {
        "meta": {},
        "sections": [{
            "type": "entries", "title": {"zh": "项目", "en": "Projects"},
            "entries": [{"title": {"zh": "项目 A", "en": "Project A"}, "responsibilities": {"zh": "负责交付", "en": "Delivered"}}],
        }],
    }
    result = normalize_resume(source, ["zh", "en"])
    assert result["sections"][0]["entries"][0]["responsibilities"] == [{"zh": "负责交付", "en": "Delivered"}]


def test_language_hint_is_conservative_for_chinese_english_and_mixed_sources():
    assert source_language_hint("负责 FastAPI 服务开发") is None
    assert source_language_hint("Built reliable services") == ["en"]
    assert source_language_hint("负责平台开发") == ["zh"]


def test_only_meaningful_text_may_be_sent_to_the_resume_llm():
    assert not has_meaningful_resume_text("Confidential\n1\n2\n")
    assert not has_meaningful_resume_text("\ufffd" * 80)
    assert has_meaningful_resume_text("张三，负责企业级智能体平台的研发、上线与持续优化。" * 4)


def test_local_ocr_uses_embedded_rapidocr_and_reads_text(monkeypatch):
    class FakeEngine:
        def __call__(self, image_bytes):
            assert image_bytes == b"image-bytes"
            return type("Result", (), {"txts": ("识别出的简历文字，负责企业级平台的研发、交付、上线和持续优化。" * 3,)})()

    monkeypatch.setattr(resume_import, "_ocr_engine", lambda: FakeEngine())
    result = extract_local_ocr("resume.png", b"image-bytes", max_pages=5)

    assert result.startswith("识别出的简历文字")


def test_mineru_api_requires_an_explicit_token():
    with pytest.raises(ResumeAgentError, match="MINERU_API_TOKEN"):
        extract_mineru_api(
            "resume.pdf", b"pdf", base_url="https://mineru.net/api/v4", token="",
            model_version="vlm", timeout_seconds=30,
        )
