# One Playwright version for the base image (browsers and system libraries) and the Python
# package: a newer package than the image left the driver hanging. It must match uv.lock
# (tests/test_image_playwright_version.py checks it).
ARG PLAYWRIGHT_VERSION=1.63.0
FROM mcr.microsoft.com/playwright/python:v${PLAYWRIGHT_VERSION}-noble
ARG PLAYWRIGHT_VERSION

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/url-inspector/ ./services/url-inspector/

# The browsers already come with the base image, for this same version.
RUN uv pip install --system "playwright==${PLAYWRIGHT_VERSION}" \
    -e ./packages/contracts -e ./packages/observability -e ./services/url-inspector

EXPOSE 8002

CMD ["uvicorn", "url_inspector.api.main:app", "--host", "0.0.0.0", "--port", "8002"]
