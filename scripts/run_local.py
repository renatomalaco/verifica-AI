"""Single script to start all Verifica AI microservices locally."""

import multiprocessing
import signal
import sys
import time
import uvicorn


def run_gateway():
    uvicorn.run("ai_gateway.api.main:app", host="127.0.0.1", port=8001, log_level="warning")


def run_inspector():
    uvicorn.run("url_inspector.api.main:app", host="127.0.0.1", port=8002, log_level="warning")


def run_image_extractor():
    uvicorn.run("image_extractor.api.main:app", host="127.0.0.1", port=8003, log_level="warning")


def run_orchestrator():
    uvicorn.run("scan_orchestrator.api.main:app", host="127.0.0.1", port=8000, log_level="warning")


def run_research():
    uvicorn.run("research_runner.api.main:app", host="127.0.0.1", port=8004, log_level="warning")


def main():
    print("=" * 70)
    print("   VERIFICA AI — INICIANDO STACK DE MICROSSERVICOS LOCAL")
    print("=" * 70)

    services = [
        (run_gateway, "ai-gateway", 8001),
        (run_inspector, "url-inspector", 8002),
        (run_image_extractor, "image-extractor", 8003),
        (run_orchestrator, "scan-orchestrator", 8000),
        (run_research, "research-runner", 8004),
    ]

    processes = []
    for target_fn, name, port in services:
        p = multiprocessing.Process(target=target_fn, daemon=True)
        p.start()
        processes.append((p, name, port))

    time.sleep(2.0)
    print("\n[OK] Todos os 5 microsservicos backend estao operacionais!")
    print("  -> scan-orchestrator: http://127.0.0.1:8000")
    print("  -> ai-gateway:        http://127.0.0.1:8001")
    print("  -> url-inspector:     http://127.0.0.1:8002")
    print("  -> image-extractor:   http://127.0.0.1:8003")
    print("  -> research-runner:   http://127.0.0.1:8004")
    print("=" * 70)
    print("Pressione CTRL+C para encerrar todos os servicos.\n")

    def shutdown(signum, frame):
        print("\n[*] Encerrando microsservicos...")
        for p, name, _ in processes:
            if p.is_alive():
                p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
