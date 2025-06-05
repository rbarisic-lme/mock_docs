import os
import json
import pymupdf  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import glob
import platform

# Import constants from the template editor
from app.template_editor.constants import (
    INPUT_DIR, CONFIG_DIR, OUTPUT_DIR, INPUT_IMG_DIR,
    OBSCURE_PIXELATE_FACTOR, DEFAULT_OBSCURE_MODE, TARGET_HEIGHT
)

# Additional directory for template-specific images
CONFIG_IMG_DIR = "config_img"

# Ensure these are consistent if they are also defined in constants.py
# For this refactor, we will prioritize the imported constants.
# CONFIG_DIR = "configs" (Now from constants)
# INPUT_DIR = "input_pdfs" (Now from constants)
# OUTPUT_DIR = "output_pdfs" (Now from constants)

def ensure_dirs():
    """Ensures that the necessary directories exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(INPUT_IMG_DIR, exist_ok=True) # Ensure input_img also exists
    os.makedirs(CONFIG_IMG_DIR, exist_ok=True) # Ensure config_img also exists

def load_all_template_files():
    """
    Loads all template_keys_*.json files from the configs directory.
    Returns a list of (filename, template_data) tuples.
    """
    template_files = []
    pattern = os.path.join(CONFIG_DIR, 'template_keys_*.json')
    
    for template_file in glob.glob(pattern):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
                filename = os.path.basename(template_file)
                template_files.append((filename, template_data))
                print(f"Loaded template file: {filename}")
        except Exception as e:
            print(f"Error loading template file {template_file}: {e}")
    
    # Sort by filename for consistent ordering
    template_files.sort(key=lambda x: x[0])
    
    if not template_files:
        print("No template_keys_*.json files found. Looking for fallback template_keys.json...")
        fallback_path = os.path.join(CONFIG_DIR, 'template_keys.json')
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                    template_files.append(('template_keys.json', template_data))
                    print("Loaded fallback template_keys.json")
            except Exception as e:
                print(f"Error loading fallback template_keys.json: {e}")
    
    return template_files

def convert_pdf_to_images(pdf_path):
    """
    Converts each page of a PDF to a PIL Image object using the same scaling
    logic as the template editor to ensure WYSIWYG consistency.
    Returns a list of PIL Image objects at the same resolution as the editor.
    """
    images = []
    try:
        doc = pymupdf.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Use the same scaling logic as template editor's pdf_page_to_image
            page_rect = page.rect
            page_height = page_rect.height
            zoom_factor = TARGET_HEIGHT / page_height
            
            # Create transformation matrix with the calculated zoom (same as editor)
            zoom_matrix = pymupdf.Matrix(zoom_factor, zoom_factor)
            pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)
            
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
            
            print(f"Doc templater rendered page {page_num+1} at size: {pix.width}x{pix.height} pixels (zoom: {zoom_factor:.3f})")
            
        doc.close()
    except Exception as e:
        print(f"Error converting PDF {pdf_path} to images: {e}")
        return []
    return images

def get_system_font_path(font_name, font_size):
    """
    Tries to find a system font file for the given font name.
    Returns a PIL font object or None if not found.
    """
    # Common font name mappings
    font_mappings = {
        'timesnewroman': ['times.ttf', 'Times New Roman.ttf', 'TimesNewRoman.ttf', 'Times-Roman.ttf'],
        'arial': ['arial.ttf', 'Arial.ttf', 'LiberationSans-Regular.ttf'],
        'helvetica': ['helvetica.ttf', 'Helvetica.ttf', 'Arial.ttf', 'LiberationSans-Regular.ttf'],
        'calibri': ['calibri.ttf', 'Calibri.ttf'],
        'verdana': ['verdana.ttf', 'Verdana.ttf'],
        'georgia': ['georgia.ttf', 'Georgia.ttf'],
        'courier': ['courier.ttf', 'Courier.ttf', 'cour.ttf'],
        'comic sans': ['comic.ttf', 'ComicSansMS.ttf'],
    }
    
    # Normalize font name (lowercase, remove spaces)
    normalized_name = font_name.lower().replace(' ', '').replace('-', '')
    
    # Get possible font files for this font name
    possible_fonts = font_mappings.get(normalized_name, [font_name + '.ttf', font_name + '.TTF'])
    
    # Font search directories (local project fonts first, then system fonts)
    font_search_dirs = []
    
    # Add local project fonts directory
    local_fonts_dir = os.path.join(os.path.dirname(__file__), 'fonts')
    if os.path.exists(local_fonts_dir):
        font_search_dirs.append(local_fonts_dir)
    
    # System font directories by platform
    if platform.system() == 'Windows':
        font_search_dirs.extend([
            'C:/Windows/Fonts/',
            'C:/Windows/System32/Fonts/',
            os.path.expanduser('~/AppData/Local/Microsoft/Windows/Fonts/')
        ])
    elif platform.system() == 'Darwin':  # macOS
        font_search_dirs.extend([
            '/System/Library/Fonts/',
            '/Library/Fonts/',
            os.path.expanduser('~/Library/Fonts/')
        ])
    else:  # Linux and others
        font_search_dirs.extend([
            '/usr/share/fonts/',
            '/usr/local/share/fonts/',
            os.path.expanduser('~/.fonts/'),
            os.path.expanduser('~/.local/share/fonts/')
        ])
    
    # Try to find the font file
    for font_file in possible_fonts:
        # First try the font name as-is (might be a direct path)
        try:
            return ImageFont.truetype(font_file, font_size)
        except (IOError, OSError):
            pass
        
        # Then try in font search directories
        for font_dir in font_search_dirs:
            if os.path.exists(font_dir):
                font_path = os.path.join(font_dir, font_file)
                try:
                    return ImageFont.truetype(font_path, font_size)
                except (IOError, OSError):
                    continue
    
    return None

def get_fallback_font(font_size):
    """
    Returns a reliable fallback font that should work on most systems.
    """
    fallback_fonts = []
    
    if platform.system() == 'Windows':
        fallback_fonts = ['arial.ttf', 'calibri.ttf', 'tahoma.ttf']
    elif platform.system() == 'Darwin':  # macOS
        fallback_fonts = ['Helvetica.ttf', 'Arial.ttf', 'Times.ttf']
    else:  # Linux
        fallback_fonts = ['LiberationSans-Regular.ttf', 'DejaVuSans.ttf', 'Ubuntu-Regular.ttf']
    
    for fallback in fallback_fonts:
        font = get_system_font_path(fallback.replace('.ttf', ''), font_size)
        if font:
            return font
    
    # Ultimate fallback - PIL's default font
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def draw_element_pil(image, element_config, template_data):
    """
    Draws a single element on the PIL Image based on its configuration.
    This function aims to replicate the visual output of the Pygame-based
    draw_element from the template_editor.
    Scale is assumed to be 1.0 for final output.
    """
    draw = ImageDraw.Draw(image)
    element_type = element_config.get("type")

    # Element's bounding box (base units, scale is 1.0)
    # Convert to integers to avoid float errors
    x = int(element_config.get("x", 0))
    y = int(element_config.get("y", 0))
    width = int(element_config.get("width", 100))
    height = int(element_config.get("height", 30))
    
    # Background color for the element's bounding box (similar to editor's default)
    # The editor uses (255,255,255) as a default background_color for elements.
    # In doc_templater.py, the original code drew a white rectangle for text elements.
    # We should decide if elements get a background by default or if it's configured.
    # For now, let's not draw a default background unless specified or for text.
    # element_background_color = tuple(element_config.get('background_color', (255, 255, 255)))

    if element_type == "text":
        # Text elements in the editor have a background color.
        # Original doc_templater.py also drew a white rectangle.
        # Let's use the element's background_color or white if not specified.
        bg_color = tuple(element_config.get('background_color', (255, 255, 255))) # Default to white for text BG
        draw.rectangle([x, y, x + width, y + height], fill=bg_color)
        # Border removed for final output - borders are only needed in editor for field visualization
        # draw.rectangle([x, y, x + width, y + height], outline=(0,0,0), width=1)

        # First check for value_key (legacy approach)
        value_key = element_config.get("value_key")
        if value_key:
            actual_value = template_data.get(value_key, "")
        else:
            # Use the value field and resolve it if it's a template path
            template_path = element_config.get("value", "")
            actual_value = resolve_template_value(template_path, template_data)
        
        text_to_draw = str(actual_value)

        font_path_or_name = element_config.get("font", "arial") # Default font
        font_size = element_config.get("font_size", 18) # Base font size
        font_color = tuple(element_config.get("font_color", [0,0,0])) # RGB, default black

        # Try to load the requested font
        font = get_system_font_path(font_path_or_name, font_size)
        
        if not font:
            print(f"Warning: Font '{font_path_or_name}' not found. Using fallback font.")
            font = get_fallback_font(font_size)
        
        if not font:
            print(f"Error: Could not load any font for text element: {element_config.get('name', 'Unnamed')}")
            return
        
        if font:
            # Text alignment from editor (basic top-left within box for now)
            # Future: honor text_align_horiz, text_align_vert if added to config
            text_render_pos_x_in_box = 0  # Simple padding/offset within box
            text_render_pos_y_in_box = 0
            
            # Calculate text actual rendering position
            text_x = x + text_render_pos_x_in_box
            text_y = y + text_render_pos_y_in_box

            # PIL's draw.text uses the top-left corner of the text.
            # We need to ensure text fits within its bounding box if clipping is desired.
            # The editor clips text to the bounding box.
            # For PIL, we can create a temporary image for the text, then paste it clipped.
            
            # Get text size
            #bbox = draw.textbbox((text_x, text_y), text_to_draw, font=font)
            #text_width = bbox[2] - bbox[0]
            #text_height = bbox[3] - bbox[1]
            
            # To clip, we draw on a temp surface and paste.
            # Create a temporary surface for text rendering with transparent background
            text_surface = Image.new('RGBA', (width, height), (0,0,0,0))
            text_draw = ImageDraw.Draw(text_surface)
            text_draw.text((text_render_pos_x_in_box, text_render_pos_y_in_box), text_to_draw, font=font, fill=font_color)
            
            # Paste the text surface onto the main image, respecting alpha for transparency
            # The element's (x,y) is the top-left of its bounding box.
            image.paste(text_surface, (x, y), text_surface)
        else:
            print(f"Error: Could not load font for text element: {element_config.get('name', 'Unnamed')}")


    elif element_type == "rectangle":
        rect_fill_color = tuple(element_config.get('background_color', (255, 255, 255))) # Default white
        draw.rectangle([x, y, x + width, y + height], fill=rect_fill_color)
        # Only draw border if explicitly requested in config
        if element_config.get('show_border', False):
            border_color = tuple(element_config.get('border_color', (0, 0, 0)))
            draw.rectangle([x, y, x + width, y + height], outline=border_color, width=1)

    elif element_type == "image" or element_type == "signature":
        # First check for value_key (legacy approach)
        value_key = element_config.get("value_key")
        if value_key:
            image_path_template = str(template_data.get(value_key, ""))
        else:
            # Use the value field and resolve it if it's a template path
            template_path = element_config.get("value", "")
            image_path_template = str(resolve_template_value(template_path, template_data))

        # Resolve image path (might be a key itself in template_data for dynamic paths)
        image_path, search_directory = resolve_image_path(image_path_template, template_data)

        if not image_path:
            print(f"Warning: Image path is empty for element: {element_config.get('name', 'Unnamed')}")
            return

        full_img_path = image_path
        if not os.path.isabs(image_path):
            full_img_path = os.path.join(search_directory, image_path)

        if not os.path.exists(full_img_path):
            print(f"Warning: Image not found at {full_img_path} for element: {element_config.get('name', 'Unnamed')}")
            # Draw an X or error placeholder like in editor
            draw.rectangle([x, y, x + width, y + height], outline=(255,0,0), width=1)
            draw.line([(x,y), (x+width, y+height)], fill=(255,0,0), width=1)
            draw.line([(x+width,y), (x, y+height)], fill=(255,0,0), width=1)
            return

        try:
            img_to_paste_orig = Image.open(full_img_path).convert("RGBA") # Use RGBA for transparency

            padding = element_config.get('padding', {'left': 0, 'top': 0, 'right': 0, 'bottom': 0})
            pad_left = int(padding.get('left', 0))
            pad_top = int(padding.get('top', 0))
            pad_right = int(padding.get('right', 0))
            pad_bottom = int(padding.get('bottom', 0))

            content_area_w = width - pad_left - pad_right
            content_area_h = height - pad_top - pad_bottom

            if content_area_w <= 0 or content_area_h <= 0:
                print(f"Warning: Content area for image {full_img_path} is zero or negative after padding.")
                return

            img_orig_w, img_orig_h = img_to_paste_orig.size
            if img_orig_w == 0 or img_orig_h == 0:
                print(f"Warning: Original image {full_img_path} has zero dimensions.")
                return

            aspect_ratio = img_orig_w / img_orig_h
            
            render_w = content_area_w
            render_h = render_w / aspect_ratio
            
            if render_h > content_area_h:
                render_h = content_area_h
                render_w = render_h * aspect_ratio
            
            render_w = int(render_w)
            render_h = int(render_h)

            if render_w > 0 and render_h > 0:
                resized_img = img_to_paste_orig.resize((render_w, render_h), Image.LANCZOS) # High quality resize

                # Position for pasting (top-left corner of the resized image within the content area)
                # Centering the image within the padded content area
                paste_x_in_box = pad_left + (content_area_w - render_w) // 2
                paste_y_in_box = pad_top + (content_area_h - render_h) // 2
                
                final_paste_x = x + paste_x_in_box
                final_paste_y = y + paste_y_in_box
                
                # The editor's image element has a background color for the bounding box,
                # but the image itself is pasted on top. We won't draw a default bg for the image box here,
                # only if specified in element_config.background_color (which is not implemented yet).
                # Pasting with RGBA mask handles transparency.
                image.paste(resized_img, (final_paste_x, final_paste_y), resized_img)
            else:
                print(f"Warning: Calculated render dimensions for image {full_img_path} are zero after padding.")

        except Exception as e:
            print(f"Error processing image element {element_config.get('name', 'Unnamed')} with path {full_img_path}: {e}")
            # Draw an X or error placeholder
            draw.rectangle([x, y, x + width, y + height], outline=(255,0,0), width=1)
            draw.line([(x,y), (x+width, y+height)], fill=(255,0,0), width=1)
            draw.line([(x+width,y), (x, y+height)], fill=(255,0,0), width=1)
    
    elif element_type == "obscure":
        mode = element_config.get('mode', DEFAULT_OBSCURE_MODE)
        obscure_rect_pil = (x, y, x + width, y + height)

        if width > 0 and height > 0:
            try:
                region_to_obscure = image.crop(obscure_rect_pil)
                
                if mode == 'blacken':
                    obscured_region = Image.new('RGB', (width, height), (0,0,0))
                elif mode == 'pixelate':
                    factor = OBSCURE_PIXELATE_FACTOR # From constants
                    small_w = max(1, int(width * factor))
                    small_h = max(1, int(height * factor))
                    small = region_to_obscure.resize((small_w, small_h), Image.NEAREST)
                    obscured_region = small.resize((width, height), Image.NEAREST)
                elif mode == 'blur': # TODO: Implement blur similar to editor (e.g., BoxBlur or Gaussian)
                    # Example using BoxBlur, kernel size needs to match editor's effect
                    # from app.template_editor.constants import OBSURE_BLUR_KERNEL (if defined)
                    blur_radius = element_config.get('blur_radius', 5) # Or derive from OBSURE_BLUR_KERNEL
                    obscured_region = region_to_obscure.filter(ImageFilter.BoxBlur(blur_radius))
                    print(f"Warning: 'blur' mode for 'obscure' element is using basic BoxBlur. Ensure visual match with editor or refine.")
                else: # Default to blacken if mode is unknown
                    obscured_region = Image.new('RGB', (width, height), (0,0,0))
                
                image.paste(obscured_region, obscure_rect_pil)
                # Border removed for natural appearance in final output
                # draw.rectangle(obscure_rect_pil, outline=(0,0,0), width=1)

            except Exception as e:
                print(f"Error obscuring region for element {element_config.get('name', 'Unnamed')}: {e}")
                # Fallback: draw a simple black rectangle if effect fails
                draw.rectangle(obscure_rect_pil, fill=(50,50,50)) # Dark gray to indicate error in effect
                draw.rectangle(obscure_rect_pil, outline=(255,0,0), width=1)
    else:
        print(f"Unsupported element type: {element_type} in draw_element_pil")

# Original draw_element function is removed as we're replacing its usage
# with draw_element_pil within this script's context.

def process_pdf(pdf_filename, config_path, output_dir_param, template_files): # Added template_files parameter
    """
    Processes a single PDF file based on its JSON configuration.
    Generates multiple output PDFs based on template_files list.
    Uses draw_element_pil for rendering.
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f: # Added encoding
            config_data = json.load(f)
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        return
    except json.JSONDecodeError:
        print(f"Error decoding JSON from: {config_path}")
        return

    pdf_path = os.path.join(INPUT_DIR, pdf_filename)
    base_pdf_images = convert_pdf_to_images(pdf_path) # This returns PIL Images

    if not base_pdf_images:
        print(f"Could not convert PDF {pdf_filename} to images. Skipping.")
        return

    # Process each template file
    for template_filename, template_data in template_files:
        output_images_pil = [] # Store PIL images for output
        
        # Extract employee name for filename if available
        employee_name = template_data.get('employee', {}).get('name', '')
        if employee_name:
            # Clean up name for filename
            clean_name = employee_name.replace(' ', '_').replace('.', '').lower()
            output_suffix = f"_{clean_name}"
        else:
            # Use template filename as fallback
            base_template_name = os.path.splitext(template_filename)[0]
            output_suffix = f"_{base_template_name}"

        output_pdf_path = os.path.join(output_dir_param, f"{os.path.splitext(pdf_filename)[0]}{output_suffix}.pdf")

        for page_index, page_config in enumerate(config_data.get("pages", [])):
            if page_index >= len(base_pdf_images):
                print(f"Warning: Page config for page {page_index + 1} exists, but PDF has only {len(base_pdf_images)} pages.")
                continue

            current_page_image_pil = base_pdf_images[page_index].copy() # Work on a copy

            # Draw elements in the correct order: rectangle, obscure, image, text
            # This ensures proper layering just like in the template editor
            element_types_draw_order = ['rectangle', 'obscure', 'image', 'text']
            all_elements_with_indices = list(enumerate(page_config.get("elements", [])))
            
            # Draw elements by type in the specified order
            for el_type_to_draw in element_types_draw_order:
                for original_idx, element in all_elements_with_indices:
                    if element.get('type') == el_type_to_draw:
                        # Call the new PIL-based drawing function with template_data
                        draw_element_pil(current_page_image_pil, element, template_data)
            
            # Draw any remaining element types not in the standard order
            for original_idx, element in all_elements_with_indices:
                if element.get('type') not in element_types_draw_order:
                    # Call the new PIL-based drawing function with template_data
                    draw_element_pil(current_page_image_pil, element, template_data)
            
            output_images_pil.append(current_page_image_pil)

        if output_images_pil:
            try:
                # Ensure images are in RGB before saving to PDF if they had alpha (e.g. from RGBA paste)
                # PyMuPDF conversion should give RGB, but elements might have introduced alpha.
                rgb_output_images = [img.convert("RGB") for img in output_images_pil]
                
                if rgb_output_images:
                    rgb_output_images[0].save(
                        output_pdf_path, 
                        save_all=True, 
                        append_images=rgb_output_images[1:]
                    )
                    print(f"Successfully generated {output_pdf_path}")
                else:
                    print(f"No images to save for {pdf_filename} with template {template_filename}. Output PDF not generated.")
            except Exception as e:
                print(f"Error saving output PDF {output_pdf_path}: {e}")
        else:
            print(f"No images processed for {pdf_filename} with template {template_filename}. Output PDF not generated.")

