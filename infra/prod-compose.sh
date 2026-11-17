#!/usr/bin/env bash
# Runs docker compose for production with the secrets read from Google Secret Manager.
# The secrets only live in this process's environment: nothing is written to disk.
# Non-secret settings (PUBLIC_DOMAIN, AI_PROVIDER...) stay in the repository's .env on the VM.
#
# Usage, on the VM, from the repository root:
#   ./infra/prod-compose.sh up -d --build
#   ./infra/prod-compose.sh logs -f scan-orchestrator
set -euo pipefail

SECRETS=(
  POSTGRES_PASSWORD
  AUTH_JWT_PRIVATE_KEY
  AUTH_JWT_PUBLIC_KEY
  GRAFANA_ADMIN_PASSWORD
  DEVICE_TOKEN_SECRET
  GEMINI_API_KEY
)

if [ "$#" -eq 0 ]; then
  echo "usage: $0 <docker compose command>   (e.g. up -d --build)" >&2
  exit 2
fi

cd "$(dirname "$0")/.."

for name in "${SECRETS[@]}"; do
  if ! value="$(gcloud secrets versions access latest --secret="$name" --quiet)"; then
    echo "Could not read secret '$name' from Secret Manager (see infra/DEPLOY.md, step 3)." >&2
    exit 1
  fi
  export "$name=$value"
done

exec docker compose -f infra/docker-compose.prod.yml --env-file .env "$@"
