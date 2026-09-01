from typing import Any, TypedDict


class ResumeState(TypedDict, total=False):
    run_id: str
    original_resume: dict[str, Any]
    job_description: str
    job_profile: dict[str, Any]
    match_report: dict[str, Any]
    hr_review: dict[str, Any]
    rewrite_strategy: dict[str, Any]
    approved_strategy: dict[str, Any]
    editor_patch: dict[str, Any]
    candidate_resume: dict[str, Any]
    fact_validation: dict[str, Any]
    hiring_evaluation: dict[str, Any]
    iteration: int
    max_iterations: int
    status: str

