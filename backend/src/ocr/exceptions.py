from src.common.exceptions import AppError


class OCRException(AppError):
    """Base exception for OCR-related errors"""

    pass


class FileValidationError(OCRException):
    """Invalid file format or corrupted file"""

    pass


class ExtractionError(OCRException):
    """Failed to extract data from image"""

    pass


class AIServiceError(OCRException):
    """AI Service API communication error"""

    pass
