import base64
import io

from PIL import Image

from image_extractor.domain.extractor_service import ImageExtractorService
from image_extractor.domain.hasher import compute_hashes, hamming_distance
from image_extractor.domain.image_validator import load_image
from image_extractor.domain.ocr_reader import OcrResult, read_text
from image_extractor.infrastructure.fakes import FakeOcrEngine, FakeQrReader


def create_sample_image(color="blue", size=(100, 100), fmt="PNG", **save_args) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=color).save(buffer, format=fmt, **save_args)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_identical_images_have_hamming_distance_zero():
    raw = base64.b64decode(create_sample_image(color="red"))
    _, phash = compute_hashes(raw, load_image(raw))
    assert hamming_distance(phash, phash) == 0


def test_extractor_service_aggregates_qr_ocr_and_urls():
    ocr = FakeOcrEngine(OcrResult("Acesse agora https://banco-promo.com e resgate seu cupom.", confidence=91.0))
    qr = FakeQrReader(qr_codes=["https://qr-promo.com/pix"])

    result = ImageExtractorService(ocr_engine=ocr, qr_reader=qr).extract(create_sample_image())

    assert "https://banco-promo.com" in result.urls_found
    assert "https://qr-promo.com/pix" in result.urls_found
    assert result.ocr_confidence == 91.0
    assert len(result.sha256) == 64
    assert len(result.phash) == 16


def test_extractor_returns_a_clean_copy_without_metadata_for_visual_rag():
    exif = Image.Exif()
    exif[0x010F] = "Celular"
    service = ImageExtractorService(ocr_engine=FakeOcrEngine(OcrResult("", None)), qr_reader=FakeQrReader())

    result = service.extract(create_sample_image(fmt="JPEG", exif=exif.tobytes()))

    clean = Image.open(io.BytesIO(base64.b64decode(result.clean_image_b64)))
    assert clean.format == "JPEG"
    assert not clean.getexif()


# --- OCR with an optional fallback engine ---

def test_confident_ocr_does_not_call_the_fallback():
    fallback = FakeOcrEngine(OcrResult("outro", 99.0))
    result = read_text(Image.new("RGB", (5, 5)), FakeOcrEngine(OcrResult("ok", 85.0)), fallback, min_confidence=60)
    assert result.text == "ok"
    assert fallback.calls == 0


def test_low_confidence_ocr_uses_the_fallback_when_it_is_configured():
    result = read_text(Image.new("RGB", (5, 5)), FakeOcrEngine(OcrResult("t3xt0", 30.0)), FakeOcrEngine(OcrResult("texto", 88.0)), 60)
    assert result == OcrResult("texto", 88.0)


def test_without_fallback_the_low_confidence_is_kept_so_the_verdict_can_hold_back():
    result = read_text(Image.new("RGB", (5, 5)), FakeOcrEngine(OcrResult("t3xt0", 30.0)), None, 60)
    assert result == OcrResult("t3xt0", 30.0)
