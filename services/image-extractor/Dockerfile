FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/image-extractor/ ./services/image-extractor/

RUN uv pip install --system -e ./packages/contracts -e ./services/image-extractor

EXPOSE 8003

CMD ["uvicorn", "image_extractor.api.main:app", "--host", "0.0.0.0", "--port", "8003"]
