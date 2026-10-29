"""Untrusted image input: format by magic number, size and pixel limits, orientation and EXIF."""

import base64
import binascii
import io

from PIL import Image, ImageOps

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_WIDTH, MAX_HEIGHT = 1920, 1080

# The file name and the declared type lie; the first bytes do not.
_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
)


def decode_base64(b64_str: str) -> bytes:
    try:
        return base64.b64decode(b64_str, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid or corrupted image data: base64 decoding failed.") from exc


def load_image(raw: bytes) -> Image.Image:
    if len(raw) > MAX_BYTES:
        raise ValueError(f"Image exceeds the {MAX_BYTES // (1024 * 1024)}MB limit.")
    fmt = _sniff_format(raw)
    img = _open_within_pixel_limit(raw, fmt)
    return _normalized(img)


def _sniff_format(raw: bytes) -> str:
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "WEBP"
    for magic, fmt in _MAGIC:
        if raw.startswith(magic):
            return fmt
    raise ValueError("Unsupported image format: send a PNG, JPEG or WebP.")


def _open_within_pixel_limit(raw: bytes, fmt: str) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(raw), formats=[fmt])
    except Exception as exc:
        raise ValueError("Invalid or corrupted image data: unrecognized format.") from exc
    # The header is read lazily, so a decompression bomb is refused before any pixel is decoded.
    if img.width * img.height > MAX_PIXELS:
        raise ValueError(f"Image exceeds {MAX_PIXELS // 1_000_000} megapixels.")
    try:
        img.load()
    except Exception as exc:
        raise ValueError("Invalid or corrupted image data: decoding failed.") from exc
    return img


def _normalized(img: Image.Image) -> Image.Image:
    """Phone photos keep their rotation in EXIF; apply it, then drop every metadata field (GPS included)."""
    upright = ImageOps.exif_transpose(img).convert("RGB")
    clean = Image.new("RGB", upright.size)
    clean.paste(upright)
    if clean.width > MAX_WIDTH or clean.height > MAX_HEIGHT:
        clean.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
    return clean
