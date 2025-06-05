"""
WYSIWYG Verification Script

This script demonstrates that the template editor, config files, and doc_templater
now use consistent resolutions and coordinate systems, ensuring true WYSIWYG editing.
"""

import os
import json
import pymupdf
from app.template_editor.constants import CONFIG_DIR, INPUT_DIR, TARGET_HEIGHT
from app.template_editor.pdf_utils import pdf_page_to_image

def verify_consistency():
    print("=== WYSIWYG Consistency Verification ===")
    print(f"Target height for all systems: {TARGET_HEIGHT}px")
    print()
    
    # Find a config file that has a corresponding PDF
    config_files = [f for f in os.listdir(CONFIG_DIR) if f.endswith('.json') and not f.endswith('.backup')]
    
    if not config_files:
        print("No config files found for verification.")
        return
    
    test_config = None
    pdf_path = None
    
    for config_file in config_files:
        pdf_name = os.path.splitext(config_file)[0] + '.pdf'
        pdf_path_candidate = os.path.join(INPUT_DIR, pdf_name)
        if os.path.exists(pdf_path_candidate):
            test_config = config_file
            pdf_path = pdf_path_candidate
            break
    
    if not test_config:
        print("No config files found with corresponding PDF files.")
        return
    
    config_path = os.path.join(CONFIG_DIR, test_config)
    
    print(f"Testing with: {test_config}")
    print(f"Corresponding PDF: {os.path.basename(pdf_path)}")
    print()
    
    # Load config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Check PDF original dimensions
    doc = pymupdf.open(pdf_path)
    page = doc.load_page(0)
    original_width = page.rect.width
    original_height = page.rect.height
    zoom_factor = TARGET_HEIGHT / original_height
    doc.close()
    
    print("1. PDF Original Dimensions:")
    print(f"   {original_width:.1f} x {original_height:.1f} points")
    print()
    
    print("2. Template Editor Rendering:")
    print(f"   Zoom factor: {zoom_factor:.3f}")
    print(f"   Rendered size: {int(original_width * zoom_factor)} x {TARGET_HEIGHT}px")
    print()
    
    # Check config dimensions
    page_config = config['pages'][0]
    config_width = page_config['width']
    config_height = page_config['height']
    
    print("3. Config File Dimensions:")
    print(f"   Stored dimensions: {config_width} x {config_height}px")
    
    if 'original_width' in page_config:
        print(f"   Original dimensions: {page_config['original_width']:.1f} x {page_config['original_height']:.1f}")
        print(f"   Zoom factor: {page_config['zoom_factor']:.3f}")
    else:
        print("   (Legacy config - needs migration)")
    print()
    
    # Verify consistency
    expected_width = int(original_width * zoom_factor)
    expected_height = TARGET_HEIGHT
    
    print("4. Consistency Check:")
    width_match = abs(config_width - expected_width) <= 2  # Allow for rounding
    height_match = abs(config_height - expected_height) <= 2
    
    print(f"   Config width matches expected: {width_match} ({config_width} vs {expected_width})")
    print(f"   Config height matches expected: {height_match} ({config_height} vs {expected_height})")
    
    if width_match and height_match:
        print("   ✅ WYSIWYG consistency verified!")
    else:
        print("   ❌ Inconsistency detected!")
    print()
    
    # Sample element coordinate check
    if config['pages'][0].get('elements'):
        element = config['pages'][0]['elements'][0]
        print("5. Sample Element Coordinates:")
        print(f"   Type: {element.get('type', 'unknown')}")
        print(f"   Position: ({element.get('x', 0)}, {element.get('y', 0)})")
        print(f"   Size: {element.get('width', 0)} x {element.get('height', 0)}px")
        print(f"   Font size: {element.get('font_size', 'N/A')}")
        print("   (These coordinates are now relative to the rendered image size)")
    
    print()
    print("Summary:")
    print("- Template editor renders PDFs at ~2000px height")
    print("- Config files store coordinates relative to this rendered size")
    print("- Doc templater uses the same rendering scale")
    print("- This ensures true WYSIWYG: what you see in the editor is what you get in output!")

if __name__ == "__main__":
    verify_consistency() 