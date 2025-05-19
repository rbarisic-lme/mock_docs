import pygame
from app.template_editor.constants import SCALE, HANDLE_SIZE, RULER_COLOR, RULER_TEXT_COLOR
from app.template_editor.elements import get_resize_handles
from .constants import RULER_THICKNESS, RULER_TEXT_COLOR, HELP_TEXT, ICON_RESIZE_PATH

# Global variable for the resize icon, loaded on demand
_resize_icon_img_surface = None

def _get_resize_icon():
    """Loads (if not already loaded) and returns the resize icon surface."""
    global _resize_icon_img_surface
    if _resize_icon_img_surface is None:
        try:
            # Attempt to load and convert_alpha now that display should be initialized
            loaded_img = pygame.image.load(ICON_RESIZE_PATH)
            _resize_icon_img_surface = loaded_img.convert_alpha()
            print(f"INFO: Resize icon '{ICON_RESIZE_PATH}' loaded successfully.") # INFO Print
        except pygame.error as e:
            print(f"ERROR: Loading resize icon '{ICON_RESIZE_PATH}': {e}")
            _resize_icon_img_surface = False # Use False to indicate loading failed, to prevent retries
    return _resize_icon_img_surface if _resize_icon_img_surface is not False else None

def clamp_pan(pan_x, pan_y, window_width, window_height, scaled_w, scaled_h, leeway=500):
    """
    Constrain panning to keep the document in view
    
    Parameters:
    -----------
    pan_x, pan_y : float
        Current pan offset
    window_width, window_height : int
        Size of the window
    scaled_w, scaled_h : int
        Size of the canvas at current zoom level
    leeway : int
        How much the user can pan past the edge
    """
    # Centered position
    min_x = min(0, (window_width - scaled_w) // 2)
    max_x = max(0, (window_width - scaled_w) // 2)
    min_y = min(0, (window_height - scaled_h) // 2)
    max_y = max(0, (window_height - scaled_h) // 2)
    
    # Allow a little leeway
    min_x -= leeway
    max_x += leeway
    min_y -= leeway
    max_y += leeway
    
    pan_x = max(min_x, min(pan_x, max_x))
    pan_y = max(min_y, min(pan_y, max_y))
    
    return pan_x, pan_y

def get_canvas_coords(mx, my, canvas_x, canvas_y, zoom):
    """
    Convert screen coordinates to canvas coordinates
    
    Parameters:
    -----------
    mx, my : int
        Mouse position in screen coordinates
    canvas_x, canvas_y : int
        Position of canvas in screen coordinates
    zoom : float
        Current zoom level
    """
    cx = int((mx - canvas_x) / zoom)
    cy = int((my - canvas_y) / zoom)
    return cx, cy

def get_canvas_position(window_width, window_height, scaled_w, scaled_h, pan_x, pan_y):
    """Calculate the position of the canvas in the window"""
    canvas_x = (window_width - scaled_w) // 2 + pan_x
    canvas_y = (window_height - scaled_h) // 2 + pan_y
    return canvas_x, canvas_y

def draw_document_rulers(surface, zoom, width, height, color, text_color):
    """
    Draws horizontal and vertical rulers with tick marks onto the given surface.
    These rulers are meant to be part of the document canvas, so they scale with zoom.
    Assumes the surface passed is the scaled_canvas.
    Coordinates are relative to the surface itself.
    """
    if not surface:
        return

    font_size = max(8, int(10 / zoom)) # Adjust font size based on zoom, with a minimum
    try:
        font = pygame.font.SysFont('arial', font_size)
    except Exception:
        font = pygame.font.Font(None, font_size) # Fallback font

    # Define ruler properties - these are in "original document pixels" before scaling by zoom
    # For example, major tick every 100 document pixels, minor every 10.
    major_tick_interval_unscaled = 100  # In original document units
    minor_tick_interval_unscaled = 20   # In original document units
    sub_minor_tick_interval_unscaled = 5 # In original document units

    # Convert to scaled units (pixels on the scaled_canvas)
    major_tick_interval = major_tick_interval_unscaled * zoom
    minor_tick_interval = minor_tick_interval_unscaled * zoom
    sub_minor_tick_interval = sub_minor_tick_interval_unscaled * zoom

    ruler_thickness = 1 # pixels on screen
    major_tick_len = 10 # pixels on screen
    minor_tick_len = 5  # pixels on screen
    sub_minor_tick_len = 2 # pixels on screen

    # --- Horizontal Ruler ---
    # Draw main horizontal line (usually at top, can be adjusted)
    # pygame.draw.line(surface, color, (0, 0), (width, 0), ruler_thickness) 
    
    # Draw horizontal ticks
    pos_x_unscaled = 0
    while pos_x_unscaled * zoom < width:
        x = pos_x_unscaled * zoom
        if pos_x_unscaled % major_tick_interval_unscaled == 0:
            pygame.draw.line(surface, color, (x, 0), (x, major_tick_len), ruler_thickness)
            if zoom > 0.2: # Only draw text if not too zoomed out
                label = font.render(str(pos_x_unscaled), True, text_color)
                surface.blit(label, (x + 2, 2))
        elif pos_x_unscaled % minor_tick_interval_unscaled == 0:
            pygame.draw.line(surface, color, (x, 0), (x, minor_tick_len), ruler_thickness)
        elif pos_x_unscaled % sub_minor_tick_interval_unscaled == 0 and zoom > 0.5: # only draw sub-minor if sufficiently zoomed
             pygame.draw.line(surface, color, (x, 0), (x, sub_minor_tick_len), ruler_thickness)
        pos_x_unscaled += sub_minor_tick_interval_unscaled # Smallest increment

    # --- Vertical Ruler ---
    # Draw main vertical line (usually at left, can be adjusted)
    # pygame.draw.line(surface, color, (0, 0), (0, height), ruler_thickness)

    # Draw vertical ticks
    pos_y_unscaled = 0
    while pos_y_unscaled * zoom < height:
        y = pos_y_unscaled * zoom
        if pos_y_unscaled % major_tick_interval_unscaled == 0:
            pygame.draw.line(surface, color, (0, y), (major_tick_len, y), ruler_thickness)
            if zoom > 0.2:
                label = font.render(str(pos_y_unscaled), True, text_color)
                surface.blit(label, (2, y + 2))
        elif pos_y_unscaled % minor_tick_interval_unscaled == 0:
            pygame.draw.line(surface, color, (0, y), (minor_tick_len, y), ruler_thickness)
        elif pos_y_unscaled % sub_minor_tick_interval_unscaled == 0 and zoom > 0.5:
            pygame.draw.line(surface, color, (0, y), (sub_minor_tick_len, y), ruler_thickness)
        pos_y_unscaled += sub_minor_tick_interval_unscaled # Smallest increment

def draw_rulers(window, mx, my, window_width, window_height):
    """Draw ruler guides and coordinate display at mouse position"""
    # Only draw if mouse is inside the window
    if 0 <= mx < window_width and 0 <= my < window_height:
        # Fine ruler lines
        pygame.draw.line(window, RULER_COLOR, (mx, 0), (mx, window_height), 1)
        pygame.draw.line(window, RULER_COLOR, (0, my), (window_width, my), 1)

def draw_coordinates(window, mx, my, cx, cy):
    """Draw coordinate display at mouse position"""
    font = pygame.font.SysFont('arial', 16)
    coord_text = f"x: {cx}, y: {cy}"
    text_surf = font.render(coord_text, True, RULER_TEXT_COLOR)
    text_rect = text_surf.get_rect()
    text_rect.topleft = (mx + 10, my + 10)
    # Draw white background behind label
    bg_rect = text_rect.inflate(8, 4)
    pygame.draw.rect(window, (255, 255, 255), bg_rect)
    window.blit(text_surf, text_rect)

def draw_help_text(window, help_text):
    """Draw help text at the bottom of the window"""
    font = pygame.font.SysFont('arial', 16)
    for i, line in enumerate(help_text):
        text_surf = font.render(line, True, (180, 180, 180))
        window.blit(text_surf, (10, window.get_height() - 20 * (len(help_text) - i)))

def draw_resize_handles(window, _element_rect_scaled_is_unused, selected_idx, config, page_num, canvas_x, canvas_y, zoom):
    if selected_idx is None or selected_idx >= len(config['pages'][page_num]['elements']):
        return
    element_config = config['pages'][page_num]['elements'][selected_idx]

    handle_positions_base = get_resize_handles(element_config, 1.0)
    current_resize_icon = _get_resize_icon() # Load on demand

    for hidx, (hx_base, hy_base) in enumerate(handle_positions_base):
        handle_screen_x = canvas_x + (hx_base * zoom)
        handle_screen_y = canvas_y + (hy_base * zoom)
        handle_draw_rect = pygame.Rect(
            handle_screen_x - (HANDLE_SIZE // 2),
            handle_screen_y - (HANDLE_SIZE // 2),
            HANDLE_SIZE, HANDLE_SIZE
        )

        if hidx == 4 and element_config.get('type') == 'text':
            # print(f"DEBUG: Drawing handle {hidx} for text element. Icon loaded: {current_resize_icon is not None}") # Retain for now
            if current_resize_icon:
                scaled_icon = pygame.transform.scale(current_resize_icon, (HANDLE_SIZE, HANDLE_SIZE))
                window.blit(scaled_icon, handle_draw_rect.topleft)
            else:
                pygame.draw.rect(window, (255, 0, 0), handle_draw_rect) # RED fallback
                pygame.draw.rect(window, (0, 0, 0), handle_draw_rect, 1)
        else:
            pygame.draw.rect(window, (255, 255, 255), handle_draw_rect)
            pygame.draw.rect(window, (0, 0, 0), handle_draw_rect, 1) 

def draw_marquee_rectangle(window, state, canvas_x, canvas_y, zoom):
    if not state.get('marquee_selecting') or not state.get('marquee_start') or not state.get('marquee_end'):
        return
    x0, y0 = state['marquee_start']
    x1, y1 = state['marquee_end']
    x_min, x_max = min(x0, x1), max(x0, x1)
    y_min, y_max = min(y0, y1), max(y0, y1)
    # Convert canvas coords to screen coords
    screen_x = canvas_x + x_min * zoom
    screen_y = canvas_y + y_min * zoom
    width = (x_max - x_min) * zoom
    height = (y_max - y_min) * zoom
    rect = pygame.Rect(screen_x, screen_y, width, height)
    # Draw semi-transparent fill and border
    color_fill = (100, 180, 255, 60)
    color_border = (30, 120, 200, 180)
    s = pygame.Surface((max(1, int(width)), max(1, int(height))), pygame.SRCALPHA)
    s.fill(color_fill)
    window.blit(s, (screen_x, screen_y))
    pygame.draw.rect(window, color_border, rect, 2) 