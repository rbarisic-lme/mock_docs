import os
import json

# Base directory of the constants.py file
_BASE_CONSTANTS_DIR = os.path.dirname(os.path.abspath(__file__))
# Assets directory is typically one level up from 'template_editor' and then into 'assets'
_ASSETS_DIR = os.path.join(_BASE_CONSTANTS_DIR, '..', 'assets')

# Directory paths
CONFIG_DIR = 'configs'
INPUT_DIR = 'input_pdfs'
OUTPUT_DIR = 'output_pdfs'
TEMP_IMG_DIR = 'temp_images'
INPUT_IMG_DIR = 'input_img'

# Asset paths
BG_TEXTURE_PATH = os.path.join(_ASSETS_DIR, 'background.png')
CURSOR_TEXT_PATH = os.path.join(_ASSETS_DIR, 'cursor_text.png')
CURSOR_IMAGE_PATH = os.path.join(_ASSETS_DIR, 'cursor_image.png')
ICON_TRASH_PATH = os.path.join(_ASSETS_DIR, 'icon_trash.png')
ICON_RESIZE_PATH = os.path.join(_ASSETS_DIR, 'icon_resize.png')

# Display settings
PADDING = 80  # workspace padding around the document (display units)
SCALE = 2     # 2x resolution for all images and coordinates
ZOOM_LEVELS = [0.25, 0.33, 0.5, 0.66, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]
DEFAULT_ZOOM_INDEX = 7  # 1.0
HANDLE_SIZE = 10

# Colors
TEXT_COLOR = (0, 0, 0)
RULER_COLOR = (150, 150, 150)
RULER_THICKNESS = 1
RULER_TEXT_COLOR = (0, 0, 0)
TOOLBAR_BG_COLOR = (30, 30, 30, 250)  # RGBA, semi-transparent dark
HIGHLIGHT_COLOR = (255, 240, 170)  # Light yellow for text editing highlight

# UI Dimensions
THUMB_SIZE = (128, 128)
PREVIEW_SIZE = (256, 362)
THUMBNAIL_SIZE = (100, 100)

# Help text
HELP_TEXT = [
    'ctrl+scroll: zoom',
    'middle/right mouse: pan',
    'left mouse: select/move',
    'reset pan: button below',
]

# Other constants
DOUBLE_CLICK_THRESHOLD = 0.4  # seconds

# Template Keys
CUSTOM_TEXT_KEY_DISPLAY = "<Custom Text>"
DEFAULT_TEXT_PLACEHOLDER_VALUE = "{{NEW_TEXT_FIELD}}"

# New constants
DEFAULT_OBSCURE_MODE = 'pixelate'
OBSCURE_PIXELATE_FACTOR = 0.08
OBSCURE_BLUR_KERNEL = 7

def flatten_json_keys(data, prefix=''):
    """Flattens a nested dictionary or list into a list of dot-separated keys."""
    items = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}{k}" if prefix else k
            if isinstance(v, (dict, list)):
                items.extend(flatten_json_keys(v, new_key + '.'))
            else:
                items.append(new_key)
    elif isinstance(data, list):
        # If we encounter a list, we might want to handle it differently,
        # e.g., by index or by assuming it's a list of values rather than keys.
        # For now, if a list contains dicts, we process them.
        # If it's a list of simple values, they won't become keys themselves unless they are dicts.
        for i, item in enumerate(data):
            # Construct a key like list_key.0, list_key.1 if needed, or just process if item is a dict
            # For the current structure, it seems lists primarily hold objects, so direct recursion is fine.
            if isinstance(item, (dict, list)):
                items.extend(flatten_json_keys(item, prefix)) # Pass prefix if items in list don't form their own base keys
            # else: # Simple values in a list are ignored for key generation
            #    pass
    return items

def load_template_keys():
    """Loads template keys from the JSON config file and flattens them."""
    keys_file_path = os.path.join(CONFIG_DIR, 'template_keys.json')
    try:
        with open(keys_file_path, 'r') as f:
            raw_keys_data = json.load(f)
        
        flattened_keys = flatten_json_keys(raw_keys_data)
        
        # Ensure CUSTOM_TEXT_KEY_DISPLAY is always the first option
        if CUSTOM_TEXT_KEY_DISPLAY in flattened_keys:
            flattened_keys.remove(CUSTOM_TEXT_KEY_DISPLAY) # Remove if exists to avoid duplication
        
        return [CUSTOM_TEXT_KEY_DISPLAY] + flattened_keys
        
    except FileNotFoundError:
        print(f"Warning: Template keys file not found at {keys_file_path}. Using default keys.")
        return [
            CUSTOM_TEXT_KEY_DISPLAY,
            "fallback.key1",
            "fallback.key2"
        ]
    except json.JSONDecodeError:
        print(f"Warning: Error decoding JSON from {keys_file_path}. Using default keys.")
        return [
            CUSTOM_TEXT_KEY_DISPLAY,
            "error.key1",
            "error.key2"
        ]

TEMPLATE_VARIABLE_KEYS = load_template_keys() 