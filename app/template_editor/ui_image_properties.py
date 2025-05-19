import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UITextEntryLine

IMAGE_PROPS_PANEL_WIDTH = 250
IMAGE_PROPS_PANEL_HEIGHT = 200 # Adjust as needed
PADDING_INPUT_WIDTH = 50
LABEL_WIDTH = 100

image_props_panel = None
image_props_inputs = {} # To store references to input fields

def create_image_properties_panel(manager: pygame_gui.UIManager, panel_rect: pygame.Rect):
    """
    Creates the UI panel for editing image properties.
    """
    global image_props_panel, image_props_inputs
    if image_props_panel is not None:
        image_props_panel.kill()
        image_props_panel = None
        image_props_inputs = {}

    image_props_panel = UIPanel(relative_rect=panel_rect,
                                manager=manager,
                                object_id='#image_properties_panel')

    current_y = 10
    props_to_create = [
        ('padding_top', 'Padding Top:'),
        ('padding_right', 'Padding Right:'),
        ('padding_bottom', 'Padding Bottom:'),
        ('padding_left', 'Padding Left:')
    ]

    for name, text in props_to_create:
        UILabel(relative_rect=pygame.Rect(10, current_y, LABEL_WIDTH, 30),
                text=text,
                manager=manager,
                container=image_props_panel)
        
        input_field = UITextEntryLine(relative_rect=pygame.Rect(LABEL_WIDTH + 20, current_y, PADDING_INPUT_WIDTH, 30),
                                       manager=manager,
                                       container=image_props_panel,
                                       object_id=f'#img_prop_{name}')
        image_props_inputs[name] = input_field
        current_y += 40
        
    return image_props_panel

def show_image_properties_panel(manager: pygame_gui.UIManager, element: dict, element_rect_on_screen: pygame.Rect):
    """
    Shows the image properties panel and populates it with the element's current properties.
    Positions the panel relative to the selected element.
    """
    global image_props_panel, image_props_inputs
    
    panel_x = element_rect_on_screen.right + 10
    panel_y = element_rect_on_screen.top
    
    # Basic boundary check - prefer right, but move left if no space
    window_width, _ = manager.window_resolution
    if panel_x + IMAGE_PROPS_PANEL_WIDTH > window_width:
        panel_x = element_rect_on_screen.left - IMAGE_PROPS_PANEL_WIDTH - 10
        if panel_x < 0: # If still no space on left, fallback to just right of element
             panel_x = element_rect_on_screen.right + 10

    panel_rect = pygame.Rect(panel_x, panel_y, IMAGE_PROPS_PANEL_WIDTH, IMAGE_PROPS_PANEL_HEIGHT)

    if image_props_panel is None or not image_props_panel.alive():
        create_image_properties_panel(manager, panel_rect)
    else:
        # If panel exists, just move it
        image_props_panel.set_relative_position((panel_x, panel_y))
        image_props_panel.show()

    # Populate fields
    padding = element.get('padding', {'left': 0, 'top': 0, 'right': 0, 'bottom': 0})
    if image_props_inputs.get('padding_top'):
        image_props_inputs['padding_top'].set_text(str(padding.get('top', 0)))
    if image_props_inputs.get('padding_right'):
        image_props_inputs['padding_right'].set_text(str(padding.get('right', 0)))
    if image_props_inputs.get('padding_bottom'):
        image_props_inputs['padding_bottom'].set_text(str(padding.get('bottom', 0)))
    if image_props_inputs.get('padding_left'):
        image_props_inputs['padding_left'].set_text(str(padding.get('left', 0)))
    
    if image_props_panel:
        image_props_panel.focus()


def hide_image_properties_panel():
    """Hides the image properties panel."""
    global image_props_panel
    if image_props_panel is not None and image_props_panel.alive():
        image_props_panel.hide()
        # image_props_panel.kill() # Or kill if we want to recreate it each time
        # image_props_panel = None
        # image_props_inputs = {}

def update_image_properties_from_panel(element_config: dict, property_name: str, new_value_str: str):
    """Updates a specific padding property in the element's config."""
    try:
        new_value = int(new_value_str)
    except ValueError:
        print(f"Invalid value for {property_name}: {new_value_str}")
        return False # Indicate failure

    if 'padding' not in element_config:
        element_config['padding'] = {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}
    
    padding_key_map = {
        'padding_top': 'top',
        'padding_right': 'right',
        'padding_bottom': 'bottom',
        'padding_left': 'left',
    }
    
    if property_name in padding_key_map:
        element_config['padding'][padding_key_map[property_name]] = new_value
        print(f"Updated {property_name} to {new_value} for element. New padding: {element_config['padding']}")
        return True
    return False


def handle_image_properties_event(event: pygame.event.Event, editing_idx: int, config: dict, page_num: int) -> bool:
    """
    Handles UI events from the image properties panel.
    Returns True if the event was handled, False otherwise.
    """
    global image_props_panel, image_props_inputs

    if editing_idx is None or editing_idx >= len(config['pages'][page_num]['elements']):
        return False
        
    current_element = config['pages'][page_num]['elements'][editing_idx]
    if current_element.get('type') != 'image':
        return False # Should not happen if panel is shown correctly

    if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
        ui_element = event.ui_element
        prop_name_id = None
        if hasattr(ui_element, 'object_ids') and ui_element.object_ids and len(ui_element.object_ids) > 0:
            last_obj_id = ui_element.object_ids[-1] # e.g., '#img_prop_padding_top'
            if last_obj_id.startswith('#img_prop_'):
                prop_name_id = last_obj_id[len('#img_prop_'):] # e.g., 'padding_top'

        if prop_name_id and prop_name_id in image_props_inputs and ui_element == image_props_inputs[prop_name_id]:
            if update_image_properties_from_panel(current_element, prop_name_id, event.text):
                # Optionally, refresh the panel or element display if needed immediately
                return True
    
    # Handle panel close button if it's a UIWindow and has one, or other panel-specific events.
    # For UIPanel, closing is usually managed by hide_image_properties_panel() externally.

    return False 