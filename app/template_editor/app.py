import os
import pygame
import pygame_gui
import copy

# Import modules from our refactored structure
from app.template_editor.constants import *
from app.template_editor.pdf_utils import (
    pdf_page_to_image, load_config, save_config, 
    get_pdf_thumbnails
)
from app.template_editor.elements import draw_element, get_element_bounds
from app.template_editor.canvas import (
    clamp_pan, get_canvas_position,
    draw_coordinates, draw_help_text, draw_resize_handles,
    draw_marquee_rectangle
)
from app.template_editor.ui_components import (
    ListFileSelectWindow, create_toolbar_buttons, update_toolbar_highlight,
    create_zoom_controls, update_zoom_controls, create_page_controls,
    update_page_controls, draw_toolbar_backgrounds
)
from app.template_editor.event_handlers import (
    handle_keyboard_event, handle_mousewheel_event, handle_mousebuttondown,
    handle_mousebuttonup, handle_mousemotion, handle_ui_event,
    reset_text_edit_mode
)
from app.template_editor.ui_text_properties import hide_font_menu
import generate_config # Assuming it's at the root, sibling to template_editor.py
from app.template_editor.ui_merge_toolbar import MergeToolbarPanel

ICON_MERGE_PATH = 'app/assets/icon_merge.png'

def initialize_editor():
    """Initialize the template editor application"""
    os.makedirs(TEMP_IMG_DIR, exist_ok=True)
    pygame.init()
    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    window = pygame.display.set_mode((min(1600, screen_width - 100), min(1000, screen_height - 100)), pygame.RESIZABLE)
    pygame.display.set_caption('PDF Template Visual Editor')
    manager = pygame_gui.UIManager((screen_width, screen_height))
    clock = pygame.time.Clock()
    bg_texture = pygame.image.load(BG_TEXTURE_PATH)
    bg_texture_rect = bg_texture.get_rect()
    cursor_text_img = pygame.image.load(CURSOR_TEXT_PATH).convert_alpha()
    cursor_image_img = pygame.image.load(CURSOR_IMAGE_PATH).convert_alpha()
    return window, manager, clock, bg_texture, bg_texture_rect, cursor_text_img, cursor_image_img

def select_pdf_file(window, manager, clock):
    """Show the PDF file selection dialog and return the selected PDF file"""
    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print('No PDFs found in input_pdfs.')
        return None
    
    # Generate thumbnails
    thumb_paths = get_pdf_thumbnails(pdf_files)
    
    # Show file selection dialog
    file_select_win = ListFileSelectWindow(pygame.Rect(200, 40, 650, 600), manager, pdf_files, thumb_paths)
    if pdf_files:
        file_select_win.selection_list.selected_item = pdf_files[0]
        file_select_win.selected = pdf_files[0]
        file_select_win.update_preview(pdf_files[0])
    
    selected_pdf = None
    show_editor = False
    while not show_editor:
        time_delta = clock.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None
            if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == file_select_win.confirm_btn:
                if file_select_win.selected:
                    selected_pdf = file_select_win.selected
                    file_select_win.kill()
                    show_editor = True
            file_select_win.process_event(event)
            manager.process_events(event)
        manager.update(time_delta)
        window.fill((40, 40, 40))
        manager.draw_ui(window)
        pygame.display.update()
        # If the dialog is closed without a selection, re-show it
        if not file_select_win.alive() and not show_editor:
            file_select_win = ListFileSelectWindow(pygame.Rect(200, 40, 650, 420), manager, pdf_files, thumb_paths)
    
    return selected_pdf

