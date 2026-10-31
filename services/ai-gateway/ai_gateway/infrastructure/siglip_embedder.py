import asyncio
import base64
import binascii
import io
import math
import threading

from PIL import Image, UnidentifiedImageError

_MAX_PIXELS = 40_000_000  # same ceiling as the image-extractor (decompression bombs)


class SiglipEmbedder:
    """
    Local SigLIP image embeddings (CPU is enough for one image per scan). The published
    checkpoint is the joint image-text model, so it loads whole; only the image side is used.
    torch and transformers come from the optional 'siglip' extra.
    """

    def __init__(self, model_name: str, dimension: int) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._lock = threading.Lock()
        self._model = None
        self._processor = None

    async def embed_image(self, image_b64: str) -> list[float]:
        image = decode_image(image_b64)
        return await asyncio.to_thread(self._embed, image)

    def _embed(self, image: Image.Image) -> list[float]:
        import torch

        model, processor = self._load()
        with torch.inference_mode():
            inputs = processor(images=image, return_tensors="pt")
            features = model.get_image_features(**inputs)[0]
        return unit_vector(features.tolist(), self._dimension)

    def _load(self):
        with self._lock:
            if self._model is None:
                try:
                    from transformers import AutoImageProcessor, SiglipModel
                except ImportError as exc:
                    raise RuntimeError("SigLIP needs the ai-gateway 'siglip' extra (torch, transformers)") from exc
                self._processor = AutoImageProcessor.from_pretrained(self._model_name)
                self._model = SiglipModel.from_pretrained(self._model_name).eval()
        return self._model, self._processor


def decode_image(image_b64: str) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(base64.b64decode(image_b64, validate=True)))
    except (binascii.Error, UnidentifiedImageError) as exc:
        raise ValueError("the payload is not a decodable image") from exc
    if image.width * image.height > _MAX_PIXELS:
        raise ValueError("image above the pixel limit")
    return image.convert("RGB")


def unit_vector(values: list[float], dimension: int) -> list[float]:
    if len(values) != dimension:
        raise ValueError(f"Embedding dimension {len(values)} does not match the catalog dimension {dimension}")
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]
