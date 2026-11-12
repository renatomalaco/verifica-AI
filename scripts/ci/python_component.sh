#!/usr/bin/env bash
# One cell of the Jenkins matrix: lint, SAST and tests with an 80% coverage gate for a single
# component (packages/<name> or services/<name>).
# Locally: bash scripts/ci/python_component.sh services/url-inspector
set -euo pipefail

component="${1:?usage: python_component.sh <packages/name|services/name>}"
name="$(basename "$component")"
mkdir -p reports

echo "--- flake8 ($component)"
uv run --no-sync flake8 "$component"

echo "--- bandit ($component)"
uv run --no-sync bandit -r "$component" -x "*/tests/*" -ll -q

echo "--- pytest + coverage >= 80% ($component)"
# Own coverage file per cell: the matrix cells share one workspace and run in parallel.
COVERAGE_FILE="reports/.coverage.$name" uv run --no-sync pytest "$component" \
  -m "not integration" -q -p no:cacheprovider \
  --cov="$component" --cov-report=term-missing:skip-covered --cov-fail-under=80 \
  --junitxml="reports/junit-$name.xml"