def load_document(pdf_filename):
    """Load or create a document configuration"""
    pdf_path = os.path.join(INPUT_DIR, pdf_filename)
    config_path = os.path.join(CONFIG_DIR, f'{os.path.splitext(pdf_filename)[0]}.json')
    
    # Create config if it doesn't exist
    if not os.path.exists(config_path):
        # generate_config is used here, ensure it's accessible
        # If generate_config is in the parent directory, ensure PYTHONPATH or sys.path is correct
        # Or move generate_config into app or app.utils
        generate_config.ensure_config_dir() # Assuming generate_config is correctly imported
        page_details = generate_config.get_pdf_page_details(pdf_path)
        if page_details:
            config_skeleton = generate_config.generate_config_skeleton(pdf_filename, page_details)
            with open(config_path, 'w') as f:
                import json # Keep json import local or move to top if used widely
                json.dump(config_skeleton, f, indent=4)
    
    # Load config
    config = load_config(pdf_filename)
    if not config:
        print('No config found for', pdf_filename)
        return None, None
    
    return pdf_path, config

def render_document_page(pdf_path, page_num):
    """Render a PDF page to an image"""
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    img_path = os.path.join(TEMP_IMG_DIR, f'{base_name}_page{page_num+1}_2x.png')
    pdf_page_to_image(pdf_path, page_num, img_path)
    doc_img_full = pygame.image.load(img_path)
    return doc_img_full

def initialize_editor_state(config, doc_img_full):
    """Initialize the editor state dictionary"""
    state = {
        # Document state
        'config': config,
        'page_num': 0,
        'doc_img_full': doc_img_full,
        'doc_rect_full': doc_img_full.get_rect(),
        'canvas_size': (doc_img_full.get_width(), doc_img_full.get_height()),
        
        # View state
        'zoom_idx': DEFAULT_ZOOM_INDEX,
        'zoom': ZOOM_LEVELS[DEFAULT_ZOOM_INDEX],
        'pan_x': 0,
        'pan_y': 0,
        
        # Tool state
        'tool_mode': 'select',  # 'select', 'text', 'image'
        'insert_mode': None,    # None, 'text', 'image', 'image_select'
        'insert_image_path': None,
        
        # Selection state
        'selected_idx': None,  # Deprecated, use selected_indices
        'selected_indices': [], # New: list of selected indices for multi-select
        'dragging': False,
        'offset': (0, 0),
        'canvas_drag': False,
        'canvas_drag_start': (0, 0),
        'pan_start': (0, 0),
        'resizing': False,
        'resize_mode': None,
        'font_resizing': False,
        'font_resizing_mode': None,
        'font_resize_start_mouse': (0,0),
        'orig_font_size': 18,
        
        # Text editing state
        'text_edit_mode': False,
        'editing_idx': None,
        'editing_text': "",
        'text_cursor_pos': 0,
        'text_cursor_visible': True,
        'text_cursor_blink_time': 0,
        
        # Mouse state
        'mouse_canvas_pos': (0, 0),
        'mouse_screen_pos': (0, 0),
        'last_click_time': 0,
        'last_click_pos': (0, 0),
        'double_click_threshold': DOUBLE_CLICK_THRESHOLD,
        
        # Marquee selection state
        'marquee_selecting': False,
        'marquee_start': None,
        'marquee_end': None,
        
        # Runtime state
        'running': True,
        'file_dialog': None,
        # Undo/redo state
        'history': [],
        'history_index': -1,
    }
    
    return state

