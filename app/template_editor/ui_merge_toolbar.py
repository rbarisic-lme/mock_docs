import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UIButton

import os
from app.template_editor.constants import (
    _ASSETS_DIR,
)

ICON_MERGE_TO_TEXT = os.path.join(_ASSETS_DIR, 'icon_merge_to_text.png')
ICON_MERGE_TO_IMAGE = os.path.join(_ASSETS_DIR, 'icon_merge_to_image.png')
ICON_MERGE_TO_RECT = os.path.join(_ASSETS_DIR, 'icon_merge_to_rect.png')
ICON_MERGE_TO_OBFUSCATE = os.path.join(_ASSETS_DIR, 'icon_merge_to_obfuscate.png')

MERGE_TYPES = [
    ('text', ICON_MERGE_TO_TEXT, 'To Text'),
    ('image', ICON_MERGE_TO_IMAGE, 'To Image'),
    ('rectangle', ICON_MERGE_TO_RECT, 'To Rect'),
    ('obscure', ICON_MERGE_TO_OBFUSCATE, 'To Obfuscate'),
]

BUTTON_HEIGHT=40
BUTTON_WIDTH=40
BUTTON_GAP=12


class MergeToolbarPanel(UIPanel):
    def __init__(self, manager, on_merge_callback=None):
        panel_w = len(MERGE_TYPES) * BUTTON_WIDTH + (len(MERGE_TYPES) + 1) * BUTTON_GAP
        panel_h = BUTTON_HEIGHT + 2 * BUTTON_GAP
        super().__init__(pygame.Rect(0, 0, panel_w, panel_h), manager=manager, object_id='#merge_toolbar')
        self.on_merge_callback = on_merge_callback
        self.merge_btns = []
        
        for i, (merge_type, icon_path, tooltip) in enumerate(MERGE_TYPES):
            btn = UIButton(
                relative_rect=pygame.Rect(BUTTON_GAP + i * (BUTTON_WIDTH + BUTTON_GAP), BUTTON_GAP, BUTTON_WIDTH, BUTTON_HEIGHT),
                text='',
                manager=manager,
                container=self,
                object_id=f'#merge_multi_{merge_type}',
            )

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
            panel_w = len(MERGE_TYPES) * BUTTON_WIDTH + (len(MERGE_TYPES) + 1) * BUTTON_GAP
            panel_h = BUTTON_HEIGHT + 2 * BUTTON_GAP
            panel_screen_x = int(canvas_x + min_x * zoom + (max_x - min_x) * zoom / 2 - panel_w / 2)
            panel_screen_y = int(canvas_y + max_y * zoom + BUTTON_GAP)
            self.set_relative_position((panel_screen_x, panel_screen_y))
            self.set_dimensions((panel_w, panel_h))
            self.show()
        else:
            self.hide()

    def process_event(self, event):
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            for btn in self.merge_btns:
                if event.ui_element == btn:
                    if self.on_merge_callback:
                        self.on_merge_callback(btn.merge_type)
                    return True
        return super().process_event(event)