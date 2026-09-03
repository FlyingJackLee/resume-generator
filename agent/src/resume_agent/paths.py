from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MASTER_RESUME_PATH = PROJECT_ROOT / "web" / "data" / "resume.yaml"
MASTER_RESUME_SAMPLE_PATH = PROJECT_ROOT / "web" / "data" / "resume.sample.yaml"
RUNS_ROOT = PROJECT_ROOT / "agent" / "data" / "runs"
TEMPLATES_ROOT = PROJECT_ROOT / "agent" / "data" / "templates"
