FROM mcr.microsoft.com/playwright/python:v1.47.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/url-inspector/ ./services/url-inspector/

RUN uv pip install --system -e ./packages/contracts -e ./services/url-inspector
RUN playwright install chromium --with-deps

EXPOSE 8002

CMD ["uvicorn", "url_inspector.api.main:app", "--host", "0.0.0.0", "--port", "8002"]
