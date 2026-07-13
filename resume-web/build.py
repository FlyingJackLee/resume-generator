from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent


def load_data(path="data/resume.yaml"):
    """读取并解析简历 YAML，返回 dict。"""
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def localize(node, lang):
    """若 node 是含 zh/en 的 dict 则取对应语言，否则原样返回。"""
    if isinstance(node, dict) and "zh" in node and "en" in node:
        return node[lang]
    return node
