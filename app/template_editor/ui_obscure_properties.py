import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UIDropDownMenu

OBSCURE_PROPS_PANEL_WIDTH = 220
OBSCURE_PROPS_PANEL_HEIGHT = 100

obscure_props_panel = None
obscure_mode_dropdown = None

OBSCURE_MODES = ['pixelate', 'blur', 'blacken']


def create_obscure_properties_panel(manager: pygame_gui.UIManager, panel_rect: pygame.Rect):
    global obscure_props_panel, obscure_mode_dropdown
    if obscure_props_panel is not None:
        obscure_props_panel.kill()
        obscure_props_panel = None
        obscure_mode_dropdown = None

    obscure_props_panel = UIPanel(relative_rect=panel_rect,
                                  manager=manager,
                                  object_id='#obscure_properties_panel')
    current_y = 10
    UILabel(relative_rect=pygame.Rect(10, current_y, 80, 30),
            text='Obscure Mode:',
            manager=manager,
            container=obscure_props_panel)
    obscure_mode_dropdown = UIDropDownMenu(
        options_list=OBSCURE_MODES,
        starting_option=OBSCURE_MODES[0],
        relative_rect=pygame.Rect(100, current_y, 100, 30),
        manager=manager,
        container=obscure_props_panel,
        object_id='#obscure_mode_dropdown'
    )
    return obscure_props_panel

def show_obscure_properties_panel(manager: pygame_gui.UIManager, element: dict, element_rect_on_screen: pygame.Rect):
    global obscure_props_panel, obscure_mode_dropdown
    panel_x = element_rect_on_screen.right + 10
    panel_y = element_rect_on_screen.top
    window_width, _ = manager.window_resolution
    if panel_x + OBSCURE_PROPS_PANEL_WIDTH > window_width:
        panel_x = element_rect_on_screen.left - OBSCURE_PROPS_PANEL_WIDTH - 10
        if panel_x < 0:
            panel_x = element_rect_on_screen.right + 10
    panel_rect = pygame.Rect(panel_x, panel_y, OBSCURE_PROPS_PANEL_WIDTH, OBSCURE_PROPS_PANEL_HEIGHT)
    if obscure_props_panel is None or not obscure_props_panel.alive():
        create_obscure_properties_panel(manager, panel_rect)
    else:
        obscure_props_panel.set_relative_position((panel_x, panel_y))
        obscure_props_panel.show()
    # Set dropdown to current mode
    mode = element.get('mode', 'pixelate')
    if obscure_mode_dropdown:
        try:
            obscure_mode_dropdown.selected_option = mode
            if hasattr(obscure_mode_dropdown, 'set_selected_option'):
                obscure_mode_dropdown.set_selected_option(mode)
        except Exception:
            pass
    if obscure_props_panel:
        obscure_props_panel.focus()

def hide_obscure_properties_panel():
    global obscure_props_panel
    if obscure_props_panel is not None and obscure_props_panel.alive():
        obscure_props_panel.hide()

def handle_obscure_properties_event(event: pygame.event.Event, editing_idx: int, config: dict, page_num: int) -> bool:
    global obscure_mode_dropdown
    if editing_idx is None or editing_idx >= len(config['pages'][page_num]['elements']):
        return False
    current_element = config['pages'][page_num]['elements'][editing_idx]
    if current_element.get('type') != 'obscure':
        return False
    if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
        ui_element = event.ui_element
        if hasattr(ui_element, 'object_ids') and ui_element.object_ids and ui_element.object_ids[-1] == '#obscure_mode_dropdown':
            selected_mode = ui_element.selected_option
            current_element['mode'] = selected_mode
            return True
    return False 