def resolve_template_value(value_path, template_data):
    """
    Resolves a dot-notation path like "employee.address" to the actual value
    from the template data structure.
    
    Args:
        value_path (str): Dot-notation path like "employee.address"
        template_data (dict): The template data dictionary
    
    Returns:
        str: The resolved value or the original path if not found
    """
    if not value_path or not isinstance(value_path, str):
        return value_path
    
    # If it doesn't contain a dot, try direct lookup first
    if '.' not in value_path:
        return template_data.get(value_path, value_path)
    
    # Split the path and traverse the nested dictionary
    parts = value_path.split('.')
    current = template_data
    
    try:
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # Path not found, return original value
                return value_path
        
        # Convert to string for display
        return str(current) if current is not None else value_path
    except (KeyError, TypeError):
        # If traversal fails, return original value
        return value_path

def resolve_image_path(image_path, template_data):
    """
    Resolves image path using template-specific image replacements.
    
    Args:
        image_path (str): Original image path
        template_data (dict): The template data dictionary
    
    Returns:
        tuple: (resolved_path, search_directory) where search_directory is either CONFIG_IMG_DIR or INPUT_IMG_DIR
    """
    if not image_path or not isinstance(image_path, str):
        return image_path, INPUT_IMG_DIR
    
    # Check if template data has image replacements
    image_replacements = template_data.get('images', {})
    
    # If this image has a replacement, use it and look in config_img
    if image_path in image_replacements:
        replacement_path = image_replacements[image_path]
        print(f"Image replacement: '{image_path}' -> '{replacement_path}' (using config_img directory)")
        return replacement_path, CONFIG_IMG_DIR
    
    # No replacement found, use original path and look in input_img
    return image_path, INPUT_IMG_DIR

