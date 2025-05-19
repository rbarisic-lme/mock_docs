# put the code for the text properties floating menu here

import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UITextBox, UITextEntryLine, UIButton, UIDropDownMenu
from app.template_editor.constants import TEMPLATE_VARIABLE_KEYS, CUSTOM_TEXT_KEY_DISPLAY, DEFAULT_TEXT_PLACEHOLDER_VALUE

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

def show_font_menu(el, element_rect=None, manager=None):
    global font_menu_panel, font_dropdown, size_dropdown, color_dropdown, xy_label, note_box, padding_inputs, text_node_remove_btn, template_key_dropdown, size_input
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

    # Template Key Dropdown
    UILabel(relative_rect=pygame.Rect(10, current_y, 80, 24), text='Data Key:', manager=manager, container=font_menu_panel)
    current_value = el.get('value', '')
    initial_key_selection = current_value if current_value in TEMPLATE_VARIABLE_KEYS else CUSTOM_TEXT_KEY_DISPLAY
    template_key_dropdown = UIDropDownMenu(
        options_list=TEMPLATE_VARIABLE_KEYS,
        starting_option=initial_key_selection,
        relative_rect=pygame.Rect(90, current_y, panel_w - 100, 30),
        manager=manager,
        container=font_menu_panel,
        object_id='#template_key_dropdown'
    )
    current_y += 40

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

def hide_font_menu():
    global font_menu_panel
    if font_menu_panel:
        font_menu_panel.kill()
        font_menu_panel = None

def handle_font_menu_event(event, editing_idx, config, page_num):
    global font_dropdown, size_dropdown, color_dropdown, template_key_dropdown, size_input
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
                selected_key_text = event.text  # Text from the dropdown, e.g., "broker.email" or "<Custom Text>"
                config['pages'][page_num]['elements'][editing_idx]['value'] = selected_key_text
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
    return False