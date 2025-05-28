import os
from .ocr_processors import TesseractProcessor, EasyOcrProcessor, OcrProcessor

_ocr_processor_instance: OcrProcessor = None

def get_ocr_processor() -> OcrProcessor:
    global _ocr_processor_instance
    if _ocr_processor_instance is None:
        ocr_engine = os.environ.get("OCR_ENGINE", "tesseract").lower()
        tesseract_cmd = os.environ.get("TESSERACT_CMD_PATH", 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe')
        easyocr_languages = os.environ.get("EASYOCR_LANGUAGES", "en").split(',')

        if ocr_engine == "easyocr":
            print("Using EasyOCR engine.")
            try:
                _ocr_processor_instance = EasyOcrProcessor(languages=easyocr_languages)
            except ImportError as e:
                print(f"Failed to initialize EasyOCR: {e}. Falling back to Tesseract.")
                _ocr_processor_instance = TesseractProcessor(tesseract_cmd_path=tesseract_cmd)
            except Exception as e:
                 print(f"An unexpected error occurred while initializing EasyOCR: {e}. Falling back to Tesseract.")
                 _ocr_processor_instance = TesseractProcessor(tesseract_cmd_path=tesseract_cmd)

        elif ocr_engine == "tesseract":
            print("Using Tesseract engine.")
            _ocr_processor_instance = TesseractProcessor(tesseract_cmd_path=tesseract_cmd)
        else:
            print(f"Unknown OCR engine: {ocr_engine}. Defaulting to Tesseract.")
            _ocr_processor_instance = TesseractProcessor(tesseract_cmd_path=tesseract_cmd)
    return _ocr_processor_instance

def ocr_image(image):
    """
    Run OCR on a PIL Image or numpy array using the configured OCR engine.
    Returns a list of dicts as specified by OcrProcessor.ocr_image.
    """
    processor = get_ocr_processor()
    return processor.ocr_image(image)