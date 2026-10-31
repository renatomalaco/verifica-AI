FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/huggingface

# The gateway sits on an internal network: the SigLIP weights are baked in at build time.
ARG SIGLIP_MODEL=google/siglip-base-patch16-224
ENV SIGLIP_MODEL=${SIGLIP_MODEL}

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/ai-gateway/ ./services/ai-gateway/

# CPU-only torch first, so the extra does not pull the multi-GB CUDA build from PyPI.
RUN uv pip install --system --index-url https://download.pytorch.org/whl/cpu "torch>=2.5" \
    && uv pip install --system -e ./packages/contracts -e "./services/ai-gateway[siglip]" \
    && python -c "import os; from transformers import AutoImageProcessor, SiglipModel; m = os.environ['SIGLIP_MODEL']; AutoImageProcessor.from_pretrained(m); SiglipModel.from_pretrained(m)"

ENV HF_HUB_OFFLINE=1

EXPOSE 8001

CMD ["uvicorn", "ai_gateway.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
