FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/ai-gateway/ ./services/ai-gateway/

RUN uv pip install --system -e ./packages/contracts -e ./services/ai-gateway

EXPOSE 8001

CMD ["uvicorn", "ai_gateway.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
