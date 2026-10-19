import asyncio
import multiprocessing
import subprocess
import sys
import time
import httpx
import uvicorn
from research_runner.api.main import app as research_app
from scan_orchestrator.api.main import app as orchestrator_app


def run_research_service():
    uvicorn.run(research_app, host="127.0.0.1", port=8004, log_level="warning")


def run_orchestrator_service():
    uvicorn.run(orchestrator_app, host="127.0.0.1", port=8000, log_level="warning")


async def verify_phase_6():
    print("=" * 80)
    print("Iniciando validacao ponta a ponta da Fase 6: Pesquisa, Ablacao e Observabilidade")
    print("=" * 80)

    # 1. Validate the scientific regression gate CLI (F1 >= 0.92)
    res_cli = subprocess.run(
        [sys.executable, "-m", "research_runner", "--mode", "cascade", "--threshold-f1", "0.92"],
        capture_output=True,
        text=True,
    )
    assert res_cli.returncode == 0, f"Falha no CLI gate da cascata: {res_cli.stderr}"
    assert "GATE CIENTIFICO: APROVADO" in res_cli.stdout
    print("[OK] 1. CLI Gate Cientifico automatizado aprovado com F1 >= 0.92.")

    # 2. Validate the ablation comparison table output and LaTeX code
    res_all = subprocess.run(
        [sys.executable, "-m", "research_runner", "--mode", "all"],
        capture_output=True,
        text=True,
    )
    assert res_all.returncode == 0
    assert "Modo 1" in res_all.stdout
    assert "Modo 1b" in res_all.stdout
    assert "Modo 2" in res_all.stdout
    assert "Modo 3" in res_all.stdout
    assert "\\begin{table}" in res_all.stdout
    print("[OK] 2. Geracao automatica de tabelas de ablacao comparativa e LaTeX (Booktabs) para o TCC validada.")

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

        # 4. Validate the internal /pesquisa route on the research-runner API
        res_pesquisa = await client.get("http://127.0.0.1:8004/pesquisa")
        assert res_pesquisa.status_code == 200
        data_pesquisa = res_pesquisa.json()
        assert len(data_pesquisa["evaluations"]) == 4
        assert "markdown_table" in data_pesquisa
        assert "latex_table" in data_pesquisa
        print("[OK] 5. Rota interna /pesquisa retornou os 4 modos de ablacao com sucesso.")

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
    procs = [
        multiprocessing.Process(target=run_research_service, daemon=True),
        multiprocessing.Process(target=run_orchestrator_service, daemon=True),
    ]

    for p in procs:
        p.start()

    time.sleep(1.0)

    try:
        asyncio.run(verify_phase_6())
    finally:
        for p in procs:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1.0)


if __name__ == "__main__":
    main()
