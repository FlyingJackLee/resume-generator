import asyncio
import json

import httpx

from fakes import HappyProvider
from resume_agent.api.main import create_app
from resume_agent.config import Settings
from resume_agent.models import ResumePatch, RewriteStrategy
from resume_agent.services.workflow_service import WorkflowService

from test_workflow_service import make_service


async def wait_for_status(client, run_id, expected):
    for _ in range(200):
        response = await client.get(f"/api/v1/resume/runs/{run_id}")
        if response.json()["status"] == expected:
            return response.json()
        await asyncio.sleep(0.01)
    raise AssertionError(f"run did not reach {expected}")


def test_api_executes_both_human_gates(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
            "/api/v1/resume/runs",
            json={
                "jd_label": "Google AI Agent",
                "job_description": "We need a senior engineer to build reliable AI agent systems.",
            },
        )
            assert response.status_code == 202
            run_id = response.json()["run_id"]
            await wait_for_status(client, run_id, "WAITING_STRATEGY_APPROVAL")
            artifacts = await client.get(f"/api/v1/resume/runs/{run_id}/artifacts")
            assert artifacts.status_code == 200
            strategy = artifacts.json()["rewrite_strategy"]
            assert strategy["positioning"]
            assert strategy["actions"][0]["supported_by"]

            response = await client.post(f"/api/v1/resume/runs/{run_id}/approve-strategy", json={})
            assert response.status_code == 202
            await wait_for_status(client, run_id, "WAITING_FINAL_APPROVAL")
            assert (await client.get(f"/api/v1/resume/runs/{run_id}/diff")).status_code == 200

            response = await client.post(f"/api/v1/resume/runs/{run_id}/approve-final")
            assert response.status_code == 200
            assert response.json()["target_file"] == "google_ai_agent_resume.yaml"
    asyncio.run(scenario())


