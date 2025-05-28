# put the code for the text properties floating menu here

import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UITextBox, UITextEntryLine, UIButton, UIDropDownMenu
from app.template_editor.constants import TEMPLATE_VARIABLE_KEYS, CUSTOM_TEXT_KEY_DISPLAY, DEFAULT_TEXT_PLACEHOLDER_VALUE
import json
import os

# Choices for font, size, and color
FONT_CHOICES = ['arial', 'timesnewroman', 'couriernew']
SIZE_CHOICES = ['12', '16', '24', '32']
COLOR_CHOICES = [('Black', (0,0,0)), ('Red', (220,0,0)), ('Blue', (0,0,220)), ('Green', (0,180,0))]

# These will be set by the caller
font_menu_panel = None
font_dropdown = None
size_dropdown = None
size_input = None
color_dropdown = None
xy_label = None
note_box = None
padding_inputs = {}
text_node_remove_btn = None
template_key_dropdown = None

ICON_TRASH_PATH = 'app/assets/icon_trash.png'

# Add global flag for custom key input focus
is_editing_custom_key_input = False
custom_key_input = None  # Make this global so we can check focus

# Add a global for the example value label
example_value_label = None

# Load and flatten template keys with example values
TEMPLATE_KEYS_PATH = os.path.join('configs', 'template_keys.json')
def flatten_keys(d, prefix=''):
    items = []
    if isinstance(d, dict):
        for k, v in d.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.extend(flatten_keys(v, new_prefix))
            else:
                items.append((new_prefix, v))
    return items
try:
    with open(TEMPLATE_KEYS_PATH, 'r', encoding='utf-8') as f:
        template_keys_data = json.load(f)
    FLATTENED_TEMPLATE_KEYS = flatten_keys(template_keys_data)
except Exception as e:
    print(f"[ui_text_properties] Failed to load template_keys.json: {e}")
    FLATTENED_TEMPLATE_KEYS = []

def show_font_menu(el, element_rect=None, manager=None):
    global font_menu_panel, font_dropdown, size_dropdown, color_dropdown, xy_label, note_box, padding_inputs, text_node_remove_btn, template_key_dropdown, size_input, custom_key_input, example_value_label
    if font_menu_panel:
        font_menu_panel.kill()
        font_menu_panel = None
    if element_rect is None or manager is None:
        return
    panel_x = element_rect.right + 20
    panel_y = element_rect.top
    panel_w = 360
    panel_h = 310
    font_menu_panel = UIPanel(relative_rect=pygame.Rect(panel_x, panel_y, panel_w, panel_h), manager=manager, starting_height=2, object_id='#text_node_properties')
    
    current_y = 5
    UILabel(relative_rect=pygame.Rect(10, current_y, 200, 24), text='Text Node Properties', manager=manager, container=font_menu_panel)
    current_y += 30

    # --- New custom key input row ---
    UILabel(relative_rect=pygame.Rect(10, current_y, 80, 24), text='New Key:', manager=manager, container=font_menu_panel)
    custom_key_input = UITextEntryLine(pygame.Rect(90, current_y, panel_w - 150, 30), manager, font_menu_panel)
    custom_key_input.set_text(el.get('value', ''))
    plus_btn = UIButton(pygame.Rect(panel_w - 50, current_y, 40, 30), '+', manager, font_menu_panel, object_id='#add_custom_key')
    current_y += 40

    # --- Data Key Dropdown row ---
    UILabel(relative_rect=pygame.Rect(10, current_y, 80, 24), text='Data Key:', manager=manager, container=font_menu_panel)
    current_value = el.get('value', '')
    # Build dropdown options: 'key (example)'
    dropdown_options = [f"{k} ({v})" for k, v in FLATTENED_TEMPLATE_KEYS]
    key_to_option = {k: f"{k} ({v})" for k, v in FLATTENED_TEMPLATE_KEYS}
    option_to_key = {f"{k} ({v})": k for k, v in FLATTENED_TEMPLATE_KEYS}
    # Add custom key display if current value is not in template keys
    if current_value and current_value not in key_to_option:
        dropdown_options.append(current_value)
        initial_key_selection = current_value
    elif current_value in key_to_option:
        initial_key_selection = key_to_option[current_value]
    else:
        initial_key_selection = dropdown_options[0] if dropdown_options else ''
    template_key_dropdown = UIDropDownMenu(
        options_list=dropdown_options,
        starting_option=initial_key_selection,
        relative_rect=pygame.Rect(90, current_y, panel_w - 100, 30),
        manager=manager,
        container=font_menu_panel,
        object_id='#template_key_dropdown'
    )
    # Store mapping for use in event handler
    template_key_dropdown._option_to_key = option_to_key
    example_value_label = UILabel(
        relative_rect=pygame.Rect(90, current_y, panel_w - 100, 24),
        text='',
        manager=manager,
        container=font_menu_panel
    )
    # Set initial example value
    selected_option = template_key_dropdown.selected_option
    example_value = ''
    if hasattr(template_key_dropdown, '_option_to_key'):
        key = template_key_dropdown._option_to_key.get(selected_option, selected_option)
        for k, v in FLATTENED_TEMPLATE_KEYS:
            if k == key:
                example_value = str(v)
                break
        else:
            example_value = 'No example value'
    example_value_label.set_text(f"Example: {example_value}")
    current_y += 28

    font_dropdown = pygame_gui.elements.UIDropDownMenu(FONT_CHOICES, el.get('font', 'arial'), pygame.Rect(10, current_y, 140, 30), manager, container=font_menu_panel)
    size_input_local = UITextEntryLine(pygame.Rect(160, current_y, 60, 30), manager, font_menu_panel)
    size_input_local.set_text(str(el.get('font_size', 18)))
    size_input = size_input_local
    size_dropdown = None
    color_dropdown = pygame_gui.elements.UIDropDownMenu([c[0] for c in COLOR_CHOICES], 'Black', pygame.Rect(10, current_y + 40, 80, 30), manager, container=font_menu_panel)
    # Show x/y coordinates
    x = int(el.get('x', 0) / 2)
    y = int(el.get('y', 0) / 2)
    xy_label = UILabel(relative_rect=pygame.Rect(110, current_y + 40, 120, 30), text=f"x: {x}  y: {y}", manager=manager, container=font_menu_panel)
    # Padding inputs
    padding = el.get('padding', {'left': 0, 'top': 0, 'right': 0, 'bottom': 0})
    padding_inputs = {}
    UILabel(pygame.Rect(10, current_y + 80, 60, 24), 'Padding:', manager, font_menu_panel)
    for i, side in enumerate(['left', 'top', 'right', 'bottom']):
        UILabel(pygame.Rect(10 + i*60, current_y + 105, 50, 20), side.capitalize(), manager, font_menu_panel)
        entry = UITextEntryLine(pygame.Rect(10 + i*60, current_y + 125, 50, 28), manager, font_menu_panel)
        entry.set_text(str(int(padding.get(side, 0))))
        padding_inputs[side] = entry
    # Remove button (trash icon)
    try:
        trash_icon = pygame.image.load(ICON_TRASH_PATH).convert_alpha()
    except Exception:
        trash_icon = None
    text_node_remove_btn = UIButton(pygame.Rect(panel_w-50, panel_h-50, 40, 40), '', manager, font_menu_panel, object_id='#remove_text_node')
    if trash_icon:
        text_node_remove_btn.set_image(trash_icon)
        text_node_remove_btn.set_text('')  # Ensure no text overlays icon
    
    # Convert to Obscure button
    convert_btn = UIButton(pygame.Rect(10, panel_h-50, 160, 40), 'Convert to Obscure', manager, font_menu_panel, object_id='#convert_to_obscure')
    
    # Replace UITextBox with UILabels for the note
    note_line_1_y = current_y + 150  # Y position of the first line of the note
    note_line_height = 20  # Approximate height for a UILabel line
    
    UILabel(relative_rect=pygame.Rect(10, note_line_1_y, panel_w - 20, note_line_height),
            text="Enter a <TEMPLATE_VALUE> that will be",
            manager=manager,
            container=font_menu_panel)
    
    UILabel(relative_rect=pygame.Rect(10, note_line_1_y + note_line_height, panel_w - 20, note_line_height),
            text="replaced by automated strings.",
            manager=manager,
            container=font_menu_panel)

    # Add focus/blur event handlers for the custom key input
    def on_focus():
        global is_editing_custom_key_input
        is_editing_custom_key_input = True
    def on_blur():
        global is_editing_custom_key_input
        is_editing_custom_key_input = False


