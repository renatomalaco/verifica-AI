FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/scan-orchestrator/ ./services/scan-orchestrator/

RUN uv pip install --system -e ./packages/contracts -e ./services/scan-orchestrator

EXPOSE 8000

CMD ["uvicorn", "scan_orchestrator.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
