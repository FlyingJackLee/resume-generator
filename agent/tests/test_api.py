import asyncio

import httpx

from resume_agent.api.main import create_app

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
            gate = await client.get(f"/runs/{run_id}/view")
            assert "岗位定位" in gate.text
            assert "事实依据" in gate.text
            assert "保存策略修改" in gate.text

            response = await client.post(f"/api/v1/resume/runs/{run_id}/approve-strategy", json={})
            assert response.status_code == 202
            await wait_for_status(client, run_id, "WAITING_FINAL_APPROVAL")
            assert (await client.get(f"/api/v1/resume/runs/{run_id}/diff")).status_code == 200

            response = await client.post(f"/api/v1/resume/runs/{run_id}/approve-final")
            assert response.status_code == 200
            assert response.json()["target_file"] == "google_ai_agent_resume.yaml"
    asyncio.run(scenario())


def test_ui_loads_without_api_key_when_service_is_injected(tmp_path):
    service = make_service(tmp_path)
    async def scenario():
        transport = httpx.ASGITransport(app=create_app(lambda: service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert "Master Resume 始终只读" in response.text
    asyncio.run(scenario())