def test_root_loads_without_api_key_when_service_is_injected(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert "API only" in response.json()["message"]
    asyncio.run(scenario())


def test_list_runs_endpoint_paginates(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            for i in range(3):
                await client.post(
                    "/api/v1/resume/runs",
                    json={"jd_label": f"JD {i}", "job_description": "A sufficiently long job description."},
                )
            response = await client.get("/api/v1/resume/runs", params={"page": 1, "page_size": 2})
            assert response.status_code == 200
            body = response.json()
            assert body["total"] == 3
            assert len(body["items"]) == 2
    asyncio.run(scenario())


def test_create_run_accepts_optional_company(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "company": "Google",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]
            detail = await client.get(f"/api/v1/resume/runs/{run_id}")
            assert detail.json()["company"] == "Google"
    asyncio.run(scenario())


def test_run_events_and_notes_endpoints(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]
            events = await client.get(f"/api/v1/resume/runs/{run_id}/events")
            assert events.status_code == 200
            assert events.json()[0]["status"] == "INIT"

            notes = await client.post(
                f"/api/v1/resume/runs/{run_id}/notes", json={"notes": "跟进一下内推"}
            )
            assert notes.status_code == 200
            assert notes.json()["notes"] == "跟进一下内推"
    asyncio.run(scenario())


def test_run_facts_endpoint_returns_master_resume_facts(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]
            facts = await client.get(f"/api/v1/resume/runs/{run_id}/facts")
            assert facts.status_code == 200
            body = facts.json()
            assert "fact_introduction_body" in body
            assert body["fact_introduction_body"]["statement"]["zh"]
    asyncio.run(scenario())


def test_run_artifacts_endpoint_reveals_artifacts_progressively(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]

            fresh = await client.get(f"/api/v1/resume/runs/{run_id}/artifacts")
            assert fresh.status_code == 200
            assert fresh.json() == {key: None for key in (
                "job_profile", "match_report", "hr_review", "rewrite_strategy",
                "validation", "hiring_review", "final_diff", "error",
            )}

            await wait_for_status(client, run_id, "WAITING_STRATEGY_APPROVAL")
            analyzed = (await client.get(f"/api/v1/resume/runs/{run_id}/artifacts")).json()
            assert analyzed["job_profile"]["target_company"] == "Google"
            assert analyzed["match_report"]["matches"]
            assert analyzed["hr_review"]["strengths"]
            assert analyzed["rewrite_strategy"]["positioning"]
            assert analyzed["validation"] is None

            await client.post(f"/api/v1/resume/runs/{run_id}/approve-strategy", json={})
            await wait_for_status(client, run_id, "WAITING_FINAL_APPROVAL")
            reviewed = (await client.get(f"/api/v1/resume/runs/{run_id}/artifacts")).json()
            assert reviewed["validation"]["passed"] is True
            assert reviewed["hiring_review"]["decision"] == "PASS"
            assert reviewed["final_diff"]
    asyncio.run(scenario())


class ReorderProvider(HappyProvider):
    def complete(self, *, system, user, output_type, temperature):
        if output_type is RewriteStrategy:
            self.calls.append(output_type.__name__)
            return RewriteStrategy.model_validate(
                {
                    "positioning": "AI Agent engineer with full-stack delivery experience",
                    "safe_keywords": ["AI Agent", "LangGraph"],
                    "forbidden_keywords": [],
                    "actions": [
                        {
                            "action": "rewrite",
                            "target_path": "/sections/introduction/body",
                            "priority": 1,
                            "instruction": "Lead with AI Agent delivery",
                            "supported_by": ["fact_introduction_body"],
                        },
                        {
                            "action": "reorder",
                            "target_path": "/sections/projects/entries",
                            "priority": 2,
                            "instruction": "Put the most relevant project first",
                            "supported_by": [],
                        },
                    ],
                }
            )
        if output_type is ResumePatch:
            self.calls.append(output_type.__name__)
            return ResumePatch.model_validate(
                {
                    "operations": [
                        {
                            "op": "replace",
                            "path": "/sections/introduction/body",
                            "supported_by": ["fact_introduction_body"],
                            "reason": "Align positioning",
                            "value": {"zh": self.body["zh"], "en": self.body["en"]},
                        },
                        {
                            "op": "reorder",
                            "path": "/sections/projects/entries",
                            "value": [
                                "backend_development",
                                "full_stack_development",
                                "system_architecture_core_development_3",
                                "ai_agent_full_stack_development",
                                "system_architecture_core_development",
                            ],
                        },
                    ]
                }
            )
        return super().complete(system=system, user=user, output_type=output_type, temperature=temperature)


def _entry_order(catalog: list[dict], collection_path: str) -> list[str]:
    prefix = f"{collection_path}/"
    return [
        item["path"][len(prefix):]
        for item in catalog
        if item["path"].startswith(prefix) and item["path"].count("/") == collection_path.count("/") + 1
    ]


def test_structure_endpoint_candidate_source_reflects_reorder(tmp_path):
    settings = Settings(api_key="fake", hiring_threshold=85, max_iterations=2)
    service = WorkflowService(ReorderProvider(), settings, runs_root=tmp_path)

    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]

            too_early = await client.get(
                f"/api/v1/resume/runs/{run_id}/structure", params={"source": "candidate"}
            )
            assert too_early.status_code == 400

            await wait_for_status(client, run_id, "WAITING_STRATEGY_APPROVAL")
            await client.post(f"/api/v1/resume/runs/{run_id}/approve-strategy", json={})
            await wait_for_status(client, run_id, "WAITING_FINAL_APPROVAL")

            input_catalog = (
                await client.get(f"/api/v1/resume/runs/{run_id}/structure", params={"source": "input"})
            ).json()
            candidate_catalog = (
                await client.get(
                    f"/api/v1/resume/runs/{run_id}/structure", params={"source": "candidate"}
                )
            ).json()

            input_order = _entry_order(input_catalog, "/sections/projects/entries")
            candidate_order = _entry_order(candidate_catalog, "/sections/projects/entries")
            assert input_order == [
                "system_architecture_core_development",
                "ai_agent_full_stack_development",
                "system_architecture_core_development_3",
                "full_stack_development",
                "backend_development",
            ]
            assert candidate_order == [
                "backend_development",
                "full_stack_development",
                "system_architecture_core_development_3",
                "ai_agent_full_stack_development",
                "system_architecture_core_development",
            ]
            assert set(input_order) == set(candidate_order)
    asyncio.run(scenario())


def test_structure_endpoint_rejects_unknown_source(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]
            bad = await client.get(
                f"/api/v1/resume/runs/{run_id}/structure", params={"source": "bogus"}
            )
            assert bad.status_code == 400
    asyncio.run(scenario())


def test_run_structure_endpoint_returns_labelled_catalog(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]
            structure = await client.get(f"/api/v1/resume/runs/{run_id}/structure")
            assert structure.status_code == 200
            catalog = structure.json()
            assert catalog
            assert all("path" in item and "kind" in item and "label" in item for item in catalog)
    asyncio.run(scenario())


def test_preview_master_and_run_endpoints(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            master = await client.get("/preview/master", params={"lang": "zh"})
            assert master.status_code == 200
            assert "<html" in master.text

            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]
            not_ready = await client.get(f"/preview/{run_id}")
            assert not_ready.status_code == 400

            await wait_for_status(client, run_id, "WAITING_STRATEGY_APPROVAL")
            await client.post(f"/api/v1/resume/runs/{run_id}/approve-strategy", json={})
            await wait_for_status(client, run_id, "WAITING_FINAL_APPROVAL")
            candidate_preview = await client.get(f"/preview/{run_id}", params={"lang": "en"})
            assert candidate_preview.status_code == 200
            assert "<html" in candidate_preview.text

            await client.post(f"/api/v1/resume/runs/{run_id}/approve-final")
            final_preview = await client.get(f"/preview/{run_id}")
            assert final_preview.status_code == 200
    asyncio.run(scenario())


def test_stream_endpoint_emits_events_until_terminal_status(tmp_path):
    # Drive the run to a terminal status *before* opening the stream, so the
    # generator sees a terminal event on its very first pass and returns
    # immediately. This keeps the test independent of ASGI disconnect
    # detection, which httpx's in-process transport doesn't reliably signal
    # for a client that stops reading a still-open stream.
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/resume/runs",
                json={
                    "jd_label": "Google AI Agent",
                    "job_description": "We need a senior engineer to build reliable AI agent systems.",
                },
            )
            run_id = response.json()["run_id"]
            await wait_for_status(client, run_id, "WAITING_STRATEGY_APPROVAL")
            await client.post(f"/api/v1/resume/runs/{run_id}/approve-strategy", json={})
            await wait_for_status(client, run_id, "WAITING_FINAL_APPROVAL")
            await client.post(f"/api/v1/resume/runs/{run_id}/approve-final")

            response = await client.get(f"/api/v1/resume/runs/{run_id}/stream")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            lines = [line for line in response.text.splitlines() if line.startswith("data: ")]
            assert lines
            events = [json.loads(line[len("data: "):]) for line in lines]
            assert events[-1]["status"] == "COMPLETED"
    asyncio.run(scenario())
