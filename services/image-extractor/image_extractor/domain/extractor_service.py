import base64
import io
import re

from PIL import Image

from contracts import ExtractResult
from image_extractor.domain.hasher import compute_hashes
from image_extractor.domain.image_validator import decode_base64, load_image
from image_extractor.domain.ocr_reader import OcrEngineProtocol, QrReaderProtocol, read_text

MIN_OCR_CONFIDENCE = 60.0

_URL_REGEX = re.compile(
    r"(?:https?://|www\.)[^\s/$.?#].[^\s]*|\b[\w-]+\.(?:com|br|net|org|app|io|xyz|top|online|shop)\b",
    re.IGNORECASE,
)


class ImageExtractorService:
    """Orchestrates visual evidence extraction: hashes, OCR text, QR codes and a clean copy."""

    def __init__(
        self,
        ocr_engine: OcrEngineProtocol,
        qr_reader: QrReaderProtocol,
        fallback_ocr: OcrEngineProtocol | None = None,
    ) -> None:
        self._ocr = ocr_engine
        self._qr = qr_reader
        self._fallback = fallback_ocr

    def extract(self, image_b64: str) -> ExtractResult:
        raw = decode_base64(image_b64)
        img = load_image(raw)
        sha256_hash, phash_str = compute_hashes(raw, img)
        ocr = read_text(img, self._ocr, self._fallback, MIN_OCR_CONFIDENCE)
        qr_codes = self._qr.read_qr_codes(img)

        return ExtractResult(
            sha256=sha256_hash,
            phash=phash_str,
            extracted_text=ocr.text,
            qr_codes=qr_codes,
            urls_found=_urls_in([ocr.text, *qr_codes]),
            ocr_confidence=ocr.confidence,
            clean_image_b64=_jpeg_b64(img),
        )


def _urls_in(sources: list[str]) -> list[str]:
    urls: list[str] = []
    for match in (m for src in sources if src for m in _URL_REGEX.findall(src)):
        url = match.strip().rstrip(".,;!?:)")
        if url and url not in urls:
            urls.append(url)
    return urls


def _jpeg_b64(img: Image.Image) -> str:
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)  # re-encoding writes no EXIF
    return base64.b64encode(buffer.getvalue()).decode("ascii")
