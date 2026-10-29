import hashlib
from PIL import Image
import imagehash


def compute_hashes(raw: bytes, img: Image.Image) -> tuple[str, str]:
    """
    Computes the image hashes:
    1. Exact SHA-256 of the file bytes (base64 line breaks or padding must not change it)
    2. Perceptual pHash (DCT) to tolerate WhatsApp/Telegram JPEG compression
    """
    sha256 = hashlib.sha256(raw).hexdigest()
    phash = str(imagehash.phash(img))
    return sha256, phash


def hamming_distance(hash1_hex: str, hash2_hex: str) -> int:
    """Computes the Hamming distance between two hex-encoded perceptual hashes."""
    h1 = imagehash.hex_to_hash(hash1_hex)
    h2 = imagehash.hex_to_hash(hash2_hex)
    return h1 - h2
