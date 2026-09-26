"""下载端点的 file:// 导出渲染契约。

导出 HTML 会被 Chromium 以 file:// 打开生成 PDF；基础样式的字体是
`url("../assets/...)` 相对路径，只有写在 web/ 下一级目录时才解析得到。
下载端点把 HTML 写进 agent/data/ 下的 run/master_export 目录，相对路径
解析不到，PDF 会静默回退到系统字体，与预览的分页/字体不一致——分页线
（page guides）随之失真。这里锁定 for_file_export 渲染必须输出绝对
file:// 字体 URL。
"""
import yaml

from resume_agent.paths import MASTER_RESUME_SAMPLE_PATH, PROJECT_ROOT
from resume_agent.services.preview_service import _render


def test_file_export_render_uses_absolute_file_font_urls():
    html = _render(MASTER_RESUME_SAMPLE_PATH, "en", for_file_export=True)
    fonts_uri = (PROJECT_ROOT / "web" / "assets").as_uri()
    assert f'url("{fonts_uri}/fonts/Roboto-Regular.ttf")' in html
    assert "../assets/fonts/" not in html  # 相对字体路径不得残留在导出产物里
    assert "page-guides.js" not in html  # 导出产物不带预览分页线脚本


def test_file_export_render_rewrites_misans_urls():
    html = _render(MASTER_RESUME_SAMPLE_PATH, "zh", for_file_export=True)
    # MiSans 回退源同样指向可解析的 file:// 位置（字体文件本机缺失时仍 404，
    # 但 URL 形态正确，装上字体后无需改代码）
    web_uri = (PROJECT_ROOT / "web").as_uri()
    assert f'url("{web_uri}/assets/fonts-local/MiSans-Regular.woff2")' in html


def test_file_export_render_rewrites_photo_base(tmp_path):
    data = yaml.safe_load(MASTER_RESUME_SAMPLE_PATH.read_text(encoding="utf-8"))
    data["meta"]["photo"] = "assets/photo.jpg"
    sample = tmp_path / "resume.photo.yaml"
    sample.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    photo = PROJECT_ROOT / "web" / "assets" / "photo.jpg"
    created = not photo.exists()
    if created:
        photo.write_bytes(b"\xff\xd8\xff\xd9")  # 最小 JPEG 骨架
    try:
        html = _render(sample, "zh", for_file_export=True)
        web_uri = (PROJECT_ROOT / "web").as_uri()
        assert f'src="{web_uri}/assets/photo.jpg"' in html
    finally:
        if created:
            photo.unlink()


def test_preview_render_keeps_document_relative_urls():
    html = _render(MASTER_RESUME_SAMPLE_PATH, "zh")
    # 预览经 /preview/{token} 提供，../assets 由 API 的 /assets 挂载解析
    assert 'url("../assets/fonts/' in html
    assert "file://" not in html
