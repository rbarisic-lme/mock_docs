import pytesseract
from PIL import Image
import numpy as np
import abc

class OcrProcessor(abc.ABC):
    @abc.abstractmethod
    def ocr_image(self, image):
        """
        Run OCR on a PIL Image or numpy array and return a list of dicts:
        [{
            'text': str,
            'left': int,
            'top': int,
            'width': int,
            'height': int,
            'conf': float,
            'font_size': int (estimated, optional)
        }, ...]
        """
        pass

class TesseractProcessor(OcrProcessor):
    def __init__(self, tesseract_cmd_path='C:\\Program Files\\Tesseract-OCR\\tesseract.exe'):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_path

    def ocr_image(self, image):
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        results = []
        n_boxes = len(data['level'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0 and data['text'][i].strip():
                left, top, width, height = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                text = data['text'][i]
                conf = float(data['conf'][i])
                # Estimate font size as height (roughly)
                font_size = height
                results.append({
                    'text': text,
                    'left': left,
                    'top': top,
                    'width': width,
                    'height': height,
                    'conf': conf,
                    'font_size': font_size
                })
        return results

class EasyOcrProcessor(OcrProcessor):
    def __init__(self, languages=None):
        if languages is None:
            languages = ['en'] # Default to English
        try:
            import easyocr
            self.reader = easyocr.Reader(languages)
        except ImportError as e:
            raise ImportError("EasyOCR is not installed. Please install it using: pip install easyocr") from e
        except Exception as e:
            # Handle cases where model files might be missing or download fails
            print(f"Error initializing EasyOCR Reader: {e}")
            print("Please ensure you have the necessary EasyOCR model files for the selected languages.")
            print("You might need to run the EasyOCR setup or manually download models.")
            self.reader = None # Indicate initialization failure


    def ocr_image(self, image):
        if self.reader is None:
            print("EasyOCR reader not initialized. Cannot perform OCR.")
            return []

        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # EasyOCR returns a list of tuples: (bbox, text, prob)
        # bbox is a list of 4 points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        raw_results = self.reader.readtext(image)
        
        results = []
        for (bbox, text, prob) in raw_results:
            # Convert bbox to left, top, width, height
            # EasyOCR provides coordinates of the four corners of the bounding box
            # For simplicity, we'll take the min/max x/y to define a rectangle
            # More accurate methods could be used if skewed text is common
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            
            left = int(min(x_coords))
            top = int(min(y_coords))
            width = int(max(x_coords) - left)
            height = int(max(y_coords) - top)
            
            # Estimate font size as height (roughly)
            font_size = height
            
            results.append({
                'text': text,
                'left': left,
                'top': top,
                'width': width,
                'height': height,
                'conf': float(prob * 100),  # EasyOCR prob is 0-1, Tesseract is 0-100
                'font_size': font_size
            })
        return results 