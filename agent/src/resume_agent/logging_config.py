from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from resume_agent.config import Settings
from resume_agent.paths import PROJECT_ROOT


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(threadName)s] %(message)s"
    )
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        if getattr(handler, "_resume_agent_handler", False):
            root.removeHandler(handler)
            handler.close()

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    console._resume_agent_handler = True  # type: ignore[attr-defined]
    root.addHandler(console)

    log_path = Path(settings.log_file)
    if not log_path.is_absolute():
        log_path = PROJECT_ROOT / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler._resume_agent_handler = True  # type: ignore[attr-defined]
    root.addHandler(file_handler)

    logging.getLogger(__name__).info(
        "logging configured level=%s file=%s; API keys are never logged",
        settings.log_level,
        log_path,
    )

