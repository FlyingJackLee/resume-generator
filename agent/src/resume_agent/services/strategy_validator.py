from __future__ import annotations

from resume_agent.errors import ResumeAgentError
from resume_agent.models import RewriteStrategy

from .catalog import editable_catalog
from .master_resume import collect_facts


def validate_strategy(strategy: RewriteStrategy, resume: dict) -> None:
    catalog = editable_catalog(resume)
    valid_paths = {item["path"] for item in catalog}
    facts = collect_facts(resume)
    fact_ids = set(facts)
    for action in strategy.actions:
        if action.target_path not in valid_paths:
            raise ResumeAgentError(f"Strategy 使用非法路径：{action.target_path}")
        unknown = set(action.supported_by) - fact_ids
        if unknown:
            raise ResumeAgentError(f"Strategy 使用不存在的 facts：{sorted(unknown)}")
    # safe_keywords may be semantic normalizations (for example 分布式系统 from
    # 分布式微服务), so exact string matching here creates false negatives. The
    # Editor patch remains protected by selected fact IDs and Fact Validator.
