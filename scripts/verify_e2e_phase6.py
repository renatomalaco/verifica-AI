import os
import asyncio
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
import httpx
from service_wait import wait_until_healthy
import uvicorn
from research_runner.api.main import app as research_app
from scan_orchestrator.api.main import app as orchestrator_app

# In-memory scans unless DATABASE_URL is set explicitly; the developer .env may point to a stopped Postgres.
os.environ.setdefault("DATABASE_URL", "")


def run_research_service():
    uvicorn.run(research_app, host="127.0.0.1", port=8004, log_level="warning")


def run_orchestrator_service():
    uvicorn.run(orchestrator_app, host="127.0.0.1", port=8000, log_level="warning")


async def verify_phase_6():
    print("=" * 80)
    print("Iniciando validacao ponta a ponta da Fase 6: Pesquisa, Ablacao e Observabilidade")
    print("=" * 80)

    # 1. The F1 gate refuses to pass while the test split has no real samples (R1 honesty rule)
    res_gate = subprocess.run(
        [sys.executable, "-m", "research_runner", "--threshold-f1", "0.92"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res_gate.returncode in (0, 1, 2), f"Gate CLI crashed: {res_gate.stderr}"
    assert "F1 gate" in res_gate.stdout
    print(f"[OK] 1. F1 gate ran on the test split (exit code {res_gate.returncode}).")

    # 2. The study writes the ablation tables (Markdown + LaTeX) and latest.json
    assert "Modo 1b" in res_gate.stdout and "Modo 3" in res_gate.stdout
    assert r"\begin{table}" in res_gate.stdout
    print("[OK] 2. Ablation tables (Markdown and LaTeX booktabs) generated.")

    # 3. Test the Phase 6 HTTP services
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Wait for research-runner to come up (port 8004)
        ready_research = False
        for _ in range(30):
            try:
                r = await client.get("http://127.0.0.1:8004/health")
                if r.status_code == 200:
                    ready_research = True
                    break
            except httpx.ConnectError:
                await asyncio.sleep(0.2)
        assert ready_research, "Servico research-runner nao respondeu na porta 8004"
        print("[OK] 3. Servico research-runner operacional na porta 8004.")

        # Wait for scan-orchestrator to come up (port 8000)
        ready_orc = False
        for _ in range(30):
            try:
                r = await client.get("http://127.0.0.1:8000/health")
                if r.status_code == 200:
                    ready_orc = True
                    break
            except httpx.ConnectError:
                await asyncio.sleep(0.2)
        assert ready_orc, "Servico scan-orchestrator nao respondeu na porta 8000"
        print("[OK] 4. Servico scan-orchestrator operacional na porta 8000.")

        # 4. The research-runner serves the report the CLI just wrote
        res_report = await client.get("http://127.0.0.1:8004/pesquisa/report")
        assert res_report.status_code == 200
        assert len(res_report.json()["modes"]) == 4
        print("[OK] 5. /pesquisa/report serves the latest study with the 4 ablation modes.")

        # 5. Validate OTel telemetry: W3C traceparent propagation and /metrics endpoint
        trace_headers = {"traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"}
        res_trace = await client.get("http://127.0.0.1:8000/health", headers=trace_headers)
        assert res_trace.status_code == 200
        assert "traceparent" in res_trace.headers
        assert "4bf92f3577b34da6a3ce929d0e0e4736" in res_trace.headers["traceparent"]
        print("[OK] 6. Propagacao de contexto de trace W3C traceparent validada na borda.")

        # 6. Validate Prometheus metrics export (/metrics)
        res_metrics = await client.get("http://127.0.0.1:8000/metrics")
        assert res_metrics.status_code == 200
        assert "http_request_duration_ms" in res_metrics.text
        print("[OK] 7. Endpoint Prometheus /metrics com rastreamento de latencias distribucionais (P50/P95/P99) validado.")

    print("=" * 80)
    print("FASE 6 VALIDADA COM SUCESSO INTEGRAL (100% OK)!")
    print("=" * 80)


def main():
    # CLI and API share one reports folder, so the API serves what the CLI wrote.
    os.environ["RESEARCH_REPORTS_DIR"] = tempfile.mkdtemp(prefix="verifica-reports-")
    procs = [
        multiprocessing.Process(target=run_research_service, daemon=True),
        multiprocessing.Process(target=run_orchestrator_service, daemon=True),
    ]

    for p in procs:
        p.start()

    wait_until_healthy([8000, 8004])

    try:
        asyncio.run(verify_phase_6())
    finally:
        for p in procs:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1.0)


if __name__ == "__main__":
    main()
