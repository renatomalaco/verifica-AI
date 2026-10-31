import base64
import io
import math

import pytest
from PIL import Image

from ai_gateway.infrastructure.fakes import cosine_similarity
from ai_gateway.infrastructure.siglip_embedder import SiglipEmbedder, decode_image, unit_vector


def _jpeg_b64(color: tuple[int, int, int], quality: int = 90) -> str:
    image = Image.new("RGB", (320, 200), color)
    image.paste((255, 255, 255), (40, 40, 160, 120))  # a crude "logo" block
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode()


def test_unit_vector_normalizes_the_model_output():
    vector = unit_vector([3.0, 4.0], dimension=2)
    assert vector == pytest.approx([0.6, 0.8])


def test_unit_vector_rejects_a_model_of_another_dimension():
    # A swapped model (e.g. SigLIP large, 1024) would silently break every pgvector query.
    with pytest.raises(ValueError, match="dimension"):
        unit_vector([1.0] * 1024, dimension=768)


def test_decode_image_returns_rgb():
    image = decode_image(_jpeg_b64((10, 80, 120)))
    assert image.mode == "RGB"
    assert image.size == (320, 200)


def test_decode_image_rejects_what_is_not_an_image():
    with pytest.raises(ValueError):
        decode_image(base64.b64encode(b"not an image").decode())


@pytest.mark.integration
async def test_real_siglip_gives_768_unit_vectors_robust_to_recompression():
    pytest.importorskip("transformers", reason="install the ai-gateway 'siglip' extra")
    embedder = SiglipEmbedder(model_name="google/siglip-base-patch16-224", dimension=768)

    original = await embedder.embed_image(_jpeg_b64((10, 80, 120)))
    recompressed = await embedder.embed_image(_jpeg_b64((10, 80, 120), quality=60))
    other = await embedder.embed_image(_jpeg_b64((230, 30, 30)))

    assert len(original) == 768
    assert math.sqrt(sum(v * v for v in original)) == pytest.approx(1.0, abs=1e-4)
    assert cosine_similarity(original, recompressed) > 0.95
    assert cosine_similarity(original, recompressed) > cosine_similarity(original, other)
