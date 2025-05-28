import os
import pymupdf
from PIL import Image
import json
import pygame
from app.template_editor.constants import SCALE, TEMP_IMG_DIR, CONFIG_DIR, INPUT_DIR, THUMB_SIZE, PREVIEW_SIZE, TARGET_HEIGHT

def pdf_page_to_image(pdf_path, page_num, out_path):
    """Convert a PDF page to an image file at a standardized height"""
    doc = pymupdf.open(pdf_path)
    page = doc.load_page(page_num)
    
    # Get original page dimensions
    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height
    
    # Calculate zoom factor to achieve target height
    zoom_factor = TARGET_HEIGHT / page_height
    
    # Create transformation matrix with the calculated zoom
    mat = pymupdf.Matrix(zoom_factor, zoom_factor)
    
    # Render the page with the calculated zoom
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PIL Image and save
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img.save(out_path)
    
    # Print dimensions for debugging
    print(f"Rendered page {page_num+1} at size: {pix.width}x{pix.height} pixels (zoom: {zoom_factor:.2f})")
    
    doc.close()
    return out_path

def load_config(pdf_filename):
    """Load the template configuration for a PDF file"""
    base_name = os.path.splitext(pdf_filename)[0]
    config_path = os.path.join(CONFIG_DIR, f'{base_name}.json')
    if not os.path.exists(config_path):
        return None
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(pdf_filename, config):
    """Save the template configuration for a PDF file"""
    config_path = os.path.join(CONFIG_DIR, f'{os.path.splitext(pdf_filename)[0]}.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def generate_thumbnail(pdf_path, thumb_path):
    """Generate a thumbnail image for a PDF file"""
    try:
        doc = pymupdf.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(0.2, 0.2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img = img.resize(THUMB_SIZE, Image.LANCZOS)
        img.save(thumb_path)
        doc.close()
        return True
    except Exception as e:
        print(f'Could not create thumbnail: {e}')
        return False

def generate_preview(pdf_path, preview_path):
    """Generate a larger preview image for a PDF file"""
    try:
        doc = pymupdf.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(0.4, 0.4))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img = img.resize(PREVIEW_SIZE, Image.LANCZOS)
        img.save(preview_path)
        doc.close()
        return True
    except Exception as e:
        print(f'Could not create preview: {e}')
        return False

def get_pdf_thumbnails(pdf_files):
    """Generate thumbnails for a list of PDF files"""
    thumb_paths = {}
    for pdf in pdf_files:
        thumb_path = os.path.join(TEMP_IMG_DIR, f'{os.path.splitext(pdf)[0]}_thumb.png')
        if not os.path.exists(thumb_path):
            generate_thumbnail(os.path.join(INPUT_DIR, pdf), thumb_path)
        thumb_paths[pdf] = thumb_path
    return thumb_paths

def get_preview_path(pdf):
    """Get the path to a PDF preview image, generating it if needed"""
    preview_path = os.path.join(TEMP_IMG_DIR, f'{os.path.splitext(pdf)[0]}_preview.png')
    if not os.path.exists(preview_path):
        generate_preview(os.path.join(INPUT_DIR, pdf), preview_path)
    return preview_path 