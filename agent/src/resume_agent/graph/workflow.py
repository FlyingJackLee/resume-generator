from __future__ import annotations

from typing import Any
import logging

from langgraph.graph import END, START, StateGraph

from resume_agent.agents import AgentNodes
from resume_agent.models import ResumePatch
from resume_agent.services import apply_patch, validate_candidate

from .state import ResumeState


logger = logging.getLogger(__name__)


def build_analysis_graph(nodes: AgentNodes):
    graph = StateGraph(ResumeState)
    graph.add_node("analyze_jd", nodes.analyze_jd)
    graph.add_node("match_resume", nodes.match_resume)
    graph.add_node("hr_review", nodes.hr_review)
    graph.add_node("build_strategy", nodes.build_strategy)
    graph.add_edge(START, "analyze_jd")
    graph.add_edge("analyze_jd", "match_resume")
    graph.add_edge("match_resume", "hr_review")
    graph.add_edge("hr_review", "build_strategy")
    graph.add_edge("build_strategy", END)
    return graph.compile()


def build_compile_graph(nodes: AgentNodes):
    def apply_editor_patch(state: ResumeState) -> dict[str, Any]:
        logger.info(
            "node started: apply_patch run_id=%s iteration=%s",
            state.get("run_id"), state.get("iteration"),
        )
        patch = ResumePatch.model_validate(state["editor_patch"])
        candidate = apply_patch(state["original_resume"], patch)
        logger.debug("patch applied run_id=%s operations=%s", state.get("run_id"), patch.model_dump())
        return {"candidate_resume": candidate, "status": "VALIDATING"}

    def validate(state: ResumeState) -> dict[str, Any]:
        logger.info(
            "node started: validate_facts run_id=%s iteration=%s",
            state.get("run_id"), state.get("iteration"),
        )
        result = validate_candidate(state["original_resume"], state["candidate_resume"])
        logger.debug("fact validation run_id=%s result=%s", state.get("run_id"), result.model_dump())
        return {"fact_validation": result.model_dump(), "status": "REVIEWING" if result.passed else "REVISING"}

    def route_validation(state: ResumeState) -> str:
        if state["fact_validation"]["passed"]:
            return "hiring_manager"
        if state["iteration"] < state["max_iterations"]:
            return "edit_resume"
        return "validation_failed"

    def route_hiring(state: ResumeState) -> str:
        if state["hiring_evaluation"]["decision"] == "PASS":
            return "final_ready"
        if state["iteration"] < state["max_iterations"]:
            return "edit_resume"
        return "final_ready"

    def validation_failed(_: ResumeState) -> dict[str, str]:
        return {"status": "FAILED"}

    def final_ready(_: ResumeState) -> dict[str, str]:
        return {"status": "WAITING_FINAL_APPROVAL"}

    graph = StateGraph(ResumeState)
    graph.add_node("edit_resume", nodes.edit_resume)
    graph.add_node("apply_patch", apply_editor_patch)
    graph.add_node("validate_facts", validate)
    graph.add_node("hiring_manager", nodes.hiring_manager)
    graph.add_node("validation_failed", validation_failed)
    graph.add_node("final_ready", final_ready)
    graph.add_edge(START, "edit_resume")
    graph.add_edge("edit_resume", "apply_patch")
    graph.add_edge("apply_patch", "validate_facts")
    graph.add_conditional_edges("validate_facts", route_validation)
    graph.add_conditional_edges("hiring_manager", route_hiring)
    graph.add_edge("validation_failed", END)
    graph.add_edge("final_ready", END)
    return graph.compile()
