import io
import base64
import pytest
from PIL import Image
from image_extractor.domain.image_validator import validate_and_load_image
from image_extractor.domain.hasher import compute_hashes, hamming_distance
from image_extractor.domain.extractor_service import ImageExtractorService
from image_extractor.domain.ocr_reader import FakeOcrEngine, FakeQrReader


def create_sample_image(color="blue", size=(100, 100), fmt="PNG") -> str:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_validate_and_load_image_rejects_corrupted_data():
    with pytest.raises(ValueError, match="Dados de imagem inválidos ou corrompidos"):
        validate_and_load_image("invalid_base64_content!#%")


def test_validate_and_load_image_accepts_valid_image():
    b64 = create_sample_image()
    img = validate_and_load_image(b64)
    assert img.size == (100, 100)


def test_validate_and_load_image_resizes_huge_dimensions():
    # An image larger than 1920x1080 is resized proportionally
    b64 = create_sample_image(size=(3000, 1500))
    img = validate_and_load_image(b64)
    assert img.width <= 1920
    assert img.height <= 1080


def test_compute_hashes_and_hamming_distance():
    b64 = create_sample_image(color="red")
    img = validate_and_load_image(b64)
    sha, phash = compute_hashes(b64, img)

    assert len(sha) == 64  # SHA-256 hex
    assert len(phash) == 16  # pHash hex (64 bits)

    # Two identical images must have a Hamming distance of 0
    dist = hamming_distance(phash, phash)
    assert dist == 0


def test_extractor_service_aggregates_qr_ocr_and_urls():
    b64 = create_sample_image()
    ocr = FakeOcrEngine(text="Acesse agora https://banco-promo.com e resgate seu cupom.")
    qr = FakeQrReader(qr_codes=["https://qr-promo.com/pix"])

    service = ImageExtractorService(ocr_engine=ocr, qr_reader=qr)
    result = service.extract(b64)

    assert "https://banco-promo.com" in result.extracted_text
    assert "https://qr-promo.com/pix" in result.qr_codes
    assert "https://banco-promo.com" in result.urls_found
    assert "https://qr-promo.com/pix" in result.urls_found
    assert len(result.sha256) == 64
    assert len(result.phash) == 16
