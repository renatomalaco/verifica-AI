import asyncio
import httpx
import uvicorn
import multiprocessing
import time
from ai_gateway.api.main import app as gateway_app
from scan_orchestrator.api.main import app as orchestrator_app


def run_gateway():
    uvicorn.run(gateway_app, host="127.0.0.1", port=8001, log_level="warning")


def run_orchestrator():
    uvicorn.run(orchestrator_app, host="127.0.0.1", port=8000, log_level="warning")


async def verify_phase_1():
    print("Iniciando verificacao ponta a ponta da Fase 1...")
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=5.0) as client:
        # 1. Service health check
        health_orc = await client.get("/health")
        assert health_orc.status_code == 200
        print("[OK] Health check do scan-orchestrator OK")

        async with httpx.AsyncClient(base_url="http://127.0.0.1:8001", timeout=5.0) as gw_client:
            health_gw = await gw_client.get("/health")
            assert health_gw.status_code == 200
            print("[OK] Health check do ai-gateway OK")

        # 2. JSON test: scam message with emotional coercion and CPF
        payload_scam = {
            "content": "Oi mae, troquei de numero. Me faz um pix urgente no CPF 123.456.789-00?"
        }
        res_scam = await client.post("/api/v1/scans", json=payload_scam)
        assert res_scam.status_code == 200
        data_scam = res_scam.json()
        print("[OK] Resposta JSON de Golpe recebida:")
        print(f"  - Threat Level: {data_scam['threat_level']}")
        print(f"  - Verdict message: {data_scam['verdict_message']}")
        print(f"  - Latencia de triagem: {data_scam['details']['latency_breakdown']['triage']} ms")
        assert data_scam["threat_level"] == "GOLPE"
        assert data_scam["verdict_message"] == "scam_affective_coercion"

        # 3. SSE streaming test: safe message
        payload_safe = {
            "content": "Bom dia, nossa reuniao de alinhamento sera as 15h."
        }
        print("[OK] Testando streaming SSE (Server-Sent Events)...")
        async with client.stream("POST", "/api/v1/scans/stream", json=payload_safe) as stream:
            assert stream.status_code == 200
            assert "text/event-stream" in stream.headers["content-type"]
            event_count = 0
            async for line in stream.aiter_lines():
                if line.startswith("event:"):
                    event_count += 1
                    print(f"  [SSE Event] {line}")
                elif line.startswith("data:"):
                    print(f"  [SSE Data]  {line[:70]}...")
            assert event_count >= 2
            print("[OK] Streaming SSE consumido com sucesso!")

        # 4. Phase 1 ethics lock test: bare URL
        res_url = await client.post("/api/v1/scans", json={"content": "https://itau-seguro.com.br"})
        assert res_url.status_code == 422
        print("[OK] Trava etica de canal nao suportado (URL pura na Fase 1) validada com HTTP 422.")

    print("\n=======================================================")
    print("TODAS AS VALIDACOES DA FASE 1 PASSARAM COM 100% DE SUCESSO!")
    print("=======================================================")


if __name__ == "__main__":
    p_gw = multiprocessing.Process(target=run_gateway, daemon=True)
    p_orc = multiprocessing.Process(target=run_orchestrator, daemon=True)

    p_gw.start()
    p_orc.start()
    time.sleep(2)  # Wait for the servers to start

    try:
        asyncio.run(verify_phase_1())
    finally:
        p_gw.terminate()
        p_orc.terminate()
