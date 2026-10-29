import os
import asyncio
import io
import base64
import multiprocessing
import time
import httpx
from service_wait import wait_until_healthy
import uvicorn
from PIL import Image
from ai_gateway.api.main import app as gateway_app
from url_inspector.api.main import app as inspector_app
from image_extractor.api.main import app as image_app
from scan_orchestrator.api.main import app as orchestrator_app

# In-memory scans unless DATABASE_URL is set explicitly; the developer .env may point to a stopped Postgres.
os.environ.setdefault("DATABASE_URL", "")


def create_test_image_b64() -> str:
    img = Image.new("RGB", (120, 60), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def run_gateway():
    uvicorn.run(gateway_app, host="127.0.0.1", port=8001, log_level="warning")


def run_inspector():
    uvicorn.run(inspector_app, host="127.0.0.1", port=8002, log_level="warning")


def run_image_extractor():
    uvicorn.run(image_app, host="127.0.0.1", port=8003, log_level="warning")


def run_orchestrator():
    uvicorn.run(orchestrator_app, host="127.0.0.1", port=8000, log_level="warning")


async def verify_phase_3():
    print("Iniciando verificacao ponta a ponta da Fase 3 (Canal Imagem, OCR, QR, pHash)...")

    # 1. Health checks of the 4 microservices
    async with httpx.AsyncClient(timeout=5.0) as client:
        r_gw = await client.get("http://127.0.0.1:8001/health")
        assert r_gw.status_code == 200
        print("[OK] ai-gateway (porta 8001) respondendo.")

        r_ins = await client.get("http://127.0.0.1:8002/health")
        assert r_ins.status_code == 200
        print("[OK] url-inspector (porta 8002) respondendo.")

        r_img = await client.get("http://127.0.0.1:8003/health")
        assert r_img.status_code == 200
        print("[OK] image-extractor (porta 8003) respondendo.")

        r_orc = await client.get("http://127.0.0.1:8000/health")
        assert r_orc.status_code == 200
        print("[OK] scan-orchestrator (porta 8000) respondendo.")

    # 2. Direct test against the image-extractor microservice
    sample_b64 = create_test_image_b64()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp_ext = await client.post("http://127.0.0.1:8003/extract", json={"image_b64": sample_b64})
        assert resp_ext.status_code == 200
        ext_data = resp_ext.json()
        assert len(ext_data["sha256"]) == 64
        assert len(ext_data["phash"]) == 16
        print("[OK] image-extractor extraiu com sucesso:")
        print(f"  - SHA-256: {ext_data['sha256'][:16]}...")
        print(f"  - pHash Perceptual: {ext_data['phash']}")

    # 3. Image channel analysis via scan-orchestrator
    async with httpx.AsyncClient(timeout=15.0) as client:
        scan_payload = {"image_b64": sample_b64}
        r_scan = await client.post("http://127.0.0.1:8000/api/v1/scans", json=scan_payload)
        assert r_scan.status_code == 200
        data = r_scan.json()
        assert data["details"]["channel"] == "imagem"
        print("[OK] scan-orchestrator processou evidência visual (Canal Imagem):")
        print(f"  - Threat Level: {data['threat_level']}")
        print(f"  - Channel: {data['details']['channel']}")
        print(f"  - Deciding Stage: {data['details']['deciding_stage']}")
        print(f"  - Verdict message: {data['verdict_message']}")

    # 4. SSE streaming for the image channel
    async with httpx.AsyncClient(timeout=15.0) as client:
        print("[OK] Testando SSE para Canal Imagem...")
        async with client.stream("POST", "http://127.0.0.1:8000/api/v1/scans/stream", json={"image_b64": sample_b64}) as stream:
            assert stream.status_code == 200
            events_received = 0
            async for line in stream.aiter_lines():
                if line.startswith("event:"):
                    events_received += 1
                    print(f"  [SSE Event] {line}")
            assert events_received >= 2
            print("[OK] Streaming SSE de Canal Imagem validado com sucesso!")

    print("\n=======================================================")
    print("TODAS AS VALIDACOES DA FASE 3 PASSARAM COM 100% DE SUCESSO!")
    print("=======================================================")


if __name__ == "__main__":
    p_gw = multiprocessing.Process(target=run_gateway, daemon=True)
    p_ins = multiprocessing.Process(target=run_inspector, daemon=True)
    p_img = multiprocessing.Process(target=run_image_extractor, daemon=True)
    p_orc = multiprocessing.Process(target=run_orchestrator, daemon=True)

    p_gw.start()
    p_ins.start()
    p_img.start()
    p_orc.start()
    wait_until_healthy([8000, 8001, 8002, 8003])

    try:
        asyncio.run(verify_phase_3())
    finally:
        p_gw.terminate()
        p_ins.terminate()
        p_img.terminate()
        p_orc.terminate()
