import base64
import hashlib
import io

import pytest
from PIL import Image

from image_extractor.domain.hasher import compute_hashes
from image_extractor.domain.image_validator import MAX_BYTES, decode_base64, load_image


def encoded(img: Image.Image, fmt: str, **save_args) -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, format=fmt, **save_args)
    return buffer.getvalue()


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_accepts_the_three_screenshot_formats(fmt):
    assert load_image(encoded(Image.new("RGB", (50, 40), "blue"), fmt)).size == (50, 40)


@pytest.mark.parametrize("fmt", ["GIF", "BMP"])
def test_rejects_formats_outside_the_allow_list_even_if_pillow_reads_them(fmt):
    with pytest.raises(ValueError, match="format"):
        load_image(encoded(Image.new("RGB", (10, 10)), fmt))


def test_rejects_a_pdf_renamed_as_image():
    with pytest.raises(ValueError, match="format"):
        load_image(b"%PDF-1.7\n" + b"0" * 100)


def test_size_limit_is_checked_on_decoded_bytes_before_decoding():
    oversized = b"\x89PNG\r\n\x1a\n" + b"0" * MAX_BYTES
    with pytest.raises(ValueError, match="8MB"):
        load_image(oversized)


def test_rejects_images_above_40_megapixels_without_decoding_them():
    huge = encoded(Image.new("1", (7000, 6000)), "PNG")  # 42 MP, tiny file: a decompression bomb
    with pytest.raises(ValueError, match="megapixels"):
        load_image(huge)


def test_applies_phone_rotation_and_drops_exif():
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90 degrees
    exif[0x010F] = "Celular"  # camera maker: personal metadata that must not travel on
    raw = encoded(Image.new("RGB", (200, 100), "white"), "JPEG", exif=exif.tobytes())

    img = load_image(raw)

    assert img.size == (100, 200)
    assert "exif" not in img.info
    assert not img.getexif()


def test_large_screenshots_are_downscaled_for_ocr():
    img = load_image(encoded(Image.new("RGB", (3000, 1500)), "PNG"))
    assert img.width <= 1920 and img.height <= 1080


def test_base64_errors_are_reported_as_invalid_image():
    with pytest.raises(ValueError, match="Invalid or corrupted image data"):
        decode_base64("nao e base64!#%")


def test_sha256_is_computed_over_the_image_bytes_not_the_base64_text():
    raw = encoded(Image.new("RGB", (20, 20), "red"), "PNG")
    sha256, phash = compute_hashes(raw, load_image(raw))
    assert sha256 == hashlib.sha256(raw).hexdigest()
    assert sha256 != hashlib.sha256(base64.b64encode(raw)).hexdigest()
    assert len(phash) == 16


def test_whatsapp_recompression_stays_within_the_cache_tolerance():
    # Acceptance (R3): the same screenshot re-sent as JPEG quality 60 must hit the perceptual cache.
    from PIL import ImageDraw

    from image_extractor.domain.hasher import hamming_distance

    screenshot = Image.new("RGB", (720, 1280), "white")
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((0, 0, 720, 140), fill=(18, 140, 126))
    for line in range(14):
        draw.text((40, 200 + line * 70), f"Mensagem {line}: seu Pix foi bloqueado, regularize agora", fill="black")
    draw.rectangle((40, 1150, 680, 1230), fill=(37, 211, 102))

    original = encoded(screenshot, "PNG")
    resent = encoded(load_image(original), "JPEG", quality=60)

    _, phash_original = compute_hashes(original, load_image(original))
    _, phash_resent = compute_hashes(resent, load_image(resent))
    assert hamming_distance(phash_original, phash_resent) <= 4
