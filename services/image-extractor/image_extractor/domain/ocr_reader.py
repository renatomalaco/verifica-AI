from typing import Protocol
from PIL import Image


class OcrEngineProtocol(Protocol):
    def extract_text(self, img: Image.Image) -> str:
        ...


class QrReaderProtocol(Protocol):
    def read_qr_codes(self, img: Image.Image) -> list[str]:
        ...


class FakeOcrEngine:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def extract_text(self, img: Image.Image) -> str:
        return self._text


class FakeQrReader:
    def __init__(self, qr_codes: list[str] | None = None) -> None:
        self._qr_codes = qr_codes or []

    def read_qr_codes(self, img: Image.Image) -> list[str]:
        return list(self._qr_codes)


class DefaultOcrEngine:
    """OCR implementation backed by Tesseract with graceful fallback."""

    def extract_text(self, img: Image.Image) -> str:
        try:
            import pytesseract
            return pytesseract.image_to_string(img, lang="por+eng").strip()
        except Exception:
            return ""


class DefaultQrReader:
    """QR code implementation backed by pyzbar with graceful fallback."""

    def read_qr_codes(self, img: Image.Image) -> list[str]:
        try:
            from pyzbar.pyzbar import decode
            decoded_objects = decode(img)
            return [obj.data.decode("utf-8", errors="ignore").strip() for obj in decoded_objects if obj.data]
        except Exception:
            return []
