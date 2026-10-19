FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/research-runner/ ./services/research-runner/

RUN uv pip install --system -e ./packages/contracts -e ./services/research-runner

EXPOSE 8004

CMD ["uvicorn", "research_runner.api.main:app", "--host", "0.0.0.0", "--port", "8004"]
