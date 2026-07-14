"""Lightweight load test: concurrent authenticated traffic with latency stats.

Not a substitute for a real load-testing rig; it demonstrates the platform
holds under concurrency and gives honest p50/p95/p99 numbers for the README.

Usage:
    python scripts/load_test.py [--api URL] [--requests 200] [--concurrency 20]
"""

import argparse
import asyncio
import statistics
import time
import uuid

import httpx


async def main(api: str, total: int, concurrency: int) -> None:
    async with httpx.AsyncClient(base_url=api, timeout=30) as client:
        register = await client.post(
            "/api/v1/auth/register",
            json={
                "tenant_name": f"load-{uuid.uuid4().hex[:8]}",
                "admin_email": f"load-{uuid.uuid4().hex[:8]}@clinic.example",
                "admin_password": "load-test-password-1",
                "admin_display_name": "Load Tester",
            },
        )
        register.raise_for_status()
        headers = {"Authorization": f"Bearer {register.json()['access_token']}"}
        patient = await client.post(
            "/api/v1/patients", headers=headers, json={"display_name": "Load Patient"}
        )
        pid = patient.json()["patient_id"]

        latencies: list[float] = []
        errors = 0
        semaphore = asyncio.Semaphore(concurrency)

        async def one(i: int) -> None:
            nonlocal errors
            async with semaphore:
                start = time.perf_counter()
                try:
                    if i % 3 == 0:
                        r = await client.get(f"/api/v1/patients/{pid}/care-plan", headers=headers)
                    elif i % 3 == 1:
                        r = await client.get("/api/v1/patients", headers=headers)
                    else:
                        r = await client.get(f"/api/v1/patients/{pid}/timeline", headers=headers)
                    if r.status_code != 200:
                        errors += 1
                finally:
                    latencies.append(time.perf_counter() - start)

        started = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(total)))
        wall = time.perf_counter() - started

        latencies.sort()
        p = lambda q: latencies[int(q * (len(latencies) - 1))] * 1000  # noqa: E731
        print(f"requests: {total}  concurrency: {concurrency}  wall: {wall:.2f}s")
        print(f"throughput: {total / wall:.1f} req/s   errors: {errors}")
        print(f"latency ms  p50: {p(0.50):.1f}  p95: {p(0.95):.1f}  p99: {p(0.99):.1f}  "
              f"mean: {statistics.mean(latencies) * 1000:.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(main(args.api, args.requests, args.concurrency))
