from resume_agent.config import Settings
from resume_agent.models import ResumePatch, RewriteStrategy
from resume_agent.services.workflow_service import WorkflowService

from fakes import HappyProvider


def make_service(tmp_path):
    settings = Settings(api_key="fake", hiring_threshold=85, max_iterations=2)
    return WorkflowService(HappyProvider(), settings, runs_root=tmp_path)


def test_two_human_gates_and_named_final_output(tmp_path):
    service = make_service(tmp_path)
    created = service.create("Google AI Agent", "We need a senior engineer to build reliable AI agents.")
    run_id = created["run_id"]
    assert created["status"] == "ANALYZING"

    service.analyze(run_id)
    assert service.get(run_id)["status"] == "WAITING_STRATEGY_APPROVAL"
    assert not (service.resolve_run(run_id) / "candidate_resume.yaml").exists()

    service.approve_strategy(run_id)
    service.compile(run_id)
    reviewed = service.get(run_id)
    assert reviewed["status"] == "WAITING_FINAL_APPROVAL"
    assert reviewed["hiring_score"] == 92
    assert not (service.resolve_run(run_id) / "google_ai_agent_resume.yaml").exists()

    completed = service.approve_final(run_id)
    assert completed["status"] == "COMPLETED"
    assert completed["target_file"] == "google_ai_agent_resume.yaml"
    assert (service.resolve_run(run_id) / completed["target_file"]).exists()


def test_final_cannot_be_approved_before_gate(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    try:
        service.approve_final(run_id)
    except Exception as exc:
        assert "不能批准最终版本" in str(exc)
    else:
        raise AssertionError("approve_final should have failed")


def test_human_strategy_allows_semantically_normalized_safe_keyword(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Google AI Agent", "A sufficiently long pasted job description.")["run_id"]
    service.analyze(run_id)
    strategy = RewriteStrategy.model_validate_json(
        (service.resolve_run(run_id) / "rewrite_strategy.json").read_text(encoding="utf-8")
    )
    strategy.safe_keywords.append("分布式系统")
    assert service.revise_strategy(run_id, strategy)["status"] == "WAITING_STRATEGY_APPROVAL"


class AlwaysInvalidProvider(HappyProvider):
    def complete(self, *, system, user, output_type, temperature):
        if output_type is ResumePatch:
            self.calls.append(output_type.__name__)
            return ResumePatch.model_validate({
                "operations": [{
                    "op": "replace",
                    "path": "/sections/introduction/body",
                    "supported_by": ["fact_introduction_body"],
                    "reason": "unsafe",
                    "value": {
                        "zh": self.body["zh"] + " 使用 Rust 获得 99% 提升。",
                        "en": self.body["en"] + " Used Rust for a 99% gain.",
                    },
                }]
            })
        return super().complete(system=system, user=user, output_type=output_type, temperature=temperature)


def test_validator_rework_is_bounded_to_two_editor_attempts(tmp_path):
    provider = AlwaysInvalidProvider()
    settings = Settings(api_key="fake", max_iterations=2)
    service = WorkflowService(provider, settings, runs_root=tmp_path)
    run_id = service.create("Unsafe JD", "A sufficiently long pasted job description.")["run_id"]
    service.analyze(run_id)
    service.approve_strategy(run_id)
    service.compile(run_id)
    assert service.get(run_id)["status"] == "FAILED"
    assert provider.calls.count("ResumePatch") == 2
    assert "HiringEvaluation" not in provider.calls


def test_stale_active_run_is_marked_interrupted_and_can_retry(tmp_path):
    service = make_service(tmp_path)
    run_id = service.create("Retry JD", "A sufficiently long pasted job description.")["run_id"]
    restarted = make_service(tmp_path)
    assert restarted.get(run_id)["status"] == "INTERRUPTED"
    assert restarted.retry_analysis(run_id)["status"] == "ANALYZING"
