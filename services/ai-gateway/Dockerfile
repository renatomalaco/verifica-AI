FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/huggingface

# The gateway sits on an internal network: the SigLIP weights are baked in at build time.
# Pinned to a Hub commit, the same one as SIGLIP_REVISION in settings.py.
ARG SIGLIP_MODEL=google/siglip-base-patch16-224
ARG SIGLIP_REVISION=7fd15f0689c79d79e38b1c2e2e2370a7bf2761ed
ENV SIGLIP_MODEL=${SIGLIP_MODEL} \n    SIGLIP_REVISION=${SIGLIP_REVISION}

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY packages/ ./packages/
COPY services/ai-gateway/ ./services/ai-gateway/

# CPU-only torch first, so the extra does not pull the multi-GB CUDA build from PyPI.
RUN uv pip install --system --index-url https://download.pytorch.org/whl/cpu "torch>=2.5" \
    && uv pip install --system -e ./packages/contracts -e ./packages/observability -e "./services/ai-gateway[siglip]" \
    && python -c "import os; from transformers import AutoImageProcessor, SiglipModel; m, r = os.environ['SIGLIP_MODEL'], os.environ['SIGLIP_REVISION']; AutoImageProcessor.from_pretrained(m, revision=r); SiglipModel.from_pretrained(m, revision=r)"

ENV HF_HUB_OFFLINE=1

EXPOSE 8001

CMD ["uvicorn", "ai_gateway.api.main:app", "--host", "0.0.0.0", "--port", "8001"]
