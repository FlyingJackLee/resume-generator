import logging

from resume_agent.config import Settings
from resume_agent.logging_config import configure_logging


def test_debug_logging_writes_detailed_file(tmp_path):
    log_file = tmp_path / "resume-agent.log"
    configure_logging(Settings(api_key="fake", log_level="DEBUG", log_file=str(log_file)))
    logging.getLogger("resume_agent.test").debug("node output: structured model response")
    for handler in logging.getLogger().handlers:
        handler.flush()
    content = log_file.read_text(encoding="utf-8")
    assert "DEBUG resume_agent.test" in content
    assert "structured model response" in content
