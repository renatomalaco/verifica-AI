import asyncio
import base64
import io
import multiprocessing
import time
import httpx
import uvicorn
from PIL import Image
from ai_gateway.api.main import app as gateway_app, get_visual_embedder
from ai_gateway.domain.visual_embedder import FakeVisualEmbedder
from url_inspector.api.main import app as inspector_app, get_browser_driver
from url_inspector.domain.browser_driver import FakeBrowserDriver
from contracts import InspectResult
from image_extractor.api.main import app as image_app
from scan_orchestrator.api.main import app as orchestrator_app


def create_test_image_b64() -> str:
    img = Image.new("RGB", (100, 50), color="yellow")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def run_gateway():
    # Inject a vector matching the protected brand "Banco do Brasil" into the default catalog
    bb_vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    gateway_app.dependency_overrides[get_visual_embedder] = lambda: FakeVisualEmbedder(default_embedding=bb_vector)
    uvicorn.run(gateway_app, host="127.0.0.1", port=8001, log_level="warning")


def run_inspector():
    # Set up a simulated screenshot for the fake domain
    sample_b64 = create_test_image_b64()
    driver = FakeBrowserDriver(
        default_result=InspectResult(
            dom_text="Página de login do banco",
            final_url="https://bb-recadastro-falso.xyz/login",
            screenshot_b64=sample_b64,
            has_password_field=True,
            is_blocked=False,
        )
    )
    inspector_app.dependency_overrides[get_browser_driver] = lambda: driver
    uvicorn.run(inspector_app, host="127.0.0.1", port=8002, log_level="warning")


def run_image_extractor():
    uvicorn.run(image_app, host="127.0.0.1", port=8003, log_level="warning")


def run_orchestrator():
    uvicorn.run(orchestrator_app, host="127.0.0.1", port=8000, log_level="warning")


async def verify_phase_4():
    print("Iniciando verificacao ponta a ponta da Fase 4 (Visual RAG & Brand Spoofing)...")

    # 1. Health checks of the 4 services
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

    # 2. Direct Brand Matcher test on ai-gateway
    sample_b64 = create_test_image_b64()
    async with httpx.AsyncClient(timeout=10.0) as client:
        # A) Unofficial domain -> spoofing detected
        payload_fake = {
            "image_b64": sample_b64,
            "current_domain": "bb-recadastro-falso.xyz",
        }
        res_fake = await client.post("http://127.0.0.1:8001/v1/brand-match", json=payload_fake)
        assert res_fake.status_code == 200
        data_fake = res_fake.json()
        assert data_fake["matched_brand"] == "Banco do Brasil"
        assert data_fake["is_spoofing"] is True
        print("[OK] ai-gateway detectou brand spoofing no domínio 'bb-recadastro-falso.xyz' (similaridade: 1.0).")

        # B) Official domain -> not spoofing
        payload_legit = {
            "image_b64": sample_b64,
            "current_domain": "bb.com.br",
        }
        res_legit = await client.post("http://127.0.0.1:8001/v1/brand-match", json=payload_legit)
        assert res_legit.status_code == 200
        data_legit = res_legit.json()
        assert data_legit["is_spoofing"] is False
        print("[OK] ai-gateway autorizou domínio oficial 'bb.com.br' sem falso positivo de spoofing.")

    # 3. Full cascade analysis with Visual RAG on scan-orchestrator
    async with httpx.AsyncClient(timeout=15.0) as client:
        scan_payload = {"content": "https://bb-recadastro-falso.xyz/login"}
        r_scan = await client.post("http://127.0.0.1:8000/api/v1/scans", json=scan_payload)
        assert r_scan.status_code == 200
        scan_data = r_scan.json()
        assert scan_data["threat_level"] == "GOLPE"
        assert scan_data["details"]["deciding_stage"] == "visual_rag_brand_spoofing"
        assert scan_data["details"]["category"] == "brand_spoofing"
        assert scan_data["details"]["scores"]["brand_spoofing"] == 1.0
        print("[OK] scan-orchestrator short-circuitou no Visual RAG com veredito GOLPE:")
        print(f"  - Threat Level: {scan_data['threat_level']}")
        print(f"  - Deciding Stage: {scan_data['details']['deciding_stage']}")
        print(f"  - Categoria: {scan_data['details']['category']}")
        print(f"  - Verdict message: {scan_data['verdict_message']}")

    # 4. SSE streaming of the cascade with Visual RAG
    async with httpx.AsyncClient(timeout=15.0) as client:
        print("[OK] Testando SSE para Visual RAG...")
        async with client.stream("POST", "http://127.0.0.1:8000/api/v1/scans/stream", json=scan_payload) as stream:
            assert stream.status_code == 200
            events_received = 0
            async for line in stream.aiter_lines():
                if line.startswith("event:"):
                    events_received += 1
                    print(f"  [SSE Event] {line}")
            assert events_received >= 2
            print("[OK] Streaming SSE de Visual RAG validado com sucesso!")

    print("\n=======================================================")
    print("TODAS AS VALIDACOES DA FASE 4 PASSARAM COM 100% DE SUCESSO!")
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
    time.sleep(2)

    try:
        asyncio.run(verify_phase_4())
    finally:
        p_gw.terminate()
        p_ins.terminate()
        p_img.terminate()
        p_orc.terminate()
