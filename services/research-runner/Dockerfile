FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
# The study runs the orchestrator and gateway code in process.
COPY services/ai-gateway/ ./services/ai-gateway/
COPY services/scan-orchestrator/ ./services/scan-orchestrator/
COPY services/research-runner/ ./services/research-runner/

RUN uv pip install --system -e ./packages/contracts -e ./services/ai-gateway -e ./services/scan-orchestrator -e ./services/research-runner

EXPOSE 8004

CMD ["uvicorn", "research_runner.api.main:app", "--host", "0.0.0.0", "--port", "8004"]
