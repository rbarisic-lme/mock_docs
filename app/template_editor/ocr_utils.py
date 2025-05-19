import pytesseract
from PIL import Image
import numpy as np

def ocr_image(image):
    pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    
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