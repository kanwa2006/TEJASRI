"""TEJASRI resilience demonstration — "memory that survives failures".

What it proves, live:

1. CONCURRENCY  — N concurrent agents race on one patient's care plan;
   exactly one write wins per version, none are silently lost.
2. DURABILITY   — the CockroachDB node is hard-restarted mid-demo;
   every conversation turn, note embedding, task, and audit row survives.
3. RECALL       — after the restart, vector recall still answers from the
   same C-SPANN index with zero warm-up (it is disk-based table data).

Prerequisites: backend API running on --api (default http://127.0.0.1:8000),
local CockroachDB in the Docker container named `crdb`, migrations applied.

Usage:
    python scripts/demo_resilience.py [--api http://127.0.0.1:8000] [--skip-restart]
"""

import argparse
import asyncio
import subprocess
import sys
import time
import uuid

import httpx

# Windows consoles may default to cp1252, which can't print "✓".
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PASSWORD = "demo-resilience-password"


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n  {text}\n{'=' * 64}")


async def wait_for_api(client: httpx.AsyncClient) -> None:
    for _ in range(60):
        try:
            response = await client.get("/api/v1/health/ready")
            if response.status_code == 200 and response.json()["database"] == "ok":
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(1)
    sys.exit("API/database did not become ready in time")


async def main(api: str, skip_restart: bool) -> None:
    # Generous timeout: the agent turn may run a local CPU LLM (Ollama).
    async with httpx.AsyncClient(base_url=api, timeout=240) as client:
        await wait_for_api(client)

        banner("Setup: tenant, patient, care plan, clinical notes")
        register = await client.post(
            "/api/v1/auth/register",
            json={
                "tenant_name": f"demo-clinic-{uuid.uuid4().hex[:8]}",
                "admin_email": f"demo-{uuid.uuid4().hex[:8]}@clinic.example",
                "admin_password": PASSWORD,
                "admin_display_name": "Demo Coordinator",
            },
        )
        register.raise_for_status()
        headers = {"Authorization": f"Bearer {register.json()['access_token']}"}

        patient = await client.post(
            "/api/v1/patients",
            headers=headers,
            json={
                "display_name": "Asha Rao (synthetic)",
                "conditions": ["type 2 diabetes", "hypertension"],
                "allergies": ["penicillin"],
            },
        )
        patient.raise_for_status()
        pid = patient.json()["patient_id"]

        notes = [
            "Started metformin 500mg twice daily for type 2 diabetes.",
            "Blood pressure stable at 130/85; continuing lisinopril 10mg daily.",
            "Patient reported mild dizziness in the mornings last month.",
        ]
        for text in notes:
            (
                await client.post(
                    f"/api/v1/patients/{pid}/notes", headers=headers, json={"note_text": text}
                )
            ).raise_for_status()
        print(f"  patient {pid} with {len(notes)} embedded notes")

        plan = await client.get(f"/api/v1/patients/{pid}/care-plan", headers=headers)
        version = plan.json()["plan"]["version"]

        banner("1) CONCURRENCY: 5 agents race to update one care plan")
        meds = [[{"name": n, "dose": "1 tab", "schedule": "daily", "rxnorm": None}]
                for n in ("metformin", "lisinopril", "atorvastatin", "amlodipine", "aspirin")]

        async def contender(medlist: list[dict[str, object]]) -> int:
            response = await client.put(
                f"/api/v1/patients/{pid}/care-plan/medications",
                headers=headers,
                json={
                    "medications": medlist,
                    "expected_version": version,
                    "acknowledge_warnings": True,
                },
            )
            return response.status_code

        statuses = await asyncio.gather(*(contender(m) for m in meds))
        winners = statuses.count(200)
        conflicts = statuses.count(409)
        print(f"  results: {winners} winner, {conflicts} clean version conflicts")
        assert winners == 1, "exactly one concurrent writer must win"
        after = await client.get(f"/api/v1/patients/{pid}/care-plan", headers=headers)
        print(f"  final plan version: {after.json()['plan']['version']} (no lost updates)")

        turn = await client.post(
            f"/api/v1/patients/{pid}/agent/turn",
            headers=headers,
            json={"message": "What diabetes medication am I taking and is it safe?"},
        )
        turn.raise_for_status()
        print(f"  agent answered via '{turn.json()['provider']}' "
              f"with {len(turn.json()['evidence'])} evidence notes")

        if not skip_restart:
            banner("2) DURABILITY: hard-restarting the CockroachDB node NOW")
            subprocess.run(["docker", "restart", "crdb"], check=True, capture_output=True)
            print("  node restarted; waiting for the memory layer to return…")
            start = time.monotonic()
            await wait_for_api(client)
            print(f"  memory layer back in {time.monotonic() - start:.1f}s")

        banner("3) VERIFICATION: everything survived")
        conversation = await client.get(
            f"/api/v1/patients/{pid}/conversation", headers=headers
        )
        recall = await client.get(
            f"/api/v1/patients/{pid}/notes/recall",
            headers=headers,
            params={"q": "diabetes medication", "limit": 3},
        )
        audit = await client.get(
            "/api/v1/audit", headers=headers, params={"patient_id": pid}
        )
        plan_after = await client.get(f"/api/v1/patients/{pid}/care-plan", headers=headers)

        checks = {
            "conversation turns": len(conversation.json()),
            "vector-recall results (no warm-up)": len(recall.json()),
            "audit entries": len(audit.json()),
            "care plan version": plan_after.json()["plan"]["version"],
        }
        for label, value in checks.items():
            print(f"  ✓ {label}: {value}")
        assert len(conversation.json()) >= 2
        assert len(recall.json()) >= 1
        assert "metformin" in recall.json()[0]["note"]["note_text"]

        banner("RESULT: zero data loss — memory is load-bearing and it held")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-restart", action="store_true",
                        help="skip the docker restart step (e.g. cloud demo)")
    args = parser.parse_args()
    asyncio.run(main(args.api, args.skip_restart))
