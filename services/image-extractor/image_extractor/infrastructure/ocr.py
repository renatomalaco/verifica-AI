from PIL import Image

from image_extractor.domain.ocr_reader import OcrResult


class TesseractOcrEngine:
    """Tesseract word by word, so the result carries how sure the engine was."""

    def extract_text(self, img: Image.Image) -> OcrResult:
        try:
            import pytesseract

            data = pytesseract.image_to_data(img, lang="por+eng", output_type=pytesseract.Output.DICT)
        except Exception:
            return OcrResult("", None)  # engine missing or crashed: nothing read, confidence unknown
        words = [(w, float(c)) for w, c in zip(data["text"], data["conf"]) if w.strip() and float(c) >= 0]
        if not words:
            return OcrResult("", None)
        text = " ".join(w for w, _ in words)
        return OcrResult(text, sum(c for _, c in words) / len(words))


class ZbarQrReader:
    def read_qr_codes(self, img: Image.Image) -> list[str]:
        try:
            from pyzbar.pyzbar import decode

            return [obj.data.decode("utf-8", errors="ignore").strip() for obj in decode(img) if obj.data]
        except Exception:
            return []
