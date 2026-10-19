import io
import base64
from PIL import Image

MAX_ALLOWED_BYTES = 5 * 1024 * 1024  # 5MB
MAX_WIDTH = 1920
MAX_HEIGHT = 1080


def validate_and_load_image(b64_str: str) -> Image.Image:
    """
    Safely decodes the base64 image and validates integrity and dimensions.
    Downsamples proportionally above 1080p to prevent DoS attacks.
    """
    try:
        raw_bytes = base64.b64decode(b64_str, validate=True)
    except Exception as exc:
        raise ValueError("Invalid or corrupted image data: base64 decoding failed.") from exc

    if len(raw_bytes) > MAX_ALLOWED_BYTES:
        raise ValueError(f"Image exceeds the {MAX_ALLOWED_BYTES // (1024*1024)}MB limit.")

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img.load()  # Force a full decode to make sure the file is not corrupted
    except Exception as exc:
        raise ValueError("Invalid or corrupted image data: unrecognized format.") from exc

    # Convert palettes or transparency to RGB
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize proportionally if it exceeds the limits
    if img.width > MAX_WIDTH or img.height > MAX_HEIGHT:
        img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)

    return img
