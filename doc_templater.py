import os
import json
import pymupdf  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

# Placeholder for a more sophisticated configuration/logging setup
CONFIG_DIR = "configs"
INPUT_DIR = "input_pdfs"
OUTPUT_DIR = "output_pdfs"

def ensure_dirs():
    """Ensures that the necessary directories exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def convert_pdf_to_images(pdf_path):
    """
    Converts each page of a PDF to a PIL Image object.
    Returns a list of PIL Image objects.
    """
    images = []
    try:
        doc = pymupdf.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        doc.close()
    except Exception as e:
        print(f"Error converting PDF {pdf_path} to images: {e}")
        return []
    return images

def draw_element(image, element_config, template_data):
    """
    Draws a single element (text, image, signature) on the image.
    """
    draw = ImageDraw.Draw(image)
    element_type = element_config.get("type")
    x = element_config.get("x", 0)
    y = element_config.get("y", 0)
    width = element_config.get("width", 0)
    height = element_config.get("height", 0)
    value_key = element_config.get("value_key") # Key to get data from template_data
    padding = element_config.get("padding", {"top": 0, "right": 0, "bottom": 0, "left": 0})

    actual_value = template_data.get(value_key, "") if value_key else element_config.get("value", "")


    # 1. Draw a white rectangle underneath (optional, based on config?)
    # For now, always draw it to ensure text is on a clean background
    # Apply padding to the white rectangle
    rect_x0 = x - padding.get("left", 0)
    rect_y0 = y - padding.get("top", 0)
    rect_x1 = x + width + padding.get("right", 0)
    rect_y1 = y + height + padding.get("bottom", 0)
    draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], fill="white")


    if element_type == "text":
        text = str(actual_value)
        font_path = element_config.get("font", "arial.ttf") # Default font
        font_size = element_config.get("font_size", 12)
        font_color = tuple(element_config.get("font_color", [0,0,0])) # RGB, default black

        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"Warning: Font {font_path} not found. Using default.")
            font = ImageFont.load_default()

        # Adjust text position by internal padding (if any) and element's main x,y
        text_x = x
        text_y = y
        draw.text((text_x, text_y), text, font=font, fill=font_color)

    elif element_type == "image" or element_type == "signature":
        image_path_template = str(actual_value) # The value from template might be the path
        
        # If image_path_template is a key, resolve it from template_data
        # This allows dynamic image paths based on data
        image_path = template_data.get(image_path_template, image_path_template)


        if not os.path.exists(image_path):
            print(f"Warning: Image not found at {image_path} for element: {element_config.get('name', 'Unnamed')}")
            return # Skip this element if image doesn't exist

        try:
            img_to_paste = Image.open(image_path).convert("RGBA") # Use RGBA for transparency
            
            # Resize image to fit specified width/height, maintaining aspect ratio
            img_to_paste.thumbnail((width, height))
            
            # Position for pasting (top-left corner of the image)
            paste_x = x
            paste_y = y
            
            # PIL's paste uses the top-left corner.
            # If the background is not transparent, it will just overwrite.
            # If the image has an alpha channel, it will be used.
            image.paste(img_to_paste, (paste_x, paste_y), img_to_paste if img_to_paste.mode == 'RGBA' else None)

        except Exception as e:
            print(f"Error processing image element {element_config.get('name', 'Unnamed')} with path {image_path}: {e}")
    else:
        print(f"Unsupported element type: {element_type}")


def process_pdf(pdf_filename, config_path, output_dir):
    """
    Processes a single PDF file based on its JSON configuration.
    Generates multiple output PDFs based on template_values in the JSON.
    """
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        return
    except json.JSONDecodeError:
        print(f"Error decoding JSON from: {config_path}")
        return

    pdf_path = os.path.join(INPUT_DIR, pdf_filename)
    base_pdf_images = convert_pdf_to_images(pdf_path)

    if not base_pdf_images:
        print(f"Could not convert PDF {pdf_filename} to images. Skipping.")
        return

    template_values_list = config_data.get("template_values", [{}]) # Default to one run with no template vars

    for i, template_data in enumerate(template_values_list):
        output_images = []
        output_pdf_path = os.path.join(output_dir, f"{os.path.splitext(pdf_filename)[0]}_output_{i+1}.pdf")

        for page_index, page_config in enumerate(config_data.get("pages", [])):
            if page_index >= len(base_pdf_images):
                print(f"Warning: Page configuration for page {page_index + 1} exists, but PDF {pdf_filename} has only {len(base_pdf_images)} pages.")
                continue

            current_page_image = base_pdf_images[page_index].copy() # Work on a copy

            for element in page_config.get("elements", []):
                draw_element(current_page_image, element, template_data)
            
            output_images.append(current_page_image)

        if output_images:
            try:
                # Convert to RGB before saving to PDF to avoid issues with alpha channels if any were introduced.
                # PIL saves PDF by saving the first image and appending others.
                rgb_output_images = [img.convert("RGB") for img in output_images]
                rgb_output_images[0].save(
                    output_pdf_path, 
                    save_all=True, 
                    append_images=rgb_output_images[1:]
                )
                print(f"Successfully generated {output_pdf_path}")
            except Exception as e:
                print(f"Error saving output PDF {output_pdf_path}: {e}")
        else:
            print(f"No images processed for {pdf_filename} with template data set {i+1}. Output PDF not generated.")


def main():
    """
    Main function to scan for PDFs and process them.
    """
    ensure_dirs()
    print(f"Scanning for PDF files in: {INPUT_DIR}")
    print(f"Looking for JSON configurations in: {CONFIG_DIR}")
    print(f"Outputting processed PDFs to: {OUTPUT_DIR}")

    processed_files = 0
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".pdf"):
            pdf_name_without_ext = os.path.splitext(filename)[0]
            config_filename = f"{pdf_name_without_ext}.json"
            config_path = os.path.join(CONFIG_DIR, config_filename)

            print(f"Found PDF: {filename}. Looking for config: {config_path}")

            if os.path.exists(config_path):
                print(f"Processing {filename} with {config_filename}...")
                process_pdf(filename, config_path, OUTPUT_DIR)
                processed_files +=1
            else:
                print(f"Configuration file {config_filename} not found in {CONFIG_DIR}. Skipping {filename}.")
    
    if processed_files == 0:
        print(f"No PDF files were processed. Ensure your PDFs are in '{INPUT_DIR}' and corresponding JSON configs are in '{CONFIG_DIR}'.")
    else:
        print(f"Processed {processed_files} PDF file(s).")


if __name__ == "__main__":
    main()
