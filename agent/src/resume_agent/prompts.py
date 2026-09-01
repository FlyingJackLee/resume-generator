from pathlib import Path

from resume_agent.paths import PROJECT_ROOT


PROMPT_ROOT = PROJECT_ROOT / "agent" / "prompts"


class PromptRepository:
    def __init__(self, version: str = "v1"):
        self.version = version

    def load(self, name: str) -> str:
        return (PROMPT_ROOT / self.version / f"{name}.md").read_text(encoding="utf-8").strip()

