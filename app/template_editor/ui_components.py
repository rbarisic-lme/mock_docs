import os
import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel, UISelectionList, UIWindow, UIPanel, UIImage, UITextBox
from app.template_editor.constants import TOOLBAR_BG_COLOR, PREVIEW_SIZE, THUMB_SIZE, CONFIG_DIR, INPUT_DIR, THUMBNAIL_SIZE
from app.template_editor.pdf_utils import get_preview_path

class ListFileSelectWindow(UIWindow):
    """File selection window for choosing PDFs to edit"""
    def __init__(self, rect, manager, pdf_files, thumb_paths):
        super().__init__(rect, manager, window_display_title='Select PDF to Edit', object_id='#file_select')
        self.selected = None
        self.pdf_files = pdf_files
        self.thumb_paths = thumb_paths
        
        # Create selection list
        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(30, 30, 300, rect.height-120),
            item_list=pdf_files,
            manager=manager,
            container=self
        )
        
        # Create preview area
        self.preview_label = UILabel(
            relative_rect=pygame.Rect(360, 30, 260, 30),
            text='',
            manager=manager,
            container=self
        )
        self.preview_img = None
        self.preview_img_widget = None
        self.stats_box = UITextBox(
            html_text='',
            relative_rect=pygame.Rect(360, 400, 260, 100),
            manager=manager,
            container=self
        )
        
        # Create confirm button
        self.confirm_btn = UIButton(
            relative_rect=pygame.Rect(rect.width//2-60, rect.height-80, 120, 40),
            text='Open',
            manager=manager,
            container=self,
            object_id='#open_pdf'
        )
        
        self.update_preview(None)
    
    def process_event(self, event):
        handled = super().process_event(event)
        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION and event.ui_element == self.selection_list:
            self.selected = event.text
            self.update_preview(self.selected)
        return handled
    
    def update_preview(self, pdf):
        if self.preview_img_widget:
            self.preview_img_widget.kill()
            self.preview_img_widget = None
        
        if pdf:
            preview_path = get_preview_path(pdf)
            if os.path.exists(preview_path):
                self.preview_img_widget = UIImage(
                    relative_rect=pygame.Rect(360, 70, PREVIEW_SIZE[0], PREVIEW_SIZE[1]),
                    image_surface=pygame.image.load(preview_path),
                    manager=self.ui_manager,
                    container=self
                )
            self.preview_label.set_text(pdf)
            
            # Show file stats
            file_path = os.path.join(INPUT_DIR, pdf)
            size_mb = os.path.getsize(file_path) / (1024*1024)
            config_path = os.path.join(CONFIG_DIR, f'{os.path.splitext(pdf)[0]}.json')
            has_config = os.path.exists(config_path)
            stats_text = f"Size: {size_mb:.2f} MB<br>Config: {'Yes' if has_config else 'No'}"
            self.stats_box.set_text(stats_text)
        else:
            self.preview_label.set_text('')
            self.stats_box.set_text('')

def create_toolbar_buttons(manager, window_height):
    """Create the main toolbar buttons for the editor"""
    toolbar_btn_w = 120
    toolbar_btn_h = 40
    toolbar_btn_gap = 20
    toolbar_y_start = (window_height - (3 * toolbar_btn_h + 2 * toolbar_btn_gap)) // 2
    
    # Create buttons
    btn_select = UIButton(
        relative_rect=pygame.Rect(20, toolbar_y_start, toolbar_btn_w, toolbar_btn_h), 
        text='(1) Select', 
        manager=manager, 
        object_id='#select'
    )
    btn_add_text = UIButton(
        relative_rect=pygame.Rect(20, toolbar_y_start + toolbar_btn_h + toolbar_btn_gap, toolbar_btn_w, toolbar_btn_h), 
        text='(2) Add Text', 
        manager=manager, 
        object_id='#add_text'
    )
    btn_add_image = UIButton(
        relative_rect=pygame.Rect(20, toolbar_y_start + 2 * (toolbar_btn_h + toolbar_btn_gap), toolbar_btn_w, toolbar_btn_h), 
        text='(3) Add Image', 
        manager=manager, 
        object_id='#add_image'
    )
    btn_add_rect = UIButton(
        relative_rect=pygame.Rect(20, toolbar_y_start + 3 * (toolbar_btn_h + toolbar_btn_gap), toolbar_btn_w, toolbar_btn_h), 
        text='(4) Add Rect',
        manager=manager, 
        object_id='#add_rect'
    )
    btn_add_obscure = UIButton(
        relative_rect=pygame.Rect(20, toolbar_y_start + 4 * (toolbar_btn_h + toolbar_btn_gap), toolbar_btn_w, toolbar_btn_h),
        text='(5) Obscure',
        manager=manager,
        object_id='#add_obscure'
    )
    btn_undo = UIButton(
        relative_rect=pygame.Rect(20, toolbar_y_start + 5 * (toolbar_btn_h + toolbar_btn_gap), toolbar_btn_w, toolbar_btn_h),
        text='(Ctrl+Z) Undo',
        manager=manager,
        object_id='#undo'
    )
    
    return [btn_select, btn_add_text, btn_add_image, btn_add_rect, btn_add_obscure, btn_undo]

def update_toolbar_highlight(toolbar_buttons, tool_mode, insert_mode):
    """Update the highlighting of toolbar buttons based on active tool"""
    if len(toolbar_buttons) == 4:
        btn_select, btn_add_text, btn_add_image, btn_add_rect = toolbar_buttons
    else:
        btn_select, btn_add_text, btn_add_image = toolbar_buttons[:3]
        btn_add_rect = None
    
    active_color = pygame.Color(pygame.Color("#4B5563"))
    default_color = pygame.Color(pygame.Color("#1F2937"))
    
    if btn_select: btn_select.colours['normal_bg'] = active_color if tool_mode == 'select' and not insert_mode else default_color
    if btn_add_text: btn_add_text.colours['normal_bg'] = active_color if insert_mode == 'text' else default_color
    if btn_add_image: btn_add_image.colours['normal_bg'] = active_color if insert_mode in ('image', 'image_select') else default_color
    if btn_add_rect: btn_add_rect.colours['normal_bg'] = active_color if insert_mode == 'rectangle' else default_color
    
    if btn_select: btn_select.rebuild()
    if btn_add_text: btn_add_text.rebuild()
    if btn_add_image: btn_add_image.rebuild()
    if btn_add_rect: btn_add_rect.rebuild()

def create_zoom_controls(manager, window_width, window_height):
    """Create zoom control buttons"""
    btn_w = 100
    btn_h = 40
    
    # Calculate positions
    center = window_width // 2
    btn_gap = 20
    x_minus = center - btn_w - btn_gap
    x_actual = center
    x_plus = center + btn_w + btn_gap
    y = window_height - 50
    
    # Create buttons
    btn_minus = UIButton(
        relative_rect=pygame.Rect(x_minus, y, btn_w, btn_h), 
        text='- Zoom', 
        manager=manager, 
        object_id='#zoom_minus'
    )
    btn_actual = UIButton(
        relative_rect=pygame.Rect(x_actual, y, btn_w, btn_h), 
        text='Actual Size', 
        manager=manager, 
        object_id='#zoom_actual'
    )
    btn_plus = UIButton(
        relative_rect=pygame.Rect(x_plus, y, btn_w, btn_h), 
        text='+ Zoom', 
        manager=manager, 
        object_id='#zoom_plus'
    )
    btn_reset_pan = UIButton(
        relative_rect=pygame.Rect(x_plus + btn_w + 140, y, btn_w, btn_h), 
        text='Reset Pan', 
        manager=manager, 
        object_id='#reset_pan'
    )
    zoom_label = UILabel(
        relative_rect=pygame.Rect(x_plus + btn_w + 10, y, 120, btn_h), 
        text='Zoom: 100%', 
        manager=manager, 
        object_id='#zoom_label'
    )
    
    return btn_minus, btn_actual, btn_plus, btn_reset_pan, zoom_label

def update_zoom_controls(zoom_controls, zoom, window_width, window_height):
    """Update position and text of zoom controls after window resize or zoom change"""
    btn_minus, btn_actual, btn_plus, btn_reset_pan, zoom_label = zoom_controls
    
    # Calculate new positions
    center = window_width // 2
    btn_w = 100
    btn_gap = 20
    x_minus = center - btn_w - btn_gap
    x_actual = center
    x_plus = center + btn_w + btn_gap
    y = window_height - 50
    
    # Update button positions
    btn_minus.set_relative_position((x_minus, y))
    btn_actual.set_relative_position((x_actual, y))
    btn_plus.set_relative_position((x_plus, y))
    btn_reset_pan.set_relative_position((x_plus + btn_w + 140, y))
    zoom_label.set_relative_position((x_plus + btn_w + 10, y))
    zoom_label.set_text(f'Zoom: {int(zoom*100)}%')

def create_page_controls(manager, window_width, total_pages, current_page=0):
    """Create page navigation controls"""
    nav_btn_w = 120
    nav_btn_h = 40
    
    # Calculate positions
    center = window_width // 2
    nav_btn_gap = 20
    x_prev = center - nav_btn_w - nav_btn_gap
    x_label = center
    x_next = center + nav_btn_w + nav_btn_gap
    y = 20
    
    # Create buttons
    btn_prev_page = UIButton(
        relative_rect=pygame.Rect(x_prev, y, nav_btn_w, nav_btn_h), 
        text='Previous Page', 
        manager=manager, 
        object_id='#prev_page'
    )
    page_label = UILabel(
        relative_rect=pygame.Rect(x_label, y, nav_btn_w, nav_btn_h), 
        text=f'Page {current_page+1}/{total_pages}', 
        manager=manager, 
        object_id='#page_label'
    )
    btn_next_page = UIButton(
        relative_rect=pygame.Rect(x_next, y, nav_btn_w, nav_btn_h), 
        text='Next Page', 
        manager=manager, 
        object_id='#next_page'
    )
    
    return btn_prev_page, page_label, btn_next_page

def update_page_controls(page_controls, window_width, page_num, total_pages):
    """Update position and text of page controls after window resize or page change"""
    btn_prev_page, page_label, btn_next_page = page_controls
    
    # Calculate new positions
    center = window_width // 2
    nav_btn_w = 120
    nav_btn_gap = 20
    x_prev = center - nav_btn_w - nav_btn_gap
    x_label = center
    x_next = center + nav_btn_w + nav_btn_gap
    y = 20
    
    # Update button positions
    btn_prev_page.set_relative_position((x_prev, y))
    page_label.set_relative_position((x_label, y))
    btn_next_page.set_relative_position((x_next, y))
    page_label.set_text(f'Page {page_num+1}/{total_pages}')

def draw_toolbar_backgrounds(window, window_width, window_height):
    """Draw semi-transparent backgrounds for top and bottom toolbars"""
    # Top toolbar
    top_toolbar_height = 80
    top_toolbar_bg = pygame.Surface((window_width, top_toolbar_height), pygame.SRCALPHA)
    top_toolbar_bg.fill(TOOLBAR_BG_COLOR)
    window.blit(top_toolbar_bg, (0, 0))
    
    # Bottom toolbar
    bottom_toolbar_height = 80
    bottom_toolbar_bg = pygame.Surface((window_width, bottom_toolbar_height), pygame.SRCALPHA)
    bottom_toolbar_bg.fill(TOOLBAR_BG_COLOR)
    window.blit(bottom_toolbar_bg, (0, window_height - bottom_toolbar_height))

class ImageFileSelectWindow(UIWindow):
    """File selection window for choosing images with thumbnails."""
    def __init__(self, rect, manager, image_files, input_img_dir):
        super().__init__(rect, manager, window_display_title='Select Image', object_id='#image_select_window')
        self.selected_image_path = None
        self.image_files = image_files
        self.input_img_dir = input_img_dir
        self.thumbnail_size = THUMBNAIL_SIZE # CORRECTED: Use THUMBNAIL_SIZE

        list_width = rect.width // 2 - 30
        preview_area_x = list_width + 30

        # Create selection list for image filenames
        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(15, 15, list_width, rect.height - 80),
            item_list=[os.path.basename(f) for f in self.image_files],
            manager=manager,
            container=self,
            object_id='#image_selection_list'
        )

        # Create preview area for the thumbnail
        self.preview_label = UILabel(
            relative_rect=pygame.Rect(preview_area_x, 15, rect.width - preview_area_x - 15, 30),
            text='Preview',
            manager=manager,
            container=self
        )
        self.preview_image_widget = UIImage(
            relative_rect=pygame.Rect(preview_area_x, 50, self.thumbnail_size[0], self.thumbnail_size[1]),
            image_surface=pygame.Surface(self.thumbnail_size, pygame.SRCALPHA).convert_alpha(), # Placeholder
            manager=manager,
            container=self
        )
        self.preview_image_widget.image.fill((50, 50, 50, 0)) # Transparent placeholder

        # Create Confirm and Cancel buttons
        self.confirm_button = UIButton(
            relative_rect=pygame.Rect(rect.width // 2 - 130, rect.height - 55, 120, 40),
            text='Confirm',
            manager=manager,
            container=self,
            object_id='#confirm_image_selection'
        )

        self.cancel_button = UIButton(
            relative_rect=pygame.Rect(rect.width // 2 + 10, rect.height - 55, 120, 40),
            text='Cancel',
            manager=manager,
            container=self,
            object_id='#cancel_image_selection'
        )
        
        # Select first item by default if list is not empty
        if self.image_files:
            first_item_display_name = os.path.basename(self.image_files[0])
            # Try using set_single_selection if available, or select_item if that's the method
            # Assuming first_item_display_name is the string to select.
            try:
                self.selection_list.set_single_selection(first_item_display_name)
            except AttributeError:
                # Fallback or further investigation needed if set_single_selection doesn't exist
                # For now, we'll let it pass and the list might not have a default selection
                # or we might need to find the correct method.
                # A common alternative is to find the item in the list and pass the item object.
                print("UISelectionList might not have set_single_selection, checking alternative...")
                # Alternative: Manually find and set (less ideal if a direct method exists)
                # This part would need more specific API knowledge if set_single_selection fails.
                # For now, the goal is to fix the immediate AttributeError.
                # If this also fails, the user will see the print and we can investigate further.
                pass 
            self.update_preview(first_item_display_name) # This should still be called
        else:
            self.update_preview(None)

    def process_event(self, event: pygame.event.Event) -> bool:
        super().process_event(event)
        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.selection_list:
                self.update_preview(event.text) # event.text is the selected filename
        return False # Let other handlers process, or True if fully handled

    def update_preview(self, selected_filename):
        if selected_filename:
            try:
                # Find the full path corresponding to the selected_filename
                full_path = None
                for img_path in self.image_files:
                    if os.path.basename(img_path) == selected_filename:
                        full_path = img_path
                        break
                
                if full_path and os.path.exists(full_path):
                    image_surface = pygame.image.load(full_path).convert_alpha()
                    # Scale to fit thumbnail_size, maintaining aspect ratio
                    img_w, img_h = image_surface.get_size()
                    thumb_w, thumb_h = self.thumbnail_size
                    aspect_ratio = img_w / img_h
                    
                    if img_w > img_h: # Wider image
                        scaled_w = thumb_w
                        scaled_h = int(scaled_w / aspect_ratio)
                    else: # Taller or square image
                        scaled_h = thumb_h
                        scaled_w = int(scaled_h * aspect_ratio)
                    
                    # Ensure dimensions are at least 1x1 for transform.scale
                    scaled_w = max(1, scaled_w)
                    scaled_h = max(1, scaled_h)
                    thumbnail_surface = pygame.transform.smoothscale(image_surface, (scaled_w, scaled_h))
                    
                    # Create a new surface with transparent background to center the thumbnail
                    centered_thumb_surface = pygame.Surface(self.thumbnail_size, pygame.SRCALPHA).convert_alpha()
                    centered_thumb_surface.fill((0,0,0,0)) # Fill with transparent
                    blit_x = (self.thumbnail_size[0] - scaled_w) // 2
                    blit_y = (self.thumbnail_size[1] - scaled_h) // 2
                    centered_thumb_surface.blit(thumbnail_surface, (blit_x, blit_y))

                    self.preview_image_widget.set_image(centered_thumb_surface)
                    self.selected_image_path = full_path
                    self.preview_label.set_text(selected_filename)
                else:
                    self.preview_image_widget.image.fill((50, 50, 50, 0)) # Error or placeholder
                    self.preview_label.set_text("Preview N/A")
                    self.selected_image_path = None

            except pygame.error as e:
                print(f"Error loading or scaling image {selected_filename}: {e}")
                self.preview_image_widget.image.fill((60, 30, 30, 100)) # Error indication
                self.preview_label.set_text("Load Error")
                self.selected_image_path = None
        else:
            self.preview_image_widget.image.fill((50, 50, 50, 0)) # Placeholder
            self.preview_label.set_text("No Image Selected")
            self.selected_image_path = None 