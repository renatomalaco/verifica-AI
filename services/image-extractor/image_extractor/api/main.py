from fastapi import FastAPI, Depends, HTTPException, status
from contracts import ExtractRequest, ExtractResult
from image_extractor.domain.extractor_service import ImageExtractorService
from image_extractor.domain.ocr_reader import DefaultOcrEngine, DefaultQrReader

app = FastAPI(
    title="Verifica AI - Image Extractor",
    description="Serviço de extração e análise de evidências visuais: OCR, QR Code, pHash e SHA-256",
    version="0.1.0",
)

_global_service = ImageExtractorService(
    ocr_engine=DefaultOcrEngine(),
    qr_reader=DefaultQrReader(),
)


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
