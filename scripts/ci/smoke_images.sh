#!/usr/bin/env bash
# Imports what each production image really runs, inside the built image. The unit tests run in a
# shared workspace venv, where a dependency missing from one service's pyproject is still
# installed by another; only the image shows it (redis in the orchestrator, pytesseract and pyzbar
# in the image-extractor, whose OCR swallowed the ImportError and failed silently).
# Needs the same variables as `docker compose -f infra/docker-compose.prod.yml build`: the CI
# passes them in the environment. On the VM they only exist through prod-compose.sh, so run:
#   SMOKE_COMPOSE="bash infra/prod-compose.sh" bash scripts/ci/smoke_images.sh
set -euo pipefail

read -ra compose <<< "${SMOKE_COMPOSE:-docker compose -f infra/docker-compose.prod.yml}"

check() {
  local service="$1" code="$2"
  echo "--- $service"
  "${compose[@]}" run --rm --no-deps --entrypoint python "$service" -c "$code"
}

check scan-orchestrator "import scan_orchestrator.api.main"
check research-runner "import research_runner.api.main"
check ai-gateway "import ai_gateway.api.main, torch, transformers"
check url-inspector "import url_inspector.api.main"
check egress "import url_inspector.egress"
check threat-intel-sync "import threat_intel_sync.worker"
check image-extractor "import image_extractor.api.main, pytesseract, pyzbar.pyzbar; print('tesseract', pytesseract.get_tesseract_version())"

echo "All production images import what they run."
