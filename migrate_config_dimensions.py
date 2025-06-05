import os
import json
import pymupdf
from app.template_editor.constants import CONFIG_DIR, INPUT_DIR, TARGET_HEIGHT

def get_page_scaling_info(pdf_path):
    """
    Calculate scaling information for each page of the PDF.
    Returns a list of scaling factors for each page.
    """
    scaling_info = []
    try:
        doc = pymupdf.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Calculate zoom factor to achieve target height (same as template editor)
            zoom_factor = TARGET_HEIGHT / page_height
            
            rendered_width = int(page_width * zoom_factor)
            rendered_height = int(page_height * zoom_factor)
            
            scaling_info.append({
                'original_width': page_width,
                'original_height': page_height,
                'rendered_width': rendered_width,
                'rendered_height': rendered_height,
                'zoom_factor': zoom_factor
            })
            
        doc.close()
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return None
    return scaling_info

def migrate_config_file(config_path, pdf_path):
    """
    Update page dimensions to match rendered resolution without scaling element coordinates.
    Element coordinates are already correct for the rendered resolution.
    """
    print(f"Updating page dimensions in config: {config_path}")
    
    # Load existing config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config {config_path}: {e}")
        return False
    
    # Get scaling information for the PDF
    scaling_info = get_page_scaling_info(pdf_path)
    if not scaling_info:
        print(f"Could not get scaling info for PDF: {pdf_path}")
        return False
    
    # Check if migration is needed (look for original_width field)
    if config.get('pages') and len(config['pages']) > 0:
        if 'original_width' in config['pages'][0]:
            print(f"Config {config_path} already updated. Skipping.")
            return True
    
    # Create backup
    backup_path = config_path + '.backup'
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print(f"Created backup: {backup_path}")
    except Exception as e:
        print(f"Error creating backup {backup_path}: {e}")
        return False
    
    # Update each page's dimensions only
    updated = False
    for page_idx, page_config in enumerate(config.get('pages', [])):
        if page_idx >= len(scaling_info):
            print(f"Warning: Page {page_idx + 1} in config but not in PDF scaling info")
            continue
            
        scale_info = scaling_info[page_idx]
        
        # Check if this page needs dimension update
        current_width = page_config.get('width', 0)
        current_height = page_config.get('height', 0)
        expected_width = scale_info['rendered_width']
        expected_height = scale_info['rendered_height']
        
        # If dimensions are at original PDF dimensions, update them to rendered dimensions
        original_width = scale_info['original_width']
        original_height = scale_info['original_height']
        
        width_close_to_original = abs(current_width - original_width) < 10
        height_close_to_original = abs(current_height - original_height) < 10
        
        if width_close_to_original and height_close_to_original:
            print(f"  Page {page_idx + 1}: Updating dimensions from {current_width}x{current_height} to {expected_width}x{expected_height}")
            print(f"  (Element coordinates remain unchanged - they're already correct)")
            
            # Update only page dimensions, keep element coordinates as-is
            page_config['width'] = expected_width
            page_config['height'] = expected_height
            page_config['original_width'] = original_width
            page_config['original_height'] = original_height
            page_config['zoom_factor'] = scale_info['zoom_factor']
            
            updated = True
        else:
            print(f"  Page {page_idx + 1}: Already at rendered dimensions ({current_width}x{current_height}), skipping")
    
    if updated:
        # Save updated config
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            print(f"Successfully updated config: {config_path}")
        except Exception as e:
            print(f"Error saving updated config {config_path}: {e}")
            return False
    else:
        print(f"No update needed for config: {config_path}")
        # Remove backup if no update was needed
        if os.path.exists(backup_path):
            os.remove(backup_path)
    
    return True

def main():
    """
    Update config files to use rendered page dimensions while keeping element coordinates unchanged.
    """
    print("=== Config Page Dimension Update ===")
    print(f"This script will update page dimensions in config files to match")
    print(f"rendered dimensions (targeting {TARGET_HEIGHT}px height).")
    print("Element coordinates will remain unchanged as they're already correct.")
    print("Backups will be created before updating.")
    print()
    
    if not os.path.exists(CONFIG_DIR):
        print(f"Config directory '{CONFIG_DIR}' not found.")
        return
    
    if not os.path.exists(INPUT_DIR):
        print(f"Input directory '{INPUT_DIR}' not found.")
        return
    
    # Get all config files
    config_files = [f for f in os.listdir(CONFIG_DIR) if f.endswith('.json') and not f.endswith('.backup')]
    
    if not config_files:
        print(f"No config files found in '{CONFIG_DIR}'.")
        return
    
    print(f"Found {len(config_files)} config file(s) to check:")
    
    updated_count = 0
    for config_file in config_files:
        config_path = os.path.join(CONFIG_DIR, config_file)
        
        # Find corresponding PDF file
        pdf_name = os.path.splitext(config_file)[0] + '.pdf'
        pdf_path = os.path.join(INPUT_DIR, pdf_name)
        
        if not os.path.exists(pdf_path):
            print(f"Warning: PDF file not found for config {config_file}: {pdf_path}")
            continue
        
        if migrate_config_file(config_path, pdf_path):
            updated_count += 1
        print()  # Empty line for readability
    
    print(f"Update complete. Processed {updated_count}/{len(config_files)} config files.")
    print("Backup files (.backup) were created for updated configs.")

if __name__ == "__main__":
    main() 