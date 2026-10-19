import re
from contracts import ExtractResult
from image_extractor.domain.image_validator import validate_and_load_image
from image_extractor.domain.hasher import compute_hashes
from image_extractor.domain.ocr_reader import OcrEngineProtocol, QrReaderProtocol

_URL_REGEX = re.compile(
    r"(?:https?://|www\.)[^\s/$.?#].[^\s]*|\b[\w-]+\.(?:com|br|net|org|app|io|xyz|top|online|shop)\b",
    re.IGNORECASE,
)


class ImageExtractorService:
    """Orchestrates visual evidence extraction: hashes, OCR text and QR codes."""

    def __init__(self, ocr_engine: OcrEngineProtocol, qr_reader: QrReaderProtocol) -> None:
        self._ocr = ocr_engine
        self._qr = qr_reader

    def extract(self, image_b64: str) -> ExtractResult:
        img = validate_and_load_image(image_b64)
        sha256_hash, phash_str = compute_hashes(image_b64, img)

        extracted_text = self._ocr.extract_text(img)
        qr_codes = self._qr.read_qr_codes(img)

        # Extract links from both OCR text and QR code payloads
        all_sources = [extracted_text] + qr_codes
        urls_found: list[str] = []
        for src in all_sources:
            if not src:
                continue
            matches = _URL_REGEX.findall(src)
            for m in matches:
                clean_url = m.strip().rstrip(".,;!?:)")
                if clean_url and clean_url not in urls_found:
                    urls_found.append(clean_url)

        return ExtractResult(
            sha256=sha256_hash,
            phash=phash_str,
            extracted_text=extracted_text,
            qr_codes=qr_codes,
            urls_found=urls_found,
        )
