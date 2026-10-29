from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float | None  # mean word confidence, 0-100


class OcrEngineProtocol(Protocol):
    def extract_text(self, img: Image.Image) -> OcrResult:
        ...


class QrReaderProtocol(Protocol):
    def read_qr_codes(self, img: Image.Image) -> list[str]:
        ...


def read_text(
    img: Image.Image,
    primary: OcrEngineProtocol,
    fallback: OcrEngineProtocol | None,
    min_confidence: float,
) -> OcrResult:
    """Photos of screens defeat Tesseract; a stronger engine (Florence-2) only runs when it doubts."""
    result = primary.extract_text(img)
    is_doubtful = result.confidence is None or result.confidence < min_confidence
    if fallback is None or not is_doubtful:
        return result
    return fallback.extract_text(img)
