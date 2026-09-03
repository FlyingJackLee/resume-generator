# Resume Generator

> A local-first, bilingual resume workspace for maintaining a baseline resume, tailoring fact-safe versions to job descriptions, and exporting polished A4 HTML/PDF documents.

Resume Generator combines a structured YAML resume with an AI-assisted review workflow. It is designed for a single user: your resume data stays on your machine, while every AI-generated change remains traceable to the baseline facts.

## Highlights

- **Baseline resume workspace** — edit a single baseline resume in the browser, publish deliberately, and roll back to any published version.
- **Bilingual by default** — maintain Chinese and English content together; preview and export either language.
- **Fact-safe JD tailoring** — analyze a job description, review an AI rewrite strategy, validate every patch against source facts, then approve the final result.
- **Global resume templates** — switch between built-in templates or import a CSS-only template package. The selected template applies consistently to every preview and export.
- **Portable exports** — download A4 HTML or PDF output, plus the current published `resume.yaml`.
- **Local-first** — no authentication service, database, or remote storage is required.

## Workflow

```text
Baseline Resume ── edit draft ── publish ──> web/data/resume.yaml
       │                                      │
       ├── version history / rollback          └── source of truth
       │
       └── ATS JD Matching ── strategy gate ── fact validation ── final version
                                              │
                                              └── HTML / PDF export
```

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 20+ and `pnpm`
- Chromium for PDF generation

### Install

```bash
cp .env.example .env
# Edit .env and set RESUME_AGENT_API_KEY when using ATS JD matching.
uv sync
uv run playwright install chromium
pnpm --dir agent/frontend install
```

On its first start, the application automatically copies `web/data/resume.sample.yaml`
to the ignored local file `web/data/resume.yaml`. Replace that generated file with your
own bilingual resume; it is never committed to Git.

### Run locally

```bash
./dev.sh
```

Open <http://localhost:5173>. The API runs at <http://127.0.0.1:8010>.

If a previous local process already owns a development port:

```bash
lsof -ti:8010,5173 | xargs kill
```

## Core concepts

| Concept | Description |
| --- | --- |
| **Baseline Resume** | The sole current source of truth at `web/data/resume.yaml`. Browser edits become effective only after an explicit publish action. |
| **Editing draft** | A single local draft used by the baseline editor. It autosaves independently and detects local YAML changes. |
| **Run** | One ATS JD-matching workflow for a target role. Artifacts are isolated under `agent/data/runs/<run_id>/`. |
| **Fact validation** | A guardrail that verifies target-resume changes against stable facts derived from the baseline. |
| **Template** | A global, presentation-only theme. It never changes resume data or the A4 export contract. |

## Resume templates

Three built-in themes are included: Classic, Modern Minimal, and Professional Sidebar. Select one from **Templates** and it applies everywhere.

Custom templates are local ZIP packages containing `manifest.json`, `theme.css`, and optional local assets. They may style the fixed resume DOM but cannot execute code, import remote resources, add fields, or change paper settings.

Download the complete authoring specification from the Templates page, or read [Template Package Specification](docs/template-package-spec.md).

## Project structure

```text
agent/
  src/resume_agent/       # FastAPI API, workflow, validation, template services
  frontend/               # React + TypeScript workspace
  data/runs/              # Local, ignored workflow artifacts
web/
  data/resume.yaml        # Published baseline resume
  templates/              # Fixed resume HTML structure
  styles/                 # Base A4 resume styles
docs/                     # Public project documentation
```

Local archives, imported templates, logs, generated runs, `.env`, and PDF build output are intentionally excluded from version control.

## Development

```bash
uv run pytest -q
pnpm --dir agent/frontend build
```

## Data and security notes

- The project is designed for personal local use; do not expose it directly to the public internet.
- Keep `.env` private. It is ignored by Git.
- Imported templates are constrained to CSS and local assets; remote resources and `@import` are rejected.
- A published baseline is versioned before replacement, so it can be restored from the editor.

## Version

Current development version: **1.2.0**.

## License

No license has been selected yet. Add one before redistributing or accepting external contributions.
