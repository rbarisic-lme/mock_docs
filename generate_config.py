import os
import json
import pymupdf  # PyMuPDF
from PIL import Image

# Import TARGET_HEIGHT from template editor constants to ensure consistency
from app.template_editor.constants import CONFIG_DIR, INPUT_DIR, TARGET_HEIGHT

def ensure_config_dir():
    """Ensures that the config directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def get_pdf_page_details(pdf_path):
    """
    Gets the rendered page dimensions that match the template editor's display.
    Returns a list of dictionaries with width and height that correspond to 
    the actual rendered dimensions used in the template editor.
    """
    page_details = []
    try:
        doc = pymupdf.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Get original page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Calculate zoom factor to achieve target height (same as template editor)
            zoom_factor = TARGET_HEIGHT / page_height
            
            # Calculate rendered dimensions
            rendered_width = int(page_width * zoom_factor)
            rendered_height = int(page_height * zoom_factor)
            
            page_details.append({
                "width": rendered_width, 
                "height": rendered_height,
                "original_width": page_width,
                "original_height": page_height,
                "zoom_factor": zoom_factor
            })
            
            print(f"Page {page_num+1}: Original {page_width:.1f}x{page_height:.1f} -> Rendered {rendered_width}x{rendered_height} (zoom: {zoom_factor:.3f})")
            
        doc.close()
    except Exception as e:
        print(f"Error reading PDF {pdf_path} for page details: {e}")
        return None
    return page_details

def generate_config_skeleton(pdf_filename, page_details_list):
    """
    Generates a skeleton JSON configuration structure using rendered dimensions.
    """
    config = {
        "pages": [],
        "template_values": [{}]
    }

    for i, details in enumerate(page_details_list):
        config["pages"].append({
            "page_number": i + 1,
            "width": details["width"],  # Now uses rendered dimensions
            "height": details["height"], # Now uses rendered dimensions
            "original_width": details["original_width"],
            "original_height": details["original_height"],
            "zoom_factor": details["zoom_factor"],
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
            print(f"Config already exists: {config_save_path}")
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
        print(f"Created {created_count} config(s) with rendered dimensions matching template editor.")
    else:
        print("No new configs needed to be created.")

if __name__ == "__main__":
    main() 