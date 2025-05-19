import pygame
import pygame_gui
from pygame_gui.windows import UIFileDialog
from pygame_gui.elements import UITextEntryLine
import os
import pygame.surfarray
import numpy as np
import copy

from app.template_editor.constants import SCALE, ZOOM_LEVELS, DEFAULT_ZOOM_INDEX, HANDLE_SIZE, INPUT_IMG_DIR
from app.template_editor.elements import get_element_bounds, get_resize_handles
from app.template_editor.canvas import get_canvas_coords
from app.template_editor.ui_text_properties import hide_font_menu, show_font_menu, handle_font_menu_event
from app.template_editor.ui_image_properties import show_image_properties_panel, hide_image_properties_panel, handle_image_properties_event
from app.template_editor.ui_components import ImageFileSelectWindow
from app.template_editor import ui_text_properties # Ensure this import is present or adjust as needed
from app.template_editor.ui_obscure_properties import show_obscure_properties_panel, hide_obscure_properties_panel, handle_obscure_properties_event
from app.template_editor import ocr_utils

def handle_keyboard_event(event, state, manager: pygame_gui.UIManager):
    """Handle keyboard events"""
    if event.type == pygame.KEYDOWN:
        # Undo (Ctrl+Z)
        if event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL):
            undo_history(state)
            return True
        # Check if a pygame_gui text input element has focus
        focused_element = manager.get_focus_set()
        if focused_element is not None and isinstance(focused_element, UITextEntryLine):
            print(f"DEBUG: UITextEntryLine focused: {focused_element.object_ids if hasattr(focused_element, 'object_ids') else 'No ID'}. Key: {pygame.key.name(event.key)}")
            # If a UITextEntryLine is focused, pygame_gui is handling text input.
            # We should not process our application-level keyboard shortcuts for general key presses.
            # However, pygame_gui itself might not consume ALL keys (e.g. Escape for closing a window
            # might still need to be handled by the UIManager or specific window logic if not by default text input).
            # For general character input, this should be sufficient.
            # The manager.process_events(event) call in app.py handles passing the event to the focused widget.
            return True # Indicate event is handled by the focused UI text input element.

        # If no UI text input is active, proceed with existing application-level keyboard handling.
        if event.key == pygame.K_ESCAPE:
            if state['text_edit_mode']:
                reset_text_edit_mode(state)
                pygame.mouse.set_visible(True)
            elif state['insert_mode']:
                state['insert_mode'] = None
                state['insert_image_path'] = None
                pygame.mouse.set_visible(True)
            else:
                state['running'] = False
            return True
        
        elif state['text_edit_mode'] and state['editing_idx'] is not None:
            editing_idx = state['editing_idx']
            editing_text = state['editing_text']
            text_cursor_pos = state['text_cursor_pos']
            
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                state['config']['pages'][state['page_num']]['elements'][editing_idx]['value'] = editing_text
                reset_text_edit_mode(state)
                pygame.mouse.set_visible(True)
            elif event.key == pygame.K_BACKSPACE:
                if text_cursor_pos > 0:
                    state['editing_text'] = editing_text[:text_cursor_pos-1] + editing_text[text_cursor_pos:]
                    state['text_cursor_pos'] -= 1
                    state['config']['pages'][state['page_num']]['elements'][editing_idx]['value'] = state['editing_text']
            elif event.key == pygame.K_DELETE:
                if text_cursor_pos < len(editing_text):
                    state['editing_text'] = editing_text[:text_cursor_pos] + editing_text[text_cursor_pos+1:]
                    state['config']['pages'][state['page_num']]['elements'][editing_idx]['value'] = state['editing_text']
            elif event.key == pygame.K_LEFT:
                state['text_cursor_pos'] = max(0, text_cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                state['text_cursor_pos'] = min(len(editing_text), text_cursor_pos + 1)
            elif event.key == pygame.K_HOME:
                state['text_cursor_pos'] = 0
            elif event.key == pygame.K_END:
                state['text_cursor_pos'] = len(editing_text)
            elif event.unicode and not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                state['editing_text'] = editing_text[:text_cursor_pos] + event.unicode + editing_text[text_cursor_pos:]
                state['text_cursor_pos'] += 1
                state['config']['pages'][state['page_num']]['elements'][editing_idx]['value'] = state['editing_text']
            return True
        
        elif not state['text_edit_mode']:
            if event.key == pygame.K_1:
                state['tool_mode'] = 'select'
                state['insert_mode'] = None
                pygame.mouse.set_visible(True)
                return True
            elif event.key == pygame.K_2:
                state['insert_mode'] = 'text'
                state['tool_mode'] = None
                pygame.mouse.set_visible(False)
                return True
            elif event.key == pygame.K_3:
                state['insert_mode'] = 'image_select'
                state['tool_mode'] = None
                pygame.mouse.set_visible(False)
                return True
            elif event.key == pygame.K_4: # Shortcut for Add Rectangle
                state['insert_mode'] = 'rectangle'
                state['tool_mode'] = None
                pygame.mouse.set_visible(False) # Or True, depending on desired UX for placement
                return True
            elif event.key == pygame.K_DELETE and state['tool_mode'] == 'select' and not state['text_edit_mode']:
                page_elements = state['config']['pages'][state['page_num']]['elements']
                selected_indices = sorted(set(state.get('selected_indices', [])), reverse=True)
                if selected_indices:
                    for idx in selected_indices:
                        if 0 <= idx < len(page_elements):
                            del page_elements[idx]
                    state['selected_indices'] = []
                    state['selected_idx'] = None
                    hide_font_menu()
                    hide_image_properties_panel()
                    hide_obscure_properties_panel()
                    print(f"Elements deleted. Remaining elements: {len(page_elements)}")
                    push_history(state)
                    state['ui_needs_update'] = True
                    return True
    
    return False

def handle_mousewheel_event(event, state):
    """Handle mouse wheel events for zooming"""
    if event.type == pygame.MOUSEWHEEL:
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_CTRL:
            if event.y > 0 and state['zoom_idx'] < len(ZOOM_LEVELS) - 1:
                state['zoom_idx'] += 1
            elif event.y < 0 and state['zoom_idx'] > 0:
                state['zoom_idx'] -= 1
            state['zoom'] = ZOOM_LEVELS[state['zoom_idx']]
            return True
    return False

def handle_mousebuttondown(event, state, window, manager: pygame_gui.UIManager):
    """Handle mouse button down events"""
    if event.type != pygame.MOUSEBUTTONDOWN:
        return False
    
    # Check if a pygame_gui UI element is currently under the mouse cursor.
    if manager.get_hovering_any_element():
        return True

    mx, my = event.pos
    canvas_w, canvas_h = state['canvas_size']
    scaled_w, scaled_h = int(canvas_w * state['zoom']), int(canvas_h * state['zoom'])
    win_w, win_h = window.get_width(), window.get_height()
    canvas_x = (win_w - scaled_w) // 2 + state['pan_x']
    canvas_y = (win_h - scaled_h) // 2 + state['pan_y']
    cx, cy = get_canvas_coords(mx, my, canvas_x, canvas_y, state['zoom'])
    handled = False

    # --- Marquee or single select logic ---
    if event.button == 1 and state['tool_mode'] == 'select' and not state['insert_mode'] and not state['text_edit_mode']:
        # Check if click is on any element or handle
        hit_idx = None
        for idx, el in enumerate(state['config']['pages'][state['page_num']]['elements']):
            x_el, y_el, w_el, h_el, _, _ = get_element_bounds(el, SCALE/state['zoom'])
            if x_el <= cx <= x_el + w_el and y_el <= cy <= y_el + h_el:
                hit_idx = idx
                break
        if hit_idx is not None:
            # Single select
            state['selected_indices'] = [hit_idx]
            state['selected_idx'] = hit_idx
            print(f"[DEBUG] selected_indices updated: {state['selected_indices']}")
            state['ui_needs_update'] = True
        else:
            # Not on any element, start marquee
            state['marquee_selecting'] = True
            state['marquee_start'] = (cx, cy)
            state['marquee_end'] = (cx, cy)
            state['selected_indices'] = []
            state['selected_idx'] = None
            handled = True

    # --- Show text node properties window if single text node is selected ---
    if state['tool_mode'] == 'select' and not state['insert_mode'] and not state['text_edit_mode']:
        selected_indices = state.get('selected_indices', [])
        if len(selected_indices) == 1:
            idx = selected_indices[0]
            el = state['config']['pages'][state['page_num']]['elements'][idx]
            if el.get('type') == 'text':
                # Show font menu for this text node
                bounds_x, bounds_y, bounds_w, bounds_h, _, _ = get_element_bounds(el, SCALE/state['zoom'])
                element_screen_x = canvas_x + bounds_x * state['zoom']
                element_screen_y = canvas_y + bounds_y * state['zoom']
                element_rect = pygame.Rect(element_screen_x, element_screen_y, bounds_w * state['zoom'], bounds_h * state['zoom'])
                show_font_menu(el, element_rect, manager)
            else:
                hide_font_menu()
        else:
            hide_font_menu()
    # --- End show text node properties window ---

    if event.button == 1:  # Left mouse button
        if state['insert_mode'] == 'text':
            new_el = {
                'type': 'text',
                'x': cx,
                'y': cy,
                'width': 150,  # Default bounding box width
                'height': 50, # Default bounding box height
                'font_size': 18,
                'value': 'Sample Text',
                # 'padding': {'left': 8, 'top': 8, 'right': 8, 'bottom': 8}, # REMOVE PADDING
                'background_color': [255, 255, 255], # Default white background for the box
                'font_color': [0,0,0],
                'text_align_h': 'left', # Default horizontal alignment
                'text_align_v': 'top'   # Default vertical alignment
            }
            state['config']['pages'][state['page_num']]['elements'].append(new_el)
            new_idx = len(state['config']['pages'][state['page_num']]['elements']) - 1
            
            state['selected_idx'] = new_idx      # Select the new element
            state['tool_mode'] = 'select'        # Switch to select mode
            state['insert_mode'] = None          # Exit insert mode
            pygame.mouse.set_visible(True)     # Show mouse cursor
            
            # Ensure text editing mode is fully reset and font menu is hidden
            reset_text_edit_mode(state)
            
            push_history(state)
            state['ui_needs_update'] = True
            return True

        elif state['insert_mode'] == 'image' and state['insert_image_path']:
            new_el = {
                'type': 'image',
                'x': cx,
                'y': cy,
                'width': 200,
                'height': 200,
                'value': state['insert_image_path'],
                'padding': {'left': 0, 'top': 0, 'right': 0, 'bottom': 0} # Initialize with default padding
            }
            state['config']['pages'][state['page_num']]['elements'].append(new_el)
            new_idx = len(state['config']['pages'][state['page_num']]['elements']) - 1

            state['selected_idx'] = new_idx      # Select the new image
            state['tool_mode'] = 'select'        # Switch to select mode
            state['insert_mode'] = None          # Exit insert mode
            state['insert_image_path'] = None  # Clear image path
            pygame.mouse.set_visible(True)     # Show mouse cursor
            hide_font_menu()                   # Ensure font menu is hidden
            
            # Show image properties for the newly added and selected image
            selected_el_for_props = state['config']['pages'][state['page_num']]['elements'][new_idx]
            el_x_bounds, el_y_bounds, el_w_bounds, el_h_bounds, _, _ = get_element_bounds(selected_el_for_props, SCALE/state['zoom'])
            element_screen_x = canvas_x + el_x_bounds * state['zoom']
            element_screen_y = canvas_y + el_y_bounds * state['zoom']
            element_rect_display = pygame.Rect(element_screen_x, element_screen_y, el_w_bounds * state['zoom'], el_h_bounds * state['zoom'])
            show_image_properties_panel(manager, selected_el_for_props, element_rect_display)
            state['editing_idx'] = new_idx # Set editing_idx for property panel to use

            push_history(state)
            state['ui_needs_update'] = True
            return True

        elif state['insert_mode'] == 'rectangle':
            new_el = {
                'type': 'rectangle',
                'x': cx,
                'y': cy,
                'width': 100, # Default width
                'height': 50, # Default height
                'background_color': [200, 200, 200] # Default light gray
            }
            state['config']['pages'][state['page_num']]['elements'].append(new_el)
            state['selected_idx'] = len(state['config']['pages'][state['page_num']]['elements']) - 1 # Select new rect
            state['insert_mode'] = None
            state['tool_mode'] = 'select' # Switch to select mode
            pygame.mouse.set_visible(True)
            hide_font_menu()
            hide_image_properties_panel() # Hide panels if a rect is added
            push_history(state)
            state['ui_needs_update'] = True
            return True

        elif state['insert_mode'] == 'obscure':
            new_el = {
                'type': 'obscure',
                'x': cx,
                'y': cy,
                'width': 100,
                'height': 50,
                'mode': 'pixelate'  # default mode
            }
            state['config']['pages'][state['page_num']]['elements'].append(new_el)
            new_idx = len(state['config']['pages'][state['page_num']]['elements']) - 1
            state['selected_idx'] = new_idx
            state['insert_mode'] = None
            state['tool_mode'] = 'select'
            pygame.mouse.set_visible(True)
            hide_font_menu()
            hide_image_properties_panel()
            # Show obscure properties panel
            selected_el_for_props = state['config']['pages'][state['page_num']]['elements'][new_idx]
            el_x_bounds, el_y_bounds, el_w_bounds, el_h_bounds, _, _ = get_element_bounds(selected_el_for_props, SCALE/state['zoom'])
            element_screen_x = canvas_x + el_x_bounds * state['zoom']
            element_screen_y = canvas_y + el_y_bounds * state['zoom']
            element_rect_display = pygame.Rect(element_screen_x, element_screen_y, el_w_bounds * state['zoom'], el_h_bounds * state['zoom'])
            show_obscure_properties_panel(manager, selected_el_for_props, element_rect_display)
            state['editing_idx'] = new_idx # Ensure editing_idx is set for obscure
            hide_font_menu()
            hide_image_properties_panel()
            push_history(state)
            state['ui_needs_update'] = True
            return True

        elif state['tool_mode'] == 'select' and not state['insert_mode'] and not state['text_edit_mode']:
            clicked_on_something = False # General flag if any interaction happened
            # Check for resize handle clicks FIRST
            for idx, el in enumerate(state['config']['pages'][state['page_num']]['elements']):
                handles = get_resize_handles(el, SCALE/state['zoom'])
                for hidx, (hx, hy) in enumerate(handles):
                    if abs(cx - hx) <= HANDLE_SIZE / state['zoom'] and abs(cy - hy) <= HANDLE_SIZE / state['zoom']:
                        if hidx == 4 and el.get('type') == 'text': # NE handle (index 4) for font size, only for text
                            state['font_resizing_mode'] = (idx, hidx)
                            state['selected_idx'] = idx
                            state['font_resizing'] = True
                            state['font_resize_start_mouse'] = (cx, cy)
                            state['orig_font_size'] = el.get('font_size', 18)
                        elif hidx != 4: # Existing N,S,E,W resize handles (not font size handle)
                            state['resize_mode'] = (idx, hidx)
                            state['selected_idx'] = idx
                            state['resizing'] = True
                            state['resize_start_mouse'] = (cx, cy)
                            state['orig_rect'] = (el['x'], el['y'], el.get('width',100), el.get('height',30))
                            if el.get('type') == 'text':
                                font_name_orig = el.get('font', 'arial')
                                font_size_orig = el.get('font_size', 18)
                                text_value_orig = el.get('value', '')
                                try:
                                    orig_font = pygame.font.SysFont(font_name_orig, font_size_orig)
                                except pygame.error:
                                    orig_font = pygame.font.Font(None, font_size_orig)
                                orig_text_surf = orig_font.render(text_value_orig, True, (0,0,0))
                                state['orig_text_content_dims'] = (orig_text_surf.get_width(), orig_text_surf.get_height())
                        clicked_on_something = True; break
                if clicked_on_something: break
            
            if clicked_on_something: # A handle was clicked
                handled = True
                # If a handle of an image was clicked, ensure its properties panel is shown
                if state['selected_idx'] is not None and state['config']['pages'][state['page_num']]['elements'][state['selected_idx']].get('type') == 'image':
                    selected_el_for_props = state['config']['pages'][state['page_num']]['elements'][state['selected_idx']]
                    el_x_bounds, el_y_bounds, el_w_bounds, el_h_bounds, _, _ = get_element_bounds(selected_el_for_props, SCALE/state['zoom'])
                    element_screen_x = canvas_x + el_x_bounds * state['zoom']
                    element_screen_y = canvas_y + el_y_bounds * state['zoom']
                    element_rect_display = pygame.Rect(element_screen_x, element_screen_y, el_w_bounds * state['zoom'], el_h_bounds * state['zoom'])
                    show_image_properties_panel(manager, selected_el_for_props, element_rect_display)
                    state['editing_idx'] = state['selected_idx'] # Keep editing_idx in sync for props
                    hide_font_menu()
                elif state['selected_idx'] is not None and state['config']['pages'][state['page_num']]['elements'][state['selected_idx']].get('type') == 'obscure':
                    selected_el_for_props = state['config']['pages'][state['page_num']]['elements'][state['selected_idx']]
                    el_x_bounds, el_y_bounds, el_w_bounds, el_h_bounds, _, _ = get_element_bounds(selected_el_for_props, SCALE/state['zoom'])
                    element_screen_x = canvas_x + el_x_bounds * state['zoom']
                    element_screen_y = canvas_y + el_y_bounds * state['zoom']
                    element_rect_display = pygame.Rect(element_screen_x, element_screen_y, el_w_bounds * state['zoom'], el_h_bounds * state['zoom'])
                    show_obscure_properties_panel(manager, selected_el_for_props, element_rect_display)
                    state['editing_idx'] = state['selected_idx'] # Ensure editing_idx is set for obscure
                    hide_font_menu()
                    hide_image_properties_panel()
                elif state['selected_idx'] is not None and state['config']['pages'][state['page_num']]['elements'][state['selected_idx']].get('type') == 'text':
                    hide_image_properties_panel() # Hide image panel if a text element's handle is clicked
                    hide_obscure_properties_panel()
                else: # Non-image, non-text selected via handle, or no selection change
                    hide_font_menu()
                    hide_image_properties_panel()
                    hide_obscure_properties_panel()

            else: # No handle was clicked, proceed with element selection (click-through)
                all_page_elements_with_indices = list(enumerate(state['config']['pages'][state['page_num']]['elements']))
                overlapping_elements_details = [] # List of (element_data, original_index)

                for original_idx, el_data in all_page_elements_with_indices:
                    x_el, y_el, w_el, h_el, _, _ = get_element_bounds(el_data, SCALE/state['zoom'])
                    if x_el <= cx <= x_el + w_el and y_el <= cy <= y_el + h_el:
                        overlapping_elements_details.append((el_data, original_idx))

                if not overlapping_elements_details:
                    state['selected_idx'] = None
                    hide_font_menu()
                    hide_image_properties_panel()
                    hide_obscure_properties_panel()
                    state['editing_idx'] = None # Clear editing_idx if nothing selected
                else:
                    def get_z_order(element_type):
                        if element_type == 'rectangle': return 0
                        if element_type == 'image': return 1
                        if element_type == 'text': return 2
                        return 3 # Default for others

                    overlapping_elements_details.sort(key=lambda item: (get_z_order(item[0].get('type')), item[1]))

                    current_selected_original_idx = state['selected_idx']
                    found_current_in_overlap_at_sorted_idx = -1
                    if current_selected_original_idx is not None:
                        for i, (el_data, original_idx) in enumerate(overlapping_elements_details):
                            if original_idx == current_selected_original_idx:
                                found_current_in_overlap_at_sorted_idx = i
                                break
                    
                    new_selected_original_idx = -1
                    if found_current_in_overlap_at_sorted_idx != -1:
                        next_sorted_idx = (found_current_in_overlap_at_sorted_idx + 1) % len(overlapping_elements_details)
                        new_selected_original_idx = overlapping_elements_details[next_sorted_idx][1]
                    else:
                        new_selected_original_idx = overlapping_elements_details[-1][1] # Topmost

                    state['selected_idx'] = new_selected_original_idx
                    newly_selected_el = state['config']['pages'][state['page_num']]['elements'][new_selected_original_idx]
                    state['editing_idx'] = new_selected_original_idx # Set editing_idx for potential property panel
                    
                    state['dragging'] = True
                    state['drag_start_mouse_canvas'] = (cx, cy)
                    state['drag_start_el_x'] = newly_selected_el['x']
                    state['drag_start_el_y'] = newly_selected_el['y']

                    current_time = pygame.time.get_ticks() / 1000
                    # Use a more specific state key for double click tracking to avoid conflict with general last_click_idx
                    if (newly_selected_el['type'] == 'text' and 
                        current_time - state.get('last_click_time_for_double_click', 0) < state['double_click_threshold'] and
                        state.get('last_click_idx_for_double_click') == new_selected_original_idx):
                        state['text_edit_mode'] = True
                        state['editing_idx'] = new_selected_original_idx
                        state['editing_text'] = newly_selected_el['value']
                        state['text_cursor_pos'] = len(state['editing_text'])
                        
                        el_x_bounds, el_y_bounds, el_w_bounds, el_h_bounds, _, _ = get_element_bounds(newly_selected_el, SCALE/state['zoom'])
                        element_screen_x = canvas_x + el_x_bounds * state['zoom']
                        element_screen_y = canvas_y + el_y_bounds * state['zoom']
                        element_rect_display = pygame.Rect(element_screen_x, element_screen_y, el_w_bounds * state['zoom'], el_h_bounds * state['zoom'])
                        show_font_menu(newly_selected_el, element_rect_display, manager)
                        hide_image_properties_panel() # Hide image panel if text edit starts
                    else:
                        # Not a double click or not a text element
                        if newly_selected_el.get('type') == 'image':
                            el_x_bounds, el_y_bounds, el_w_bounds, el_h_bounds, _, _ = get_element_bounds(newly_selected_el, SCALE/state['zoom'])
                            element_screen_x = canvas_x + el_x_bounds * state['zoom']
                            element_screen_y = canvas_y + el_y_bounds * state['zoom']
                            element_rect_display = pygame.Rect(element_screen_x, element_screen_y, el_w_bounds * state['zoom'], el_h_bounds * state['zoom'])
                            show_image_properties_panel(manager, newly_selected_el, element_rect_display)
                            hide_font_menu()
                        elif newly_selected_el.get('type') == 'obscure':
                            el_x_bounds, el_y_bounds, el_w_bounds, el_h_bounds, _, _ = get_element_bounds(newly_selected_el, SCALE/state['zoom'])
                            element_screen_x = canvas_x + el_x_bounds * state['zoom']
                            element_screen_y = canvas_y + el_y_bounds * state['zoom']
                            element_rect_display = pygame.Rect(element_screen_x, element_screen_y, el_w_bounds * state['zoom'], el_h_bounds * state['zoom'])
                            show_obscure_properties_panel(manager, newly_selected_el, element_rect_display)
                            state['editing_idx'] = new_selected_original_idx # Ensure editing_idx is set for obscure
                            hide_font_menu()
                            hide_image_properties_panel()
                        elif newly_selected_el.get('type') == 'text':
                             # If it is a text element but not double-clicked for editing, font menu should be hidden.
                             # If a properties panel for selected non-editing text is desired, it would be shown here.
                            hide_font_menu()
                            hide_image_properties_panel()
                            hide_obscure_properties_panel()
                        else: # Other types like rectangle
                            hide_font_menu()
                            hide_image_properties_panel()
                            hide_obscure_properties_panel()
                    
                    # Store information for the *next* potential double click on this element
                    state['last_click_idx_for_double_click'] = new_selected_original_idx
                
                handled = True # Click was processed for selection/deselection

    elif not state['insert_mode'] and not state['text_edit_mode'] and event.button in (2, 3):
        state['canvas_drag'] = True
        state['canvas_drag_start'] = (mx, my)
        state['pan_start'] = (state['pan_x'], state['pan_y'])
        handled = True
    
    if event.button == 1:
        state['last_click_time'] = pygame.time.get_ticks() / 1000 # General last click time
        state['last_click_time_for_double_click'] = state['last_click_time'] # Also update for double click logic
        state['last_click_pos'] = (mx, my)
        # state['last_click_idx'] is no longer the primary for double click, use state['last_click_idx_for_double_click'] set above.
        # If you need a general last_click_idx for other purposes, it could be set to state['selected_idx'] here:
        # if not state['text_edit_mode']:
        # state['last_click_idx'] = state['selected_idx']

    return handled

def handle_mousebuttonup(event, state):
    """Handle mouse button up events"""
    if event.type == pygame.MOUSEBUTTONUP:
        # --- Marquee selection end ---
        if state.get('marquee_selecting'):
            start = state.get('marquee_start')
            end = state.get('marquee_end')
            if start and end:
                x0, y0 = start
                x1, y1 = end
                # If click (no drag), treat as single click (already handled in mousebuttondown)
                if abs(x0 - x1) < 2 and abs(y0 - y1) < 2:
                    pass # Do nothing, already handled
                else:
                    x_min, x_max = min(x0, x1), max(x0, x1)
                    y_min, y_max = min(y0, y1), max(y0, y1)
                    selected = []
                    for idx, el in enumerate(state['config']['pages'][state['page_num']]['elements']):
                        x_el, y_el, w_el, h_el, _, _ = get_element_bounds(el, SCALE/state['zoom'])
                        # Check intersection
                        if not (x_el + w_el < x_min or x_el > x_max or y_el + h_el < y_min or y_el > y_max):
                            selected.append(idx)
                    state['selected_indices'] = selected
                    state['selected_idx'] = selected[0] if selected else None
                    print(f"[DEBUG] selected_indices updated (marquee): {state['selected_indices']}")
                    state['ui_needs_update'] = True
            state['marquee_selecting'] = False
            state['marquee_start'] = None
            state['marquee_end'] = None
            return True
        # --- End marquee selection end ---
        state['dragging'] = False
        state['canvas_drag'] = False
        state['resizing'] = False
        state['resize_mode'] = None
        state['font_resizing'] = False 
        state['font_resizing_mode'] = None 
        return True
    return False

def handle_mousemotion(event, state, window, manager):
    """Handle mouse motion events"""
    if event.type != pygame.MOUSEMOTION:
        return False
    
    mx, my = event.pos
    state['mouse_screen_pos'] = (mx, my)
    
    canvas_w, canvas_h = state['canvas_size']
    scaled_w, scaled_h = int(canvas_w * state['zoom']), int(canvas_h * state['zoom'])
    win_w, win_h = window.get_width(), window.get_height()
    canvas_x = (win_w - scaled_w) // 2 + state['pan_x']
    canvas_y = (win_h - scaled_h) // 2 + state['pan_y']
    cx, cy = get_canvas_coords(mx, my, canvas_x, canvas_y, state['zoom'])
    state['mouse_canvas_pos'] = (cx, cy)
    handled = False

    # --- Marquee selection update ---
    if state.get('marquee_selecting'):
        state['marquee_end'] = (cx, cy)
        handled = True
    # --- End marquee selection update ---

    if state['resizing'] and state['resize_mode'] is not None:
        handle_resize_motion(state, cx, cy)
        handled = True
    elif state['font_resizing'] and state['font_resizing_mode'] is not None: 
        handle_font_resize_motion(state, cx, cy) 
        handled = True
    elif state['dragging'] and state['selected_idx'] is not None:
        # Use new dragging logic
        idx = state['selected_idx']
        el = state['config']['pages'][state['page_num']]['elements'][idx]
        
        dx = cx - state['drag_start_mouse_canvas'][0]
        dy = cy - state['drag_start_mouse_canvas'][1]
        
        el['x'] = state['drag_start_el_x'] + dx
        el['y'] = state['drag_start_el_y'] + dy
        
        # If text edit mode was active for this element, update font menu position
        if state['text_edit_mode'] and state['editing_idx'] == idx and el['type'] == 'text':
            # Re-fetch element bounds as its x,y (text anchor) has changed
            bounds_x, bounds_y, bounds_w, bounds_h, _, _ = get_element_bounds(el, SCALE/state['zoom'])
            element_screen_x = canvas_x + bounds_x * state['zoom']
            element_screen_y = canvas_y + bounds_y * state['zoom']
            element_rect = pygame.Rect(element_screen_x, element_screen_y, bounds_w * state['zoom'], bounds_h * state['zoom'])
            show_font_menu(el, element_rect, manager) # show_font_menu should handle repositioning
            
        handled = True
    elif state['canvas_drag']:
        dx_pan = mx - state['canvas_drag_start'][0]
        dy_pan = my - state['canvas_drag_start'][1]
        state['pan_x'] = state['pan_start'][0] + dx_pan
        state['pan_y'] = state['pan_start'][1] + dy_pan
        handled = True
    
    return handled

def handle_resize_motion(state, cx, cy):
    idx, hidx = state['resize_mode']
    el = state['config']['pages'][state['page_num']]['elements'][idx]

    if 'orig_rect' not in state or 'resize_start_mouse' not in state:
        print("Error: Missing original state for resize. Aborting resize motion.")
        return

    orig_x, orig_y, orig_w, orig_h = state['orig_rect']
    start_mouse_x, start_mouse_y = state['resize_start_mouse']

    current_mouse_x_base = cx
    current_mouse_y_base = cy

    min_dim_base = 10 # Min width/height for the element box in base units

    new_x, new_y, new_w, new_h = orig_x, orig_y, orig_w, orig_h

    if el.get('type') == 'image':
        if orig_w == 0 or orig_h == 0: 
            orig_aspect_ratio = 1.0 # Default aspect ratio if original dimensions are zero
        else:
            orig_aspect_ratio = orig_w / orig_h

        # Initialize with current values, these will be updated by handle logic
        temp_new_x, temp_new_y, temp_new_w, temp_new_h = orig_x, orig_y, orig_w, orig_h

        if hidx == 0: # N (Top handle)
            delta_y = current_mouse_y_base - start_mouse_y
            temp_new_h = orig_h - delta_y
            temp_new_y = orig_y + delta_y # Top edge moves with mouse
        elif hidx == 2: # S (Bottom handle)
            delta_y = current_mouse_y_base - start_mouse_y
            temp_new_h = orig_h + delta_y
            # temp_new_y remains orig_y (top edge fixed)
        elif hidx == 3: # W (Left handle)
            delta_x = current_mouse_x_base - start_mouse_x
            temp_new_w = orig_w - delta_x
            temp_new_x = orig_x + delta_x # Left edge moves with mouse
        elif hidx == 1: # E (Right handle)
            delta_x = current_mouse_x_base - start_mouse_x
            temp_new_w = orig_w + delta_x
            # temp_new_x remains orig_x (left edge fixed)
        else:
            # This case should ideally not be reached if font resizing is handled separately
            # and only N,S,E,W handles are used for box resizing of images.
            # Fallback to non-aspect ratio resize for other handles if any.
            pass # Will proceed to the generic logic below if not returned

        # Apply aspect ratio and min dimensions, then update el and return
        if hidx == 0 or hidx == 2: # Primarily height change (N, S handles)
            temp_new_h = max(min_dim_base, temp_new_h)
            calculated_w = temp_new_h * orig_aspect_ratio
            
            if calculated_w < min_dim_base:
                temp_new_w = min_dim_base
                temp_new_h = temp_new_w / orig_aspect_ratio if orig_aspect_ratio != 0 else min_dim_base
            else:
                temp_new_w = calculated_w
            
            # Adjust x position to maintain horizontal center based on original center
            original_center_x = orig_x + orig_w / 2.0
            temp_new_x = original_center_x - temp_new_w / 2.0

        elif hidx == 3 or hidx == 1: # Primarily width change (W, E handles)
            temp_new_w = max(min_dim_base, temp_new_w)
            calculated_h = temp_new_w / orig_aspect_ratio if orig_aspect_ratio != 0 else min_dim_base
            
            if calculated_h < min_dim_base:
                temp_new_h = min_dim_base
                temp_new_w = temp_new_h * orig_aspect_ratio
            else:
                temp_new_h = calculated_h

            # Adjust y position to maintain vertical center based on original center
            original_center_y = orig_y + orig_h / 2.0
            temp_new_y = original_center_y - temp_new_h / 2.0

        # Final assignment to new_x, new_y, new_w, new_h for images
        new_x, new_y, new_w, new_h = temp_new_x, temp_new_y, temp_new_w, temp_new_h
        
        # Update element and return for image type
        el['x'] = new_x
        el['y'] = new_y
        el['width'] = new_w
        el['height'] = new_h
        return

    # --- Existing generic resize logic for non-image elements --- 
    if hidx == 0: # N (Top handle)
        delta_y = current_mouse_y_base - start_mouse_y
        new_y = orig_y + delta_y
        new_h = orig_h - delta_y
        if new_h < min_dim_base:
            new_h = min_dim_base
            new_y = orig_y + orig_h - min_dim_base

    elif hidx == 2: # S (Bottom handle)
        delta_y = current_mouse_y_base - start_mouse_y
        new_h = orig_h + delta_y
        if new_h < min_dim_base:
            new_h = min_dim_base
        
    elif hidx == 3: # W (Left handle)
        delta_x = current_mouse_x_base - start_mouse_x
        new_x = orig_x + delta_x
        new_w = orig_w - delta_x
        if new_w < min_dim_base:
            new_w = min_dim_base
            new_x = orig_x + orig_w - min_dim_base
        
    elif hidx == 1: # E (Right handle)
        delta_x = current_mouse_x_base - start_mouse_x
        new_w = orig_w + delta_x
        if new_w < min_dim_base:
            new_w = min_dim_base

    # Update element with new box dimensions and position
    el['x'] = new_x
    el['y'] = new_y
    el['width'] = new_w
    el['height'] = new_h
    # 'padding' key is no longer used for this type of resize.

def handle_font_resize_motion(state, cx, cy):
    """Handles font resizing based on mouse movement."""
    idx, _ = state['font_resizing_mode']
    el = state['config']['pages'][state['page_num']]['elements'][idx]

    if 'font_resize_start_mouse' not in state or 'orig_font_size' not in state:
        print("Error: Missing original state for font resize. Aborting font resize motion.")
        return

    start_mouse_x, start_mouse_y = state['font_resize_start_mouse']
    orig_font_size = state['orig_font_size']

    # Calculate change in X and Y position
    delta_x = cx - start_mouse_x # current_mouse_x_base (cx) is passed as first arg
    delta_y = cy - start_mouse_y # current_mouse_y_base (cy) is passed as second arg

    # Define sensitivity: how much mouse movement (in base units) changes font size by 1 point
    # Adjust sensitivity as needed. A smaller value means more sensitive.
    sensitivity = 5 
    
    # Combine deltas: dragging right (delta_x > 0) or up (delta_y < 0) increases size.
    # Dragging left (delta_x < 0) or down (delta_y > 0) decreases size.
    # For a top-right handle, outward drag is (positive delta_x, negative delta_y) -> increases size.
    # Inward drag is (negative delta_x, positive delta_y) -> decreases size.
    # So, (delta_x - delta_y) works well.
    combined_delta = delta_x - delta_y
    font_size_change = combined_delta / sensitivity

    new_font_size = orig_font_size + font_size_change
    
    # Clamp font size to reasonable limits (e.g., 6pt to 100pt)
    min_font_size = 6
    max_font_size = 100
    el['font_size'] = max(min_font_size, min(max_font_size, int(round(new_font_size))))
    
    # Since font size change might affect text content dimensions,
    # we might need to re-calculate padding if we want to maintain visual spacing,
    # or adjust background box if padding is meant to be fixed.
    # For now, let's assume the background box and padding are NOT automatically adjusted
    # when font size changes this way. The user can adjust them separately.

def handle_drag_motion(state, cx, cy, canvas_x, canvas_y, manager):
    # This function is now effectively handled inline within handle_mousemotion
    # We can keep it for structure or refactor handle_mousemotion to call it.
    # For now, the logic is moved into handle_mousemotion's 'elif state['dragging']' block.
    pass # Or remove if all logic is confirmed moved and working in handle_mousemotion

def reset_text_edit_mode(state):
    state['text_edit_mode'] = False
    state['editing_idx'] = None
    state['editing_text'] = ""
    state['text_cursor_pos'] = 0
    hide_font_menu()
    hide_image_properties_panel() # Also hide image panel when text edit mode resets
    hide_obscure_properties_panel() # Also hide obscure panel

def handle_ui_event(event, state, save_config_func, manager):
    """Handle UI events from pygame_gui"""
    if event.type == pygame.USEREVENT:
        if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            ui_element = event.ui_element
            button_id = "Unknown Button"
            if hasattr(ui_element, 'object_ids') and ui_element.object_ids and ui_element.object_ids[-1]:
                button_id = ui_element.object_ids[-1]
            elif hasattr(ui_element, 'text') and ui_element.text:
                button_id = ui_element.text
            print(f"[event_handlers.py] UI_BUTTON_PRESSED: {button_id}")
            if ui_element == state.get('btn_undo'):
                undo_history(state)
                return True
            elif ui_element == state.get('btn_minus') and state['zoom_idx'] > 0:
                state['zoom_idx'] -= 1; state['zoom'] = ZOOM_LEVELS[state['zoom_idx']]
            elif ui_element == state.get('btn_plus') and state['zoom_idx'] < len(ZOOM_LEVELS) - 1:
                state['zoom_idx'] += 1; state['zoom'] = ZOOM_LEVELS[state['zoom_idx']]
            elif ui_element == state.get('btn_actual'):
                state['zoom_idx'] = DEFAULT_ZOOM_INDEX; state['zoom'] = ZOOM_LEVELS[state['zoom_idx']]
            elif ui_element == state.get('btn_reset_pan'):
                state['pan_x'], state['pan_y'] = 0, 0
            elif ui_element == state.get('btn_add_text'):
                state['insert_mode'] = 'text'; state['tool_mode'] = None; pygame.mouse.set_visible(False)
            elif ui_element == state.get('btn_add_image'):
                try:
                    # Get full paths for image_files
                    image_files_full_paths = [
                        os.path.join(INPUT_IMG_DIR, f) 
                        for f in os.listdir(INPUT_IMG_DIR) 
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
                    ]
                    if image_files_full_paths:
                        # Use the new ImageFileSelectWindow
                        dialog_rect = pygame.Rect(0, 0, 500, 400) # Adjust size as needed
                        # Center the dialog on the screen using manager.window_resolution
                        screen_width, screen_height = manager.window_resolution
                        dialog_rect.center = (screen_width // 2, screen_height // 2)
                        state['image_select_dialog'] = ImageFileSelectWindow(
                            rect=dialog_rect,
                            manager=manager,
                            image_files=image_files_full_paths, # Pass full paths
                            input_img_dir=INPUT_IMG_DIR
                        )
                        state['insert_mode'] = 'image_select' # Keep this to signify selection process is active
                        state['tool_mode'] = None
                        pygame.mouse.set_visible(True)
                    else:
                        print(f'No images found in {INPUT_IMG_DIR}.')
                except FileNotFoundError:
                     print(f'Error: Directory {INPUT_IMG_DIR} not found.')
            elif ui_element == state.get('btn_add_rect'): # Handle new button
                state['insert_mode'] = 'rectangle'
                state['tool_mode'] = None
                pygame.mouse.set_visible(False) # Cursor invisible during placement
            elif ui_element == state.get('btn_prev_page'):
                if state['page_num'] > 0:
                    if state['text_edit_mode']: reset_text_edit_mode(state)
                    state['page_num'] -= 1
                    state['pan_x'], state['pan_y'] = 0,0 ; state['selected_idx'] = None
                    state['page_changed'] = True
            elif ui_element == state.get('btn_next_page'):
                if state['page_num'] < len(state['config']['pages']) - 1:
                    if state['text_edit_mode']: reset_text_edit_mode(state)
                    state['page_num'] += 1
                    state['pan_x'], state['pan_y'] = 0,0 ; state['selected_idx'] = None
                    state['page_changed'] = True
            elif ui_element == state.get('btn_open_file'):
                state['reselect_file'] = True
            elif ui_element == state.get('btn_select'):
                state['tool_mode'] = 'select'; state['insert_mode'] = None; pygame.mouse.set_visible(True)
            elif ui_element == state.get('btn_save'):
                save_config_func(state['pdf_filename'], state['config'])
                state['running'] = False
            elif button_id == '#confirm_image_selection' and state.get('image_select_dialog'):
                selected_path = state['image_select_dialog'].selected_image_path
                if selected_path:
                    state['insert_mode'] = 'image' # Ready to place this image
                    state['insert_image_path'] = selected_path
                    state['image_select_dialog'].kill()
                    state['image_select_dialog'] = None
                    pygame.mouse.set_visible(False) # Hide cursor for placement
                else:
                    # Maybe provide feedback if no image was actually confirmed
                    state['image_select_dialog'].kill()
                    state['image_select_dialog'] = None
                    state['insert_mode'] = None # Cancelled or no selection
                    state['tool_mode'] = 'select'
                    pygame.mouse.set_visible(True)
                return True 
            elif button_id == '#cancel_image_selection' and state.get('image_select_dialog'):
                state['image_select_dialog'].kill()
                state['image_select_dialog'] = None
                state['insert_mode'] = None # Cancelled selection process
                state['tool_mode'] = 'select'
                pygame.mouse.set_visible(True)
                return True
            elif hasattr(event.ui_element, 'object_ids') and event.ui_element.object_ids and '#remove_text_node' in event.ui_element.object_ids[-1]:
                if state['editing_idx'] is not None and state['editing_idx'] < len(state['config']['pages'][state['page_num']]['elements']):
                    del state['config']['pages'][state['page_num']]['elements'][state['editing_idx']]
                    reset_text_edit_mode(state)
                    state['selected_idx'] = None
                    push_history(state)
            elif ui_element == state.get('btn_add_obscure'):
                state['insert_mode'] = 'obscure'
                state['tool_mode'] = None
                pygame.mouse.set_visible(False)
            elif ui_element == state.get('btn_generate_fields'):
                # Run OCR on the current page image and add text nodes
                arr = pygame.surfarray.array3d(state['doc_img_full'])
                arr = np.transpose(arr, (1, 0, 2))  # Pygame is (w,h,3), PIL is (h,w,3)
                ocr_results = ocr_utils.ocr_image(arr)
                for res in ocr_results:
                    new_el = {
                        'type': 'text',
                        'x': res['left'],
                        'y': res['top'],
                        'width': res['width'],
                        'height': res['height'],
                        'font_size': res['font_size'],
                        'value': res['text'],
                        'background_color': [255, 255, 255],
                        'font_color': [0, 0, 0],
                        'text_align_h': 'left',
                        'text_align_v': 'top',
                        'font': 'arial'
                    }
                    state['config']['pages'][state['page_num']]['elements'].append(new_el)
                state['redraw'] = True
                push_history(state)
                return True
            elif button_id == '#convert_to_obscure':
                selected_indices = state.get('selected_indices', [])
                if len(selected_indices) == 1:
                    idx = selected_indices[0]
                    el = state['config']['pages'][state['page_num']]['elements'][idx]
                    if el.get('type') == 'text':
                        # Replace with obscure node, keep position/size
                        new_obscure = {
                            'type': 'obscure',
                            'x': el.get('x', 0),
                            'y': el.get('y', 0),
                            'width': el.get('width', 100),
                            'height': el.get('height', 30),
                            'mode': 'pixelate'
                        }
                        state['config']['pages'][state['page_num']]['elements'][idx] = new_obscure
                        push_history(state)
                        hide_font_menu()
                        state['selected_indices'] = [idx]
                        state['selected_idx'] = idx
                        state['redraw'] = True
                        return True
            elif button_id == '#merge_multi':
                selected_indices = sorted(set(state.get('selected_indices', [])))
                if len(selected_indices) > 1:
                    page_elements = state['config']['pages'][state['page_num']]['elements']
                    min_x = min(page_elements[idx]['x'] for idx in selected_indices)
                    min_y = min(page_elements[idx]['y'] for idx in selected_indices)
                    max_x = max(page_elements[idx]['x'] + page_elements[idx].get('width', 0) for idx in selected_indices)
                    max_y = max(page_elements[idx]['y'] + page_elements[idx].get('height', 0) for idx in selected_indices)
                    # Create a default element for the target type
                    if page_elements[selected_indices[0]]['type'] == 'text':
                        new_el = {
                            'type': 'text',
                            'x': min_x,
                            'y': min_y,
                            'width': max_x - min_x,
                            'height': max_y - min_y,
                            'value': '',
                            'font_size': 16,
                            'background_color': [255, 255, 255],
                            'font_color': [0, 0, 0],
                            'text_align_h': 'left',
                            'text_align_v': 'top',
                            'font': 'arial'
                        }
                    elif page_elements[selected_indices[0]]['type'] == 'obscure':
                        new_el = {
                            'type': 'obscure',
                            'x': min_x,
                            'y': min_y,
                            'width': max_x - min_x,
                            'height': max_y - min_y,
                            'mode': 'pixelate',
                            'value': ''
                        }
                    elif page_elements[selected_indices[0]]['type'] == 'image':
                        new_el = {
                            'type': 'image',
                            'x': min_x,
                            'y': min_y,
                            'width': max_x - min_x,
                            'height': max_y - min_y,
                            'value': '',
                            'padding': {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}
                        }
                    elif page_elements[selected_indices[0]]['type'] == 'rectangle':
                        new_el = {
                            'type': 'rectangle',
                            'x': min_x,
                            'y': min_y,
                            'width': max_x - min_x,
                            'height': max_y - min_y,
                            'background_color': [200, 200, 200]
                        }
                    else:
                        new_el = {
                            'type': page_elements[selected_indices[0]]['type'],
                            'x': min_x,
                            'y': min_y,
                            'width': max_x - min_x,
                            'height': max_y - min_y
                        }
                    for idx in sorted(selected_indices, reverse=True):
                        del page_elements[idx]
                    page_elements.insert(selected_indices[0], new_el)
                    state['selected_indices'] = [selected_indices[0]]
                    state['selected_idx'] = selected_indices[0]
                    if new_el['type'] == 'image':
                        state['show_image_select_for_element_idx'] = selected_indices[0]
                    push_history(state)
                return True
            return True

        elif event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED or event.user_type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if handle_font_menu_event(event, state['editing_idx'], state['config'], state['page_num']):
                return True
            if handle_image_properties_event(event, state['selected_idx'], state['config'], state['page_num']):
                return True
            if handle_obscure_properties_event(event, state['selected_idx'], state['config'], state['page_num']):
                state['redraw'] = True
                return True
        
        elif state.get('file_dialog') and event.user_type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
            if event.ui_element == state['file_dialog']:
                state['insert_mode'] = 'image'
                state['insert_image_path'] = event.text
                state['file_dialog'].kill()
                state['file_dialog'] = None
                pygame.mouse.set_visible(False)
                return True

        elif event.user_type == pygame_gui.UI_WINDOW_CLOSE:
            if state.get('file_dialog') and event.ui_element == state['file_dialog']:
                state['file_dialog'].kill()
                state['file_dialog'] = None
                state['insert_mode'] = None
                state['tool_mode'] = 'select'
                pygame.mouse.set_visible(True)
                return True
            # Handle closing of ImageFileSelectWindow via its close button
            elif state.get('image_select_dialog') and event.ui_element == state['image_select_dialog']:
                state['image_select_dialog'].kill()
                state['image_select_dialog'] = None
                state['insert_mode'] = None # Cancelled selection process
                state['tool_mode'] = 'select'
                pygame.mouse.set_visible(True)
                return True

    # Handle font menu interactions
    if state.get('editing_idx') is not None: # Check if a text element is selected for property editing
        prop_changed = ui_text_properties.handle_font_menu_event(event, state['editing_idx'], state['config'], state['page_num'])
        if prop_changed:
            push_history(state)
            # If a property changed (e.g., data key, font size, font family, color)
            # we need to check if the 'value' of the text element was changed by the template_key_dropdown
            # and if that element is currently in text_edit_mode.
            # If so, state['editing_text'] must be updated to reflect the new 'value' from the config.
            
            # Check if the change was from the template key dropdown and if we are in text_edit_mode for the affected element.
            # ui_text_properties.template_key_dropdown is the actual dropdown UI element instance.
            if state['text_edit_mode'] and event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED and event.ui_element == ui_text_properties.template_key_dropdown:
                current_element_config = state['config']['pages'][state['page_num']]['elements'][state['editing_idx']]
                new_value_from_config = current_element_config.get('value', '')
                if state['editing_text'] != new_value_from_config:
                    state['editing_text'] = new_value_from_config
                    state['text_cursor_pos'] = len(state['editing_text']) # Reset cursor position
            
            # Regardless of whether editing_text was updated, the property change was handled.
            return True # Event handled by font menu, config was updated by handle_font_menu_event.

    # --- Merge logic triggered from MergeToolbarPanel ---
    merge_type = state.pop('merge_toolbar_merge_requested_type', None)
    if merge_type:
        selected_indices = sorted(set(state.get('selected_indices', [])))
        if len(selected_indices) > 1:
            page_elements = state['config']['pages'][state['page_num']]['elements']
            min_x = min(page_elements[idx]['x'] for idx in selected_indices)
            min_y = min(page_elements[idx]['y'] for idx in selected_indices)
            max_x = max(page_elements[idx]['x'] + page_elements[idx].get('width', 0) for idx in selected_indices)
            max_y = max(page_elements[idx]['y'] + page_elements[idx].get('height', 0) for idx in selected_indices)
            # Create a default element for the target type
            if merge_type == 'text':
                new_el = {
                    'type': 'text',
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y,
                    'value': '',
                    'font_size': 16,
                    'background_color': [255, 255, 255],
                    'font_color': [0, 0, 0],
                    'text_align_h': 'left',
                    'text_align_v': 'top',
                    'font': 'arial'
                }
            elif merge_type == 'obscure':
                new_el = {
                    'type': 'obscure',
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y,
                    'mode': 'pixelate',
                    'value': ''
                }
            elif merge_type == 'image':
                new_el = {
                    'type': 'image',
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y,
                    'value': '',
                    'padding': {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}
                }
            elif merge_type == 'rectangle':
                new_el = {
                    'type': 'rectangle',
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y,
                    'background_color': [200, 200, 200]
                }
            else:
                new_el = {
                    'type': merge_type,
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y
                }
            for idx in sorted(selected_indices, reverse=True):
                del page_elements[idx]
            page_elements.insert(selected_indices[0], new_el)
            state['selected_indices'] = [selected_indices[0]]
            state['selected_idx'] = selected_indices[0]
            if merge_type == 'image':
                state['show_image_select_for_element_idx'] = selected_indices[0]
            push_history(state)
        return True

    return False 

# --- Undo/History Utilities ---
def push_history(state):
    # Only keep up to 50 history states
    max_history = 50
    # If we undid and then made a new change, drop all redo states
    if state['history_index'] < len(state['history']) - 1:
        state['history'] = state['history'][:state['history_index']+1]
    # Push a deepcopy of config
    state['history'].append(copy.deepcopy(state['config']))
    # Trim if too long
    if len(state['history']) > max_history:
        state['history'] = state['history'][-max_history:]
    state['history_index'] = len(state['history']) - 1

def undo_history(state):
    if state['history_index'] > 0:
        state['history_index'] -= 1
        state['config'] = copy.deepcopy(state['history'][state['history_index']])
        state['selected_idx'] = None
        state['editing_idx'] = None
        state['text_edit_mode'] = False
        state['redraw'] = True 