def update_editor_ui(state, window, manager):
    """Update the editor UI elements based on window size"""
    window_width, window_height = window.get_size()
    
    # Create or update toolbar buttons
    toolbar_buttons = create_toolbar_buttons(manager, window_height)
    state['btn_select'], state['btn_add_text'], state['btn_add_image'], state['btn_add_rect'], state['btn_add_obscure'], state['btn_undo'] = toolbar_buttons
    
    # Create or update zoom controls
    zoom_controls = create_zoom_controls(manager, window_width, window_height)
    state['btn_minus'], state['btn_actual'], state['btn_plus'], state['btn_reset_pan'], state['zoom_label'] = zoom_controls
    
    # Create or update page navigation controls
    page_controls = create_page_controls(manager, window_width, len(state['config']['pages']), state['page_num'])
    state['btn_prev_page'], state['page_label'], state['btn_next_page'] = page_controls
    
    # Create 'Open File' button at top left
    state['btn_open_file'] = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(20, 20, 120, 40),
        text='Open File',
        manager=manager,
        object_id='#open_file'
    )
    
    # Create 'Generate Fields' button at top left, next to 'Open File'
    state['btn_generate_fields'] = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(150, 20, 160, 40),
        text='Generate Fields',
        manager=manager,
        object_id='#generate_fields'
    )

    # Create 'Save' button at bottom right
    state['btn_save'] = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(window_width - 140, window_height - 60, 120, 40),
        text='Save',
        manager=manager,
        object_id='#save'
    )
    
    # Update merge toolbar panel position and visibility
    if 'merge_toolbar_panel' in state and state['merge_toolbar_panel']:
        page_elements = state['config']['pages'][state['page_num']]['elements']
        selected_indices = state['selected_indices']
        zoom = state['zoom']
        canvas_w, canvas_h = state['canvas_size']
        scaled_w, scaled_h = int(canvas_w * zoom), int(canvas_h * zoom)
        win_w, win_h = window.get_width(), window.get_height()
        canvas_x = (win_w - scaled_w) // 2 + state['pan_x']
        canvas_y = (win_h - scaled_h) // 2 + state['pan_y']
        state['merge_toolbar_panel'].update_for_selection(selected_indices, page_elements, zoom, canvas_x, canvas_y)
    
    return state

