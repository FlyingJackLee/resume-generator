from resume_agent.errors import ResumeAgentError
from resume_agent.models import RewriteStrategy
from resume_agent.paths import MASTER_RESUME_SAMPLE_PATH
from resume_agent.services import load_master_resume, prepare_working_resume
from resume_agent.services.catalog import editable_catalog
from resume_agent.services.strategy_validator import validate_strategy


def test_work_entries_container_is_not_reorderable():
    master = prepare_working_resume(load_master_resume(MASTER_RESUME_SAMPLE_PATH))
    catalog_paths = {item["path"] for item in editable_catalog(master)}
    assert "/sections/experience/entries" not in catalog_paths
    assert "/sections/projects/entries" in catalog_paths


def test_reordering_work_entries_is_rejected():
    master = prepare_working_resume(load_master_resume(MASTER_RESUME_SAMPLE_PATH))
    strategy = RewriteStrategy.model_validate(
        {
            "positioning": "test",
            "safe_keywords": [],
            "forbidden_keywords": [],
            "actions": [
                {
                    "action": "reorder",
                    "target_path": "/sections/experience/entries",
                    "priority": 1,
                    "instruction": "Put the most recent role first",
                    "supported_by": [],
                }
            ],
        }
    )
    try:
        validate_strategy(strategy, master)
    except ResumeAgentError as exc:
        assert "/sections/experience/entries" in str(exc)
    else:
        raise AssertionError("reordering work entries should have been rejected")
