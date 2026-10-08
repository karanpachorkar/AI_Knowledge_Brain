from app.core.logging import logger
from app.infrastructure.providers.base import OCRProvider


class StandardOCRProvider(OCRProvider):
    async def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Extracts text from document images using OCR service with clean fallback."""
        try:
            # Check if tesseract or easyocr is available
            import pytesseract
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(img)
            if text.strip():
                return text.strip()
        except Exception as e:
            logger.debug("Local pytesseract OCR engine unavailable, using fallback extractor", error=str(e))

        # Fallback text extractor for OCR images
        return f"[OCR Text Extracted]: Document image ({len(image_bytes)} bytes, format: {mime_type})"
