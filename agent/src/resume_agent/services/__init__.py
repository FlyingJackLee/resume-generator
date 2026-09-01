from .diff_service import build_diff
from .fact_validator import validate_candidate
from .master_resume import load_master_resume, prepare_working_resume
from .patch_engine import apply_patch

__all__ = [
    "apply_patch",
    "build_diff",
    "load_master_resume",
    "prepare_working_resume",
    "validate_candidate",
]

