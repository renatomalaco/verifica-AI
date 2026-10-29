from fastapi import FastAPI, Depends, HTTPException, status
from contracts import ExtractRequest, ExtractResult
from image_extractor.domain.extractor_service import ImageExtractorService
from image_extractor.infrastructure.ocr import TesseractOcrEngine, ZbarQrReader

app = FastAPI(
    title="Verifica AI - Image Extractor",
    description="Visual evidence extraction and analysis: OCR, QR code, pHash and SHA-256",
    version="0.1.0",
)

# A fallback OCR (Florence-2) plugs in through fallback_ocr when it is deployed; off by default.
_global_service = ImageExtractorService(ocr_engine=TesseractOcrEngine(), qr_reader=ZbarQrReader())


def get_extractor_service() -> ImageExtractorService:
    return _global_service


@app.get("/health")
async def health():
    return {"status": "ok", "service": "image-extractor"}


@app.post("/extract", response_model=ExtractResult)
async def extract_image(
    payload: ExtractRequest,
    service: ImageExtractorService = Depends(get_extractor_service),
) -> ExtractResult:
    try:
        return service.extract(payload.image_b64)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
