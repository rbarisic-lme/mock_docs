import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UIButton
from app.template_editor.constants import (
    ICON_MERGE_PATH,
    # Add new icon paths
)

ICON_MERGE_TO_TEXT = 'app/assets/icon_merge_to_text.png'
ICON_MERGE_TO_IMAGE = 'app/assets/icon_merge_to_image.png'
ICON_MERGE_TO_RECT = 'app/assets/icon_merge_to_rect.png'
ICON_MERGE_TO_OBFUSCATE = 'app/assets/icon_merge_to_obfuscate.png'

MERGE_TYPES = [
    ('text', ICON_MERGE_TO_TEXT, 'To Text'),
    ('image', ICON_MERGE_TO_IMAGE, 'To Image'),
    ('rectangle', ICON_MERGE_TO_RECT, 'To Rect'),
    ('obscure', ICON_MERGE_TO_OBFUSCATE, 'To Obfuscate'),
]

class MergeToolbarPanel(UIPanel):
    def __init__(self, manager, on_merge_callback=None):
        panel_w, panel_h = 4 * 56 + 5 * 12, 60
        super().__init__(pygame.Rect(0, 0, panel_w, panel_h), manager=manager, object_id='#merge_toolbar')
        self.on_merge_callback = on_merge_callback
        self.merge_btns = []
        btn_w, btn_h, gap = 56, 40, 12
        for i, (merge_type, icon_path, tooltip) in enumerate(MERGE_TYPES):
            btn = UIButton(
                relative_rect=pygame.Rect(12 + i * (btn_w + gap), 10, btn_w, btn_h),
                text='',
                manager=manager,
                container=self,
                object_id=f'#merge_multi_{merge_type}'
            )
            try:
                icon = pygame.image.load(icon_path).convert_alpha()
                btn.set_image(icon)
            except Exception:
                btn.set_text(tooltip)
            btn.merge_type = merge_type
            btn.tooltip = tooltip
            self.merge_btns.append(btn)
        self.hide()

    def update_for_selection(self, selected_indices, page_elements, zoom, canvas_x, canvas_y):
        if len(selected_indices) > 1:
            min_x = min(page_elements[idx]['x'] for idx in selected_indices)
            min_y = min(page_elements[idx]['y'] for idx in selected_indices)
            max_x = max(page_elements[idx]['x'] + page_elements[idx].get('width', 0) for idx in selected_indices)
            max_y = max(page_elements[idx]['y'] + page_elements[idx].get('height', 0) for idx in selected_indices)
            panel_w, panel_h = 4 * 56 + 5 * 12, 60
            panel_screen_x = int(canvas_x + min_x * zoom + (max_x - min_x) * zoom / 2 - panel_w / 2)
            panel_screen_y = int(canvas_y + max_y * zoom + 8)
            self.set_relative_position((panel_screen_x, panel_screen_y))
            self.set_dimensions((panel_w, panel_h))
            self.show()
        else:
            self.hide()

    def hide(self):
        self.visible = 0
        self.disable()

    def show(self):
        self.visible = 1
        self.enable()

    def process_event(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            for btn in self.merge_btns:
                if event.ui_element == btn:
                    if self.on_merge_callback:
                        self.on_merge_callback(btn.merge_type)
                    return True
        return super().process_event(event) 