def main():
    """
    Main function to scan for PDFs and process them with all template files.
    """
    ensure_dirs()
    
    # Load all template files
    template_files = load_all_template_files()
    if not template_files:
        print("No template files found. Cannot process PDFs.")
        return
    
    print(f"Found {len(template_files)} template files:")
    for filename, _ in template_files:
        print(f"  - {filename}")
    
    print(f"Scanning for PDF files in: {INPUT_DIR}")
    print(f"Looking for JSON configurations in: {CONFIG_DIR}")
    print(f"Outputting processed PDFs to: {OUTPUT_DIR}") # Uses imported OUTPUT_DIR

    processed_files = 0
    total_generated_pdfs = 0
    
    for filename in os.listdir(INPUT_DIR):
        if filename.lower().endswith(".pdf"):
            pdf_name_without_ext = os.path.splitext(filename)[0]
            # Config filename might now have complex chars, ensure it's handled.
            # Assuming config files are named exactly like the PDF but with .json
            config_filename = f"{pdf_name_without_ext}.json"
            config_path = os.path.join(CONFIG_DIR, config_filename)

            print(f"Found PDF: {filename}. Looking for config: {config_path}")

            if os.path.exists(config_path):
                print(f"Processing {filename} with {config_filename} using {len(template_files)} template datasets...")
                process_pdf(filename, config_path, OUTPUT_DIR, template_files) # Pass template_files
                processed_files += 1
                total_generated_pdfs += len(template_files)  # Each PDF generates multiple outputs
            else:
                print(f"Config file {config_filename} not found for {filename}. Skipping.")
    
    if processed_files == 0:
        print(f"No PDF files were processed. Ensure PDFs are in '{INPUT_DIR}' and JSON configs in '{CONFIG_DIR}'.")
    else:
        print(f"Processed {processed_files} PDF file(s), generating {total_generated_pdfs} output documents total.")


if __name__ == "__main__":
    main()