def main():
    """Main entry point for the template editor"""
    # Initialize the editor
    window, manager, clock, bg_texture, bg_texture_rect, cursor_text_img, cursor_image_img = initialize_editor()
    
    # Select a PDF file
    pdf_filename = select_pdf_file(window, manager, clock)
    if not pdf_filename:
        print("[app.py] No PDF selected or quit during selection. Exiting.")
        return
    print(f"[app.py] PDF filename: {pdf_filename}")
    
    # Load the document
    pdf_path, config = load_document(pdf_filename)
    if not config:
        print(f"[app.py] Config not loaded for {pdf_filename}. Exiting.")
        return
    print(f"[app.py] Document loaded: {pdf_path}")
    
    # Render the first page
    doc_img_full = render_document_page(pdf_path, 0)
    print("[app.py] First page rendered.")
    
    # Initialize editor state
    state = initialize_editor_state(config, doc_img_full)
    state['pdf_filename'] = pdf_filename
    state['pdf_path'] = pdf_path
    print("[app.py] Editor state initialized.")
    # Push initial config to history for undo (only if history is empty)
    if not state['history']:
        state['history'].append(copy.deepcopy(state['config']))
        state['history_index'] = 0
    # Set up UI elements
    state = update_editor_ui(state, window, manager)
    print("[app.py] Editor UI updated.")
    # Add initial toolbar highlight
    update_toolbar_highlight(
        [state['btn_select'], state['btn_add_text'], state['btn_add_image'], state['btn_add_rect'], state['btn_add_obscure']],
        state['tool_mode'],
        state['insert_mode']
    )
    
    # Create merge toolbar panel once
    if 'merge_toolbar_panel' not in state or not state['merge_toolbar_panel']:
        state['merge_toolbar_panel'] = MergeToolbarPanel(manager, on_merge_callback=lambda merge_type: state.__setitem__('merge_toolbar_merge_requested_type', merge_type))
    
    # Main event loop
    while state['running']:
        time_delta = clock.tick(60)/1000.0
        # Debug: print selected_indices every frame
        print(f"[DEBUG] main loop selected_indices: {state.get('selected_indices')}")
        
        # Handle events
        for event in pygame.event.get():
            # It's crucial for pygame_gui to process events first.
            manager.process_events(event)

            if event.type == pygame.QUIT:
                state['running'] = False
                break # Exit event loop immediately
            
            # Custom event handlers. If an event is fully handled, continue to next event.
            if handle_keyboard_event(event, state, manager):
                # UI updates (like toolbar highlight) will be handled after the event loop finishes for this frame
                continue 
            if handle_mousewheel_event(event, state):
                # UI updates for zoom will be handled after event loop
                continue
            if handle_mousebuttondown(event, state, window, manager):
                continue
            if handle_mousebuttonup(event, state):
                continue
            if handle_mousemotion(event, state, window, manager):
                continue
            
            if event.type == pygame.VIDEORESIZE:
                window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                manager.set_window_resolution((event.w, event.h))
                manager.clear_and_reset()
                state = update_editor_ui(state, window, manager)
                # Toolbar, zoom, page controls are updated by update_editor_ui
                continue
            
            # pygame_gui user events (buttons, dropdowns, etc.)
            if handle_ui_event(event, state, save_config, manager): 
                if not state['running']:
                    break # Exit event loop if UI event led to exit
                continue # UI event was handled
            
            # Note: manager.process_events(event) was moved to the top of the loop.

        if not state['running']:
            break # Exit main loop if state['running'] became false

        # Handle state changes flagged by event handlers (outside the event iteration loop)
        if state.get('reselect_file'):
            print("[app.py] Reselecting file...")
            # Save current work maybe? For now, just reselect.
            if state.get('text_edit_mode'): reset_text_edit_mode(state)
            hide_font_menu() # Ensure font menu is hidden

            pdf_filename_new = select_pdf_file(window, manager, clock)
            if not pdf_filename_new: # User might have quit the selection dialog
                state['running'] = False
                continue
            
            pdf_path_new, config_new = load_document(pdf_filename_new)
            if not config_new:
                state['running'] = False # Failed to load new document
                print(f"Failed to load document: {pdf_filename_new}")
                continue
            
            doc_img_full_new = render_document_page(pdf_path_new, 0)
            
            # Update state with new document info
            state.update(initialize_editor_state(config_new, doc_img_full_new))
            state['pdf_filename'] = pdf_filename_new
            state['pdf_path'] = pdf_path_new
            state['reselect_file'] = False
            state['page_num'] = 0 # Reset to first page
            state['pan_x'], state['pan_y'] = 0, 0
            state['selected_idx'] = None
            state['tool_mode'] = 'select' # Default tool
            state['insert_mode'] = None

            # Re-initialize UI for the new document context
            state = update_editor_ui(state, window, manager)
            # Fall through to UI update section below to refresh highlights etc.

        if state.get('page_changed'):
            state['doc_img_full'] = render_document_page(state['pdf_path'], state['page_num'])
            state['doc_rect_full'] = state['doc_img_full'].get_rect()
            state['canvas_size'] = (state['doc_img_full'].get_width(), state['doc_img_full'].get_height())
            state['page_changed'] = False

        # --- Force redraw if requested (e.g., obscure mode changed) ---
        if state.get('redraw'):
            state['redraw'] = False
            # No-op: the next drawing section will use the updated config

        # --- UI Updates based on state (call these every frame after events) --- 
        update_toolbar_highlight(
            [state['btn_select'], state['btn_add_text'], state['btn_add_image'], state['btn_add_rect'], state['btn_add_obscure']],
            state['tool_mode'], state['insert_mode'])
        update_zoom_controls(
            [state['btn_minus'], state['btn_actual'], state['btn_plus'], state['btn_reset_pan'], state['zoom_label']],
            state['zoom'], window.get_width(), window.get_height())
        update_page_controls(
            [state['btn_prev_page'], state['page_label'], state['btn_next_page']],
            window.get_width(), state['page_num'], len(state['config']['pages']))
        # Ensure save button position is updated on resize
        current_win_width = window.get_width()
        current_win_height = window.get_height()
        state['btn_save'].set_relative_position((current_win_width - 140, current_win_height - 60))

        # Update UI manager after all event processing and state changes for this frame
        manager.update(time_delta)
        
        # Get window and canvas dimensions for drawing
        window_width, window_height = window.get_size()
        canvas_w, canvas_h = state['canvas_size']
        scaled_w, scaled_h = int(canvas_w * state['zoom']), int(canvas_h * state['zoom'])
        state['pan_x'], state['pan_y'] = clamp_pan(state['pan_x'], state['pan_y'], window_width, window_height, scaled_w, scaled_h)
        canvas_x, canvas_y = get_canvas_position(window_width, window_height, scaled_w, scaled_h, state['pan_x'], state['pan_y'])

        # --- Drawing Start ---

        # Draw repeating background texture
        for x_bg in range(0, window_width, bg_texture_rect.width):
            for y_bg in range(0, window_height, bg_texture_rect.height):
                window.blit(bg_texture, (x_bg, y_bg))
        
        # Create the scaled_canvas surface: this is where the document (PDF, elements, rulers) will be drawn
        scaled_canvas = pygame.Surface((scaled_w, scaled_h), pygame.SRCALPHA)
        scaled_canvas.fill((0, 0, 0, 0)) 

        # 1. Draw the scaled PDF image onto scaled_canvas
        if state['doc_img_full']:
            if scaled_w > 0 and scaled_h > 0: 
                try:
                    scaled_doc_img = pygame.transform.scale(state['doc_img_full'], (scaled_w, scaled_h))
                    scaled_canvas.blit(scaled_doc_img, (0, 0)) 
                except pygame.error as e:
                    print(f"Error scaling document image: {e}. Scaled_w={scaled_w}, Scaled_h={scaled_h}") 
        else:
            pass

        # 2. Draw rulers onto scaled_canvas

        # 3. Draw elements (text boxes, images) onto scaled_canvas
        current_page_config = state['config']['pages'][state['page_num']]
        if 'elements' in current_page_config:
            all_elements_with_indices = list(enumerate(current_page_config.get('elements', [])))
            element_types_draw_order = ['rectangle', 'image', 'text']
            # Calculate visible area in canvas coordinates
            win_w, win_h = window.get_width(), window.get_height()
            canvas_x, canvas_y = get_canvas_position(win_w, win_h, scaled_w, scaled_h, state['pan_x'], state['pan_y'])
            viewport_rect = pygame.Rect(-canvas_x / state['zoom'], -canvas_y / state['zoom'], win_w / state['zoom'], win_h / state['zoom'])
            for el_type_to_draw in element_types_draw_order:
                for original_idx, el_config in all_elements_with_indices:
                    if el_config.get('type') == el_type_to_draw:
                        # Get element bounds in canvas coordinates
                        x, y = el_config.get('x', 0), el_config.get('y', 0)
                        w, h = el_config.get('width', 0), el_config.get('height', 0)
                        el_rect = pygame.Rect(x, y, w, h)
                        if not viewport_rect.colliderect(el_rect):
                            continue  # Skip drawing if not visible
                        is_selected = (original_idx in state.get('selected_indices', []))
                        is_editing_this_element = (state['editing_idx'] == original_idx and state['text_edit_mode'])
                        current_text_for_draw = state['editing_text'] if is_editing_this_element else el_config.get('value', '')
                        text_cursor_pos_for_draw = state['text_cursor_pos'] if is_editing_this_element else 0
                        text_cursor_visible_for_draw = state['text_cursor_visible'] if is_editing_this_element else False
                        draw_element(scaled_canvas, el_config, selected=is_selected, editing=is_editing_this_element,
                                     current_text=current_text_for_draw, show_cursor=text_cursor_visible_for_draw,
                                     cursor_pos=text_cursor_pos_for_draw, scale=state['zoom'])
            for original_idx, el_config in all_elements_with_indices:
                if el_config.get('type') not in element_types_draw_order:
                    x, y = el_config.get('x', 0), el_config.get('y', 0)
                    w, h = el_config.get('width', 0), el_config.get('height', 0)
                    el_rect = pygame.Rect(x, y, w, h)
                    if not viewport_rect.colliderect(el_rect):
                        continue
                    is_selected = (original_idx in state.get('selected_indices', []))
                    is_editing_this_element = (state['editing_idx'] == original_idx and state['text_edit_mode'])
                    current_text_for_draw = state['editing_text'] if is_editing_this_element else el_config.get('value', '')
                    text_cursor_pos_for_draw = state['text_cursor_pos'] if is_editing_this_element else 0
                    text_cursor_visible_for_draw = state['text_cursor_visible'] if is_editing_this_element else False
                    draw_element(scaled_canvas, el_config, selected=is_selected, editing=is_editing_this_element,
                                 current_text=current_text_for_draw, show_cursor=text_cursor_visible_for_draw,
                                 cursor_pos=text_cursor_pos_for_draw, scale=state['zoom'])
        
        # 4. Blit the fully drawn scaled_canvas (with PDF, rulers, elements) onto the main window
        window.blit(scaled_canvas, (canvas_x, canvas_y))

        # Draw marquee selection rectangle (if active)
        draw_marquee_rectangle(window, state, canvas_x, canvas_y, state['zoom'])

        # 5. Draw resize handles directly on the main window (if an element is selected)
        if state['tool_mode'] == 'select' and state.get('selected_indices'):
            for idx in state['selected_indices']:
                if idx < len(current_page_config.get('elements', [])):
                    selected_element_config = current_page_config['elements'][idx]
                    element_rect_unscaled = get_element_bounds(selected_element_config, state['zoom'])
                    draw_resize_handles(window, element_rect_unscaled, idx, state['config'], state['page_num'],
                                        canvas_x, canvas_y, state['zoom'])

        # 6. Draw toolbar backgrounds (should be on top of canvas content, but below UI manager elements)
        draw_toolbar_backgrounds(window, window_width, window_height)
        
        # 7. Draw coordinates and help text (on top of everything except UI Manager elements)
        draw_coordinates(window, state['mouse_screen_pos'][0], state['mouse_screen_pos'][1],
                         int(state['mouse_canvas_pos'][0]), int(state['mouse_canvas_pos'][1]))
        help_text_lines = [
            f"Tool: {state['tool_mode']}" + (f" ({state['insert_mode']})" if state['insert_mode'] else ""),
            f"Page: {state['page_num'] + 1}/{len(state['config']['pages'])} Zoom: {int(state['zoom']*100)}%",
            f"Mouse (Canvas): {int(state['mouse_canvas_pos'][0])}, {int(state['mouse_canvas_pos'][1])}",
            "Pan: Click-Drag (Select Tool) / Middle-Mouse Drag. Scroll: Zoom.",
            "Ctrl+S: Save Config. Del: Delete Selected Element.",
        ]
        if state['tool_mode'] == 'text' and state['editing_idx'] is not None:
            help_text_lines.append("Text Edit Mode: Esc to exit. Enter for new line (if supported).")
        draw_help_text(window, help_text_lines)

        # 8. Pygame GUI Manager draws its UI elements (buttons, dialogs etc.) last, so they are on top
        
        manager.draw_ui(window)
        
        # 9. Update the full display Surface to the screen
        pygame.display.update()

        # Handle state changes flagged by event handlers (outside the event iteration loop)
        if state.get('ui_needs_update'):
            update_editor_ui(state, window, manager)
            state['ui_needs_update'] = False

    # Save config on exit (if not already saved by button)
    print("[app.py] Exiting main loop. Attempting to save config...")
    if os.path.exists(os.path.join(CONFIG_DIR, f'{os.path.splitext(pdf_filename)[0]}.json')):
         save_config(pdf_filename, config) # pdf_filename and config might be from the last loaded file
    pygame.quit()

if __name__ == '__main__':
    main() 