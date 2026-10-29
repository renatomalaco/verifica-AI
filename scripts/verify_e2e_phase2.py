import os
import asyncio
import multiprocessing
import time
import httpx
from service_wait import wait_until_healthy
import uvicorn
from ai_gateway.api.main import app as gateway_app
from url_inspector.api.main import app as inspector_app
from scan_orchestrator.api.main import app as orchestrator_app

# In-memory scans unless DATABASE_URL is set explicitly; the developer .env may point to a stopped Postgres.
os.environ.setdefault("DATABASE_URL", "")


def run_gateway():
    uvicorn.run(gateway_app, host="127.0.0.1", port=8001, log_level="warning")


def run_inspector():
    uvicorn.run(inspector_app, host="127.0.0.1", port=8002, log_level="warning")


def run_orchestrator():
    uvicorn.run(orchestrator_app, host="127.0.0.1", port=8000, log_level="warning")


async def verify_phase_2():
    print("Iniciando verificacao ponta a ponta da Fase 2 (Canal URL & Cascata)...")

    # 1. Health checks of the 3 microservices
    async with httpx.AsyncClient(timeout=5.0) as client:
        r_gw = await client.get("http://127.0.0.1:8001/health")
        assert r_gw.status_code == 200
        print("[OK] ai-gateway (porta 8001) respondendo com sucesso.")

        r_ins = await client.get("http://127.0.0.1:8002/health")
        assert r_ins.status_code == 200
        print("[OK] url-inspector (porta 8002) respondendo com sucesso.")

        r_orc = await client.get("http://127.0.0.1:8000/health")
        assert r_orc.status_code == 200
        print("[OK] scan-orchestrator (porta 8000) respondendo com sucesso.")

    # 2. url-inspector SSRF protection
    async with httpx.AsyncClient(timeout=5.0) as client:
        ssrf_payload = {"url": "http://169.254.169.254/latest/meta-data/"}
        r_ssrf = await client.post("http://127.0.0.1:8002/inspect", json=ssrf_payload)
        assert r_ssrf.status_code == 400
        assert "SSRF" in r_ssrf.json()["detail"]
        print("[OK] url-inspector bloqueou tentativa de SSRF em metadados de nuvem (169.254.169.254) com HTTP 400.")

        ssrf_priv_payload = {"url": "http://192.168.1.1/admin"}
        r_ssrf_priv = await client.post("http://127.0.0.1:8002/inspect", json=ssrf_priv_payload)
        assert r_ssrf_priv.status_code == 400
        assert "SSRF" in r_ssrf_priv.json()["detail"]
        print("[OK] url-inspector bloqueou tentativa de SSRF em rede privada RFC 1918 (192.168.1.1) com HTTP 400.")

    # 3. Bare URL analysis via scan-orchestrator (enabled in Phase 2)
    async with httpx.AsyncClient(timeout=30.0) as client:
        url_payload = {"content": "https://google.com"}
        r_scan = await client.post("http://127.0.0.1:8000/api/v1/scans", json=url_payload)
        assert r_scan.status_code == 200
        data = r_scan.json()
        assert data["details"]["channel"] == "url"
        print("[OK] scan-orchestrator processou URL pura com sucesso:")
        print(f"  - Threat Level: {data['threat_level']}")
        print(f"  - Channel: {data['details']['channel']}")
        print(f"  - Deciding Stage: {data['details']['deciding_stage']}")

    # 4. Text analysis with an embedded link (parallel cascade processing)
    async with httpx.AsyncClient(timeout=30.0) as client:
        text_with_link = {
            "content": "Acesse nosso site oficial para ver a tabela de precos: https://google.com"
        }
        r_combined = await client.post("http://127.0.0.1:8000/api/v1/scans", json=text_with_link)
        assert r_combined.status_code == 200
        c_data = r_combined.json()
        assert c_data["details"]["channel"] == "texto"
        print("[OK] scan-orchestrator processou texto com link embutido em paralelo:")
        print(f"  - Threat Level: {c_data['threat_level']}")
        print(f"  - Deciding Stage: {c_data['details']['deciding_stage']}")

    # 5. URL SSE streaming
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("[OK] Testando SSE para canal URL...")
        async with client.stream("POST", "http://127.0.0.1:8000/api/v1/scans/stream", json={"content": "https://google.com"}) as stream:
            assert stream.status_code == 200
            events_received = 0
            async for line in stream.aiter_lines():
                if line.startswith("event:"):
                    events_received += 1
                    print(f"  [SSE Event] {line}")
            assert events_received >= 2
            print("[OK] Streaming SSE de URL validado com sucesso!")

    print("\n=======================================================")
    print("TODAS AS VALIDACOES DA FASE 2 PASSARAM COM 100% DE SUCESSO!")
    print("=======================================================")


if __name__ == "__main__":
    p_gw = multiprocessing.Process(target=run_gateway, daemon=True)
    p_ins = multiprocessing.Process(target=run_inspector, daemon=True)
    p_orc = multiprocessing.Process(target=run_orchestrator, daemon=True)

    p_gw.start()
    p_ins.start()
    p_orc.start()
    wait_until_healthy([8000, 8001, 8002])

    try:
        asyncio.run(verify_phase_2())
    finally:
        p_gw.terminate()
        p_ins.terminate()
        p_orc.terminate()
