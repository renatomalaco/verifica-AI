import asyncio
import json
import multiprocessing
import os
import time
import httpx
import uvicorn
from ai_gateway.api.main import app as gateway_app
from url_inspector.api.main import app as inspector_app
from image_extractor.api.main import app as image_app
from scan_orchestrator.api.main import app as orchestrator_app


def run_gateway():
    uvicorn.run(gateway_app, host="127.0.0.1", port=8001, log_level="warning")


def run_inspector():
    uvicorn.run(inspector_app, host="127.0.0.1", port=8002, log_level="warning")


def run_image_extractor():
    uvicorn.run(image_app, host="127.0.0.1", port=8003, log_level="warning")


def run_orchestrator():
    uvicorn.run(orchestrator_app, host="127.0.0.1", port=8000, log_level="warning")


async def verify_phase_5():
    print("=" * 70)
    print("Iniciando validacao ponta a ponta da Fase 5: Frontend Acessivel & PWA")
    print("=" * 70)

    # 1. Validate the integrity of the frontend build artifacts
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
    index_html = os.path.join(dist_dir, "index.html")
    assert os.path.exists(index_html), f"dist/index.html nao encontrado em {dist_dir}"
    with open(index_html, "r", encoding="utf-8") as f:
        html_content = f.read()
    assert "Verifica AI" in html_content, "index.html nao contem o titulo do Verifica AI"
    assert "manifest.json" in html_content, "index.html nao referencia o manifest.json"
    print("[OK] 1. Artefatos de producao do Vite/React compilados com sucesso.")

    # 2. Validate the PWA manifest and Web Share Target API
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "web", "public", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data.get("display") == "standalone", "PWA display deve ser standalone"
    assert "share_target" in manifest_data, "PWA manifest deve conter configuracao de share_target"
    share_target = manifest_data["share_target"]
    assert "params" in share_target and "text" in share_target["params"], "share_target params deve suportar text"
    assert "url" in share_target["params"], "share_target params deve suportar url"
    print("[OK] 2. PWA Manifest e Web Share Target configurados e validados.")

    # 3. Validate the service worker
    sw_path = os.path.join(os.path.dirname(__file__), "..", "web", "public", "sw.js")
    with open(sw_path, "r", encoding="utf-8") as f:
        sw_content = f.read()
    assert "caches.open" in sw_content and "fetch" in sw_content, "Service Worker invalido"
    print("[OK] 3. Service Worker para suporte offline validado.")

    # 4. Start the 4 backend services and test frontend communication with SSE streaming and CORS
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Wait for the services to come up
        for port, name in [
            (8001, "ai-gateway"),
            (8002, "url-inspector"),
            (8003, "image-extractor"),
            (8000, "scan-orchestrator"),
        ]:
            ready = False
            for _ in range(30):
                try:
                    res = await client.get(f"http://127.0.0.1:{port}/health")
                    if res.status_code == 200:
                        ready = True
                        break
                except httpx.ConnectError:
                    await asyncio.sleep(0.2)
            assert ready, f"Servico {name} nao respondeu na porta {port}"

        print("[OK] 4. Todos os 4 microservicos estao saudaveis e operacionais.")

        # 5. Test CORS preflight for browser calls
        cors_headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
        res_options = await client.options("http://127.0.0.1:8000/api/v1/scans/stream", headers=cors_headers)
        assert res_options.status_code == 200, f"Falha no CORS OPTIONS preflight: {res_options.status_code}"
        assert "access-control-allow-origin" in res_options.headers, "CORS headers ausentes no orchestrator"
        print("[OK] 5. CORS preflight validado para requisicoes do navegador (Vite dev server).")

        # 6. Test real-time SSE streaming consumed by the frontend
        stream_payload = {"content": "Urgente: Banco do Brasil informa bloqueio de conta. Acesse https://bb.com.br"}
        headers = {"Origin": "http://localhost:5173", "Content-Type": "application/json"}
        async with client.stream(
            "POST",
            "http://127.0.0.1:8000/api/v1/scans/stream",
            json=stream_payload,
            headers=headers,
            timeout=15.0,
        ) as response:
            assert response.status_code == 200, f"Status SSE stream: {response.status_code}"
            assert "text/event-stream" in response.headers.get("content-type", "")

            events = []
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    raw_data = line.replace("data:", "").strip()
                    try:
                        parsed = json.loads(raw_data)
                        events.append(parsed)
                    except json.JSONDecodeError:
                        pass

            assert len(events) >= 1, "Nenhum evento recebido no SSE stream"
            verdict_events = [e for e in events if "threat_level" in e]
            assert len(verdict_events) == 1, "Veredito final ausente no SSE stream"
            verdict = verdict_events[0]
            print(f"[OK] 6. Streaming SSE consumido com sucesso. Veredito final: {verdict['threat_level']}")
            print(f"     Explicacao: {verdict['verdict_plain']}")
            print(f"     Orientacao: {verdict['action_advice']}")

    print("=" * 70)
    print("FASE 5 VALIDADA COM SUCESSO INTEGRAL (100% OK)!")
    print("=" * 70)


def main():
    procs = [
        multiprocessing.Process(target=run_gateway, daemon=True),
        multiprocessing.Process(target=run_inspector, daemon=True),
        multiprocessing.Process(target=run_image_extractor, daemon=True),
        multiprocessing.Process(target=run_orchestrator, daemon=True),
    ]

    for p in procs:
        p.start()

    time.sleep(1.0)

    try:
        asyncio.run(verify_phase_5())
    finally:
        for p in procs:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1.0)


if __name__ == "__main__":
    main()