def hide_font_menu():
    global font_menu_panel
    if font_menu_panel:
        font_menu_panel.kill()
        font_menu_panel = None

def handle_font_menu_event(event, editing_idx, config, page_num):
    global font_dropdown, size_dropdown, color_dropdown, template_key_dropdown, size_input, example_value_label
    if font_menu_panel is None:
        return False
    if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
        if event.ui_element == font_dropdown:
            if editing_idx is not None:
                config['pages'][page_num]['elements'][editing_idx]['font'] = event.text
                return True
        elif event.ui_element == color_dropdown:
            if editing_idx is not None:
                color_map = dict(COLOR_CHOICES)
                config['pages'][page_num]['elements'][editing_idx]['font_color'] = color_map.get(event.text, (0,0,0))
                return True
        elif event.ui_element == template_key_dropdown:
            if editing_idx is not None:
                # Store only the key, not the example value
                selected_option = event.text
                key = template_key_dropdown._option_to_key.get(selected_option, selected_option)
                config['pages'][page_num]['elements'][editing_idx]['value'] = key
                # Update example value label
                example_value = ''
                for k, v in FLATTENED_TEMPLATE_KEYS:
                    if k == key:
                        example_value = str(v)
                        break
                else:
                    example_value = 'No example value'
                if example_value_label:
                    example_value_label.set_text(f"Example: {example_value}")
                return True
    # Handle font size input change
    if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
        if hasattr(event, 'ui_element') and hasattr(event.ui_element, 'get_text'):
            # Check if this is the size input
            if editing_idx is not None and event.ui_element == size_input:
                try:
                    new_size = int(event.text)
                    config['pages'][page_num]['elements'][editing_idx]['font_size'] = new_size
                    return True
                except ValueError:
                    pass  # Ignore invalid input
    if event.type == pygame_gui.UI_BUTTON_PRESSED:
        if hasattr(event.ui_element, 'object_id') and event.ui_element.object_id == '#add_custom_key':
            # Get the text from the custom key input
            for element in font_menu_panel.get_container().get_descendants():
                if isinstance(element, UITextEntryLine):
                    new_key = element.get_text().strip()
                    break
            else:
                new_key = ''
            if new_key and new_key not in TEMPLATE_VARIABLE_KEYS:
                # Add to config and update config file
                TEMPLATE_VARIABLE_KEYS.append(new_key)
                # Save to config file (assume config is the loaded config dict)
                config_path = os.path.join('configs', f"{config['pdf_filename'].split('.')[0]}.json")
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=4)
                # Reload keys (simulate by reloading the panel)
                # You may want to call show_font_menu again or refresh the dropdown
                # For now, just print for debug
                print(f"Added new key: {new_key} and updated config file.")
                return True
    return False