import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from src.deps import CurrentUser
from src.middleware.rate_limit import check_ocr_rate_limit
from src.ocr.schemas import OCRExtractResponse
from src.ocr.services import OCRService

router = APIRouter(prefix="/ocr", tags=["OCR"])


async def get_ocr_service() -> OCRService:
    return OCRService()


OCRServiceDependency = Annotated[OCRService, Depends(get_ocr_service)]


@router.post("/extract",response_model=OCRExtractResponse,dependencies=[Depends(check_ocr_rate_limit)])
async def extract_receipt_data(file: UploadFile = File(..., description="Receipt image (JPEG, PNG, WEBP)"),current_user: CurrentUser = ...,ocr_service: OCRServiceDependency = ...,) -> OCRExtractResponse:
    """
    Extract structured data from a receipt image using AI (Gemini or Ollama).
    
    **MVP Note:** This endpoint is primarily for development/testing.
    In production, Telegram Bot calls OCRService directly.
    
    **Rate Limit:** 5 requests per minute per user.
    
    **Authentication:** Required (JWT Bearer token)
    
    **File Requirements:**
    - Formats: JPEG, PNG, WEBP
    - Max size: 10MB
    - Magic bytes validation is performed
    
    **Response:**
    - Success (200): Returns extracted receipt data
    - Error (400): Invalid file format or size
    - Error (422): Could not extract data from image
    - Error (429): Rate limit exceeded
    - Error (502): AI Service temporarily unavailable
    """
    start_time = time.perf_counter()
    
    result = await ocr_service.extract_data(file)
    
    execution_time = time.perf_counter() - start_time
    
    return OCRExtractResponse(
        success=True,
        message="Ekstrakcja zakończona pomyślnie",
        data=result,
        raw_text=None,
        execution_time=execution_time
    )
