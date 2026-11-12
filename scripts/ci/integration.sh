#!/usr/bin/env bash
# Integration stage: Postgres (pgvector) and Redis from docker compose, the real migrations,
# then `pytest -m integration`. Same commands in Jenkins and on a developer machine.
# Needs POSTGRES_PASSWORD in the environment (Jenkins injects it from its credential store).
set -euo pipefail

: "${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD (Jenkins credential verifica-postgres-password)}"
export CI_POSTGRES_PORT="${CI_POSTGRES_PORT:-55432}"
export CI_REDIS_PORT="${CI_REDIS_PORT:-56379}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-verifica-ci}"

compose() {
  docker compose -f infra/docker-compose.yml -f infra/docker-compose.ci.yml "$@"
}
trap 'compose down --volumes --remove-orphans' EXIT

compose up --detach --wait

database_url="postgresql+asyncpg://verifica:${POSTGRES_PASSWORD}@127.0.0.1:${CI_POSTGRES_PORT}/verifica_db"
(cd services/scan-orchestrator && DATABASE_URL="$database_url" uv run --no-sync alembic upgrade head)

# Without TEST_DATABASE_URL the integration tests skip themselves; here they must run.
TEST_DATABASE_URL="$database_url" uv run --no-sync pytest packages services -m integration \
  -q -p no:cacheprovider -rs --junitxml=reports/junit-integration.xml
