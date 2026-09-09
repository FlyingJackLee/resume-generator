import os

# Force tracing off for the whole test session, regardless of what .env sets,
# so `pytest` never sends real runs to LangSmith. Must run before
# resume_agent.config (or langsmith itself) is imported by any test module.
os.environ["LANGSMITH_TRACING"] = "false"
