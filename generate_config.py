import os
import json
import pymupdf  # PyMuPDF
from PIL import Image

# Consistent with doc-templater.py
CONFIG_DIR = "configs"
INPUT_DIR = "input_pdfs" 

def ensure_config_dir():
    """Ensures that the config directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def get_pdf_page_details(pdf_path):
    """
    Gets the number of pages and dimensions for each page in a PDF.
    Returns a list of tuples, where each tuple is (width, height).
    """
    page_details = []
    try:
        doc = pymupdf.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # Get dimensions directly from the page object for accuracy
            # The page.rect gives (x0, y0, x1, y1) from which width and height can be calculated.
            # Using get_pixmap().width/height is also fine but this is more direct.
            width = int(page.rect.width)
            height = int(page.rect.height)
            page_details.append({"width": width, "height": height})
        doc.close()
    except Exception as e:
        print(f"Error reading PDF {pdf_path} for page details: {e}")
        return None
    return page_details

def generate_config_skeleton(pdf_filename, page_details_list):
    """
    Generates a skeleton JSON configuration structure.
    """
    config = {
        "pages": [],
        "template_values": [{}]
    }

    for i, details in enumerate(page_details_list):
        config["pages"].append({
            "page_number": i + 1,
            "width": details["width"],
            "height": details["height"],
            "elements": []
        })
    
    return config

def main():
    ensure_config_dir()
    os.makedirs(INPUT_DIR, exist_ok=True)

    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"No PDF files found in '{INPUT_DIR}'.")
        return

    created_count = 0
    for pdf_filename in pdf_files:
        base_name = os.path.splitext(pdf_filename)[0]
        config_filename = f"{base_name}.json"
        config_save_path = os.path.join(CONFIG_DIR, config_filename)
        pdf_path = os.path.join(INPUT_DIR, pdf_filename)

        if os.path.exists(config_save_path):
            continue

        page_details = get_pdf_page_details(pdf_path)
        if page_details:
            config_skeleton = generate_config_skeleton(pdf_filename, page_details)
            try:
                with open(config_save_path, 'w') as f:
                    json.dump(config_skeleton, f, indent=4)
                print(f"Created config: {config_save_path}")
                created_count += 1
            except IOError as e:
                print(f"Error saving configuration file {config_save_path}: {e}")
        else:
            print(f"Could not retrieve page details for {pdf_filename}. Config file not generated.")

    if created_count > 0:
        print(f"Created {created_count} config(s).")
    else:
        print("No configs need to be created.")

if __name__ == "__main__":
    main() 