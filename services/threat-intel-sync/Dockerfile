FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/threat-intel-sync/ ./services/threat-intel-sync/

RUN uv pip install --system -e ./packages/contracts -e ./services/threat-intel-sync

CMD ["python", "-m", "threat_intel_sync.worker"]
