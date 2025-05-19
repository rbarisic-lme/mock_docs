import pygame
import os
from app.template_editor.constants import SCALE, HIGHLIGHT_COLOR, INPUT_IMG_DIR

def draw_element(surface, element, selected=False, editing=False, current_text=None, show_cursor=False, cursor_pos=0, scale=1.0):
    """
    Draws a template element.
    For text: el['x'], el['y'] are top-left of bounding box. el['width'], el['height'] are box dims.
    For rectangle: el['x'], el['y'] are top-left. el['width'], el['height'] are dims.
    'scale' is state['zoom']. All base units are multiplied by 'scale' for drawing.
    """
    if scale <= 0: return None, 0, 0

    el_type = element.get('type')

    # --- Element's bounding box (scaled) ---
    scaled_box_x = int(element.get('x', 0) * scale)
    scaled_box_y = int(element.get('y', 0) * scale)
    scaled_box_width = int(element.get('width', 100) * scale)
    scaled_box_height = int(element.get('height', 30) * scale)
    background_color = tuple(element.get('background_color', (220,220,220))) # Default light gray for any element

    # --- Draw Selection Highlight (around the bounding box) ---
    if selected:
        selection_color = (0, 120, 255)
        pygame.draw.rect(surface, selection_color, (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height), 2)

    # --- Draw Element Type Specifics ---
    if el_type == 'text':
        font_color = tuple(element.get('font_color', (0,0,0)))
        text_to_draw = current_text if current_text is not None else element.get('value', '')
        base_font_size = element.get('font_size', 18)
        font_name = element.get('font', 'arial')
        scaled_font_size = max(1, int(base_font_size * scale))

        try:
            font = pygame.font.SysFont(font_name, scaled_font_size)
        except pygame.error:
            font = pygame.font.Font(None, scaled_font_size) # Fallback
        text_surf = font.render(text_to_draw, True, font_color)
        scaled_text_content_width = text_surf.get_width()
        scaled_text_content_height = text_surf.get_height()

        # Draw Background Box for Text Element
        if scaled_box_width > 0 and scaled_box_height > 0:
            bg_color_to_draw = HIGHLIGHT_COLOR if editing else background_color
            pygame.draw.rect(surface, bg_color_to_draw, (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height))
            pygame.draw.rect(surface, (0,0,0), (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height), 1) # Border

        # Text Alignment (Phase 3 - for now, basic top-left within box)
        text_render_pos_x_in_box = 0 
        text_render_pos_y_in_box = 0
        blit_text_at_x = scaled_box_x + text_render_pos_x_in_box
        blit_text_at_y = scaled_box_y + text_render_pos_y_in_box

        if scaled_box_width > 0 and scaled_box_height > 0 and scaled_font_size > 0:
            clip_area_for_text = pygame.Rect(0,0, scaled_box_width, scaled_box_height)
            source_rect_for_blit = pygame.Rect(
                0, 0,
                min(scaled_text_content_width, clip_area_for_text.width - text_render_pos_x_in_box),
                min(scaled_text_content_height, clip_area_for_text.height - text_render_pos_y_in_box)
            )
            if source_rect_for_blit.width > 0 and source_rect_for_blit.height > 0:
                surface.blit(text_surf, (blit_text_at_x, blit_text_at_y), area=source_rect_for_blit)

            if editing and show_cursor and cursor_pos >= 0:
                clamped_cursor_pos = max(0, min(cursor_pos, len(text_to_draw)))
                cursor_offset_text = text_to_draw[:clamped_cursor_pos]
                cursor_offset_surf = font.render(cursor_offset_text, True, font_color) 
                cursor_draw_x_relative_to_blit = cursor_offset_surf.get_width()
                final_cursor_draw_x = blit_text_at_x + cursor_draw_x_relative_to_blit
                final_cursor_draw_x = max(blit_text_at_x, min(final_cursor_draw_x, blit_text_at_x + source_rect_for_blit.width -1 ))
                cursor_y1 = blit_text_at_y
                cursor_y2 = blit_text_at_y + source_rect_for_blit.height
                if cursor_y2 > cursor_y1 and final_cursor_draw_x >= blit_text_at_x and final_cursor_draw_x <= blit_text_at_x + source_rect_for_blit.width:
                    pygame.draw.line(surface, font_color, (final_cursor_draw_x, cursor_y1), (final_cursor_draw_x, cursor_y2), 1)
    
    elif el_type == 'rectangle':
        if scaled_box_width > 0 and scaled_box_height > 0:
            # Rectangles are simpler: just draw their background_color as their fill
            pygame.draw.rect(surface, background_color, (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height))
            pygame.draw.rect(surface, (0,0,0), (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height), 1) # Border
    
    elif el_type == 'image':
        # Placeholder for image drawing logic if it needs to be different from a simple rect
        # For now, assume images also have x,y,width,height and might use a similar box rendering
        # or specialized image loading/scaling here.
        if scaled_box_width > 0 and scaled_box_height > 0:
            # Draw the bounding box for the image element - REMOVED
            # pygame.draw.rect(surface, background_color, (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height)) # Use element's background_color or a default
            # pygame.draw.rect(surface, (0,0,0), (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height), 1) # Border
            
            img_path = element.get('value')
            if img_path:
                try:
                    # Construct full path if img_path is relative
                    if not os.path.isabs(img_path):
                        full_img_path = os.path.join(INPUT_IMG_DIR, img_path)
                    else:
                        full_img_path = img_path

                    img_surf = pygame.image.load(full_img_path)
                    img_orig_w, img_orig_h = img_surf.get_size()

                    if img_orig_w > 0 and img_orig_h > 0:
                        padding = element.get('padding', {'left': 0, 'top': 0, 'right': 0, 'bottom': 0})
                        scaled_padding_left = int(padding.get('left', 0) * scale)
                        scaled_padding_top = int(padding.get('top', 0) * scale)
                        scaled_padding_right = int(padding.get('right', 0) * scale)
                        scaled_padding_bottom = int(padding.get('bottom', 0) * scale)

                        # Available width/height for image content, after padding
                        content_area_w = scaled_box_width - scaled_padding_left - scaled_padding_right
                        content_area_h = scaled_box_height - scaled_padding_top - scaled_padding_bottom

                        if content_area_w <= 0 or content_area_h <= 0:
                            raise ValueError("Content area for image is zero or negative after padding.")

                        aspect_ratio = img_orig_w / img_orig_h
                        
                        render_w = content_area_w
                        render_h = render_w / aspect_ratio
                        
                        if render_h > content_area_h:
                            render_h = content_area_h
                            render_w = render_h * aspect_ratio
                        
                        render_w = int(render_w)
                        render_h = int(render_h)

                        if render_w > 0 and render_h > 0:
                            # Calculate blit position, accounting for padding and centering within the remaining content area
                            # Blit relative to the start of the content area (after top-left padding)
                            # And then center within that content area
                            content_blit_x = scaled_box_x + scaled_padding_left + (content_area_w - render_w) // 2
                            content_blit_y = scaled_box_y + scaled_padding_top + (content_area_h - render_h) // 2
                            
                            scaled_img_surf = pygame.transform.smoothscale(img_surf, (render_w, render_h))
                            surface.blit(scaled_img_surf, (content_blit_x, content_blit_y))
                        else: 
                            raise ValueError("Calculated render dimensions for image are zero after padding.")
                    else: 
                        raise ValueError("Original image dimensions are zero.")

                except Exception as e:
                    print(f"Error loading/drawing image {img_path} (resolved to {full_img_path if 'full_img_path' in locals() else 'N/A'}): {e}")
                    # Draw an X or error message on the box
                    font = pygame.font.Font(None, max(1,int(20 * scale))) # Scale error font size
                    err_surf = font.render("X", True, (255,0,0))
                    err_blit_x = scaled_box_x + (scaled_box_width - err_surf.get_width()) // 2
                    err_blit_y = scaled_box_y + (scaled_box_height - err_surf.get_height()) // 2
                    surface.blit(err_surf, (err_blit_x, err_blit_y))

    elif el_type == 'obscure':
        # Dies wird benutzt um Infos in Dokumenten zu schwärzen.
        mode = element.get('mode', 'pixelate')
        if scaled_box_width > 0 and scaled_box_height > 0:
            if mode == 'pixelate':
                # Pixelate: downscale and upscale the area
                try:
                    sub_surface = surface.subsurface((scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height)).copy()
                    factor = 0.08  # 8% of original size
                    small = pygame.transform.smoothscale(sub_surface, (max(1,int(scaled_box_width*factor)), max(1,int(scaled_box_height*factor))))
                    pixelated = pygame.transform.scale(small, (scaled_box_width, scaled_box_height))
                    surface.blit(pixelated, (scaled_box_x, scaled_box_y))
                except Exception as e:
                    pygame.draw.rect(surface, (0,0,0), (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height))
            elif mode == 'blur':
                # Simple box blur: average color in a grid
                try:
                    sub_surface = surface.subsurface((scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height)).copy()
                    arr = pygame.surfarray.pixels3d(sub_surface)
                    import numpy as np
                    kernel_size = 7
                    arr_blur = arr.copy()
                    for y in range(arr.shape[1]):
                        for x in range(arr.shape[0]):
                            x0 = max(0, x - kernel_size//2)
                            x1 = min(arr.shape[0], x + kernel_size//2 + 1)
                            y0 = max(0, y - kernel_size//2)
                            y1 = min(arr.shape[1], y + kernel_size//2 + 1)
                            arr_blur[x, y] = np.mean(arr[x0:x1, y0:y1], axis=(0,1))
                    pygame.surfarray.blit_array(sub_surface, arr_blur)
                    surface.blit(sub_surface, (scaled_box_x, scaled_box_y))
                except Exception as e:
                    pygame.draw.rect(surface, (0,0,0), (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height))
            elif mode == 'blacken':
                pygame.draw.rect(surface, (0,0,0), (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height))
            pygame.draw.rect(surface, (0,0,0), (scaled_box_x, scaled_box_y, scaled_box_width, scaled_box_height), 1)

    return None, 0, 0


def get_element_bounds(element, zoom_level_unused): # zoom_level_unused is not used here anymore
    """
    For text elements, returns the x, y, width, height of its DEFINED BOUNDING BOX in BASE units.
    Also returns the text content's actual base_width and base_height.
    element['x'], element['y'] = bounding box top-left in base units.
    element['width'], element['height'] = bounding box dimensions in base units.
    """
    box_x = element.get('x', 0)
    box_y = element.get('y', 0)
    box_width = element.get('width', 100) # Default if not specified
    box_height = element.get('height', 30) # Default if not specified

    base_text_content_width = 0
    base_text_content_height = 0

    if element.get('type') == 'text':
        base_font_size = element.get('font_size', 18)
        font_name = element.get('font', 'arial')
        text_value = element.get('value', '')
        try:
            font = pygame.font.SysFont(font_name, base_font_size)
        except pygame.error:
            font = pygame.font.Font(None, base_font_size)
        text_surf = font.render(text_value, True, (0,0,0)) # Color doesn't matter for size
        base_text_content_width = text_surf.get_width()
        base_text_content_height = text_surf.get_height()
    elif element.get('type') == 'image': # Images also have explicit w/h
        pass # base_text_content_width/height remain 0 for images

    return box_x, box_y, box_width, box_height, base_text_content_width, base_text_content_height


def get_resize_handles(element, current_zoom_unused):
    """
    Resize handles are for the DEFINED BOUNDING BOX. Returns positions in BASE units.
    """
    # Use el['x'], el['y'], el['width'], el['height'] directly
    box_x = element.get('x', 0)
    box_y = element.get('y', 0)
    box_w = element.get('width', 100)
    box_h = element.get('height', 30)

    handle_positions = [
        (box_x + box_w // 2, box_y),           # N
        (box_x + box_w, box_y + box_h // 2),     # E
        (box_x + box_w // 2, box_y + box_h),     # S
        (box_x, box_y + box_h // 2),            # W
        (box_x + box_w, box_y)                 # NE (Font Size)
    ]
    return handle_positions


# def get_padding_handles(element, current_zoom_unused): # REMOVE THIS FUNCTION
#     """
#     Padding handles control the padding values. Returns positions in BASE units,
#     offset from the TEXT CONTENT edges.
#     """
#     base_text_x = element.get('x', 0)
#     base_text_y = element.get('y', 0)
#     base_font_size = element.get('font_size', 18)
#     font_name = element.get('font', 'arial')
#     text_value = element.get('value', '')
#     
#     try:
#         font = pygame.font.SysFont(font_name, base_font_size)
#     except pygame.error:
#         font = pygame.font.Font(None, base_font_size)
#     text_surf = font.render(text_value, True, (0,0,0))
#     base_text_content_width = text_surf.get_width()
#     base_text_content_height = text_surf.get_height()
#
#     # Padding handles are conceptually outside the text content area
#     offset = 5 # Visual offset for handle from the content edge (in base units)
#
#     handle_positions = [
#         (base_text_x - offset, base_text_y + base_text_content_height // 2),                    # Left padding
#         (base_text_x + base_text_content_width // 2, base_text_y - offset),                    # Top padding
#         (base_text_x + base_text_content_width + offset, base_text_y + base_text_content_height // 2), # Right padding
#         (base_text_x + base_text_content_width // 2, base_text_y + base_text_content_height + offset)  # Bottom padding
#     ]
#     return handle_positions 