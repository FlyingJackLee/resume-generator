import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import load_data, localize  # noqa: E402


def test_load_data_has_meta_and_sections():
    data = load_data()
    assert data["meta"]["name"]["zh"] == "李祖民"
    assert data["meta"]["name"]["en"] == "Zumin Li"
    assert len(data["sections"]) == 5


def test_localize_picks_language():
    node = {"zh": "个人介绍", "en": "Introduction"}
    assert localize(node, "zh") == "个人介绍"
    assert localize(node, "en") == "Introduction"


def test_localize_passthrough_for_plain_values():
    assert localize("FlyingJackLee", "zh") == "FlyingJackLee"
    assert localize({"url": "x", "label": "y"}, "en") == {"url": "x", "label": "y"}


def test_section_types_are_known():
    data = load_data()
    types = {s["type"] for s in data["sections"]}
    assert types <= {"paragraph", "skills", "education", "entries"}


def test_localize_single_language_fallback():
    assert localize({"zh": "只中文"}, "en") == "只中文"
    assert localize({"en": "en only"}, "zh") == "en only"
