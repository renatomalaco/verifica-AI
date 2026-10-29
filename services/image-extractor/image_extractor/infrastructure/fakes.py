from PIL import Image

from image_extractor.domain.ocr_reader import OcrResult


class FakeOcrEngine:
    def __init__(self, result: OcrResult | None = None) -> None:
        self._result = result or OcrResult("", None)
        self.calls = 0

    def extract_text(self, img: Image.Image) -> OcrResult:
        self.calls += 1
        return self._result


class FakeQrReader:
    def __init__(self, qr_codes: list[str] | None = None) -> None:
        self._qr_codes = qr_codes or []

    def read_qr_codes(self, img: Image.Image) -> list[str]:
        return list(self._qr_codes)
