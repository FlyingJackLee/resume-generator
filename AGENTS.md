# Repository rules

- `web/data/resume.yaml` is the only Master Resume and the only source of truth.
- Agent code must treat the Master Resume as read-only. Never write, format, migrate,
  or overwrite it during a run.
- Generate stable IDs, facts, and `supported_by` metadata only in an in-memory working
  copy. Write all generated artifacts below `agent/data/runs/<run_id>/`.
- A target resume may rewrite, reorder, hide, or omit approved content, but it must not
  mutate the Master Resume.
- Manage Python dependencies and commands with uv (`uv sync`, `uv run ...`).

