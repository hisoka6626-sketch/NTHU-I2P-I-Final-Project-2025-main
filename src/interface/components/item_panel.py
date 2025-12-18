import pygame as pg
from src.interface.components.component import UIComponent
from src.sprites import Sprite
from src.utils import GameSettings

class ItemPanel(UIComponent):
    def __init__(self, items, callback=None):
        self.items = items  # List of item dicts
        self.callback = callback  # Function(item_index)
        self.is_open = False
        self.scroll_offset = 0
        self.SCROLL_SPEED = 25
        
        # Fonts
        self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        
        # UI Frame (尺寸擴大)
        self.surface = pg.Surface((600, 500), pg.SRCALPHA)
        self.rect = self.surface.get_rect(center=(GameSettings.SCREEN_WIDTH//2, GameSettings.SCREEN_HEIGHT//2))
        
        # Clipping area (加寬)
        self.clip_rect = pg.Rect(self.rect.x + 30, self.rect.y + 80, 540, 400)
        
        # Close Button
        self.close_button = Sprite("UI/button_x.png", (45, 45))
        self.close_rect = pg.Rect(self.rect.x + 535, self.rect.y + 20, 45, 45)
        
        # Colors
        self.COLOR_SCROLL_HANDLE = (50, 50, 50)

    def open(self, callback=None):
        self.is_open = True
        if callback:
            self.callback = callback
        self.scroll_offset = 0

    def close(self):
        self.is_open = False

    def update(self, dt, input_manager):
        if not self.is_open:
            return
            
        mx, my = input_manager.mouse_pos
        wheel = input_manager.mouse_wheel
        
        # Scroll logic
        if wheel != 0 and self.clip_rect.collidepoint((mx, my)):
            self.scroll_offset += wheel * self.SCROLL_SPEED
            
        # Clamp scroll
        row_h = 80
        total_h = max(self.clip_rect.height, len(self.items) * row_h)
        min_scroll = self.clip_rect.height - total_h
        
        if self.scroll_offset < min_scroll: self.scroll_offset = min_scroll
        if self.scroll_offset > 0: self.scroll_offset = 0
            
        # Close logic
        if self.close_rect.collidepoint((mx, my)) and input_manager.mouse_pressed(1):
            self.close()
            
        # Item click logic
        if input_manager.mouse_pressed(1):
            # Check clicks relative to scroll offset
            for idx, it in enumerate(self.items):
                # Calculate screen Y for this item
                item_local_y = idx * row_h + self.scroll_offset
                
                # Check if item is within view
                if 0 <= item_local_y <= self.clip_rect.height - row_h:
                    # Construct hit rect in screen coordinates
                    screen_item_y = self.clip_rect.y + item_local_y
                    item_rect = pg.Rect(self.clip_rect.x, screen_item_y, self.clip_rect.width - 20, row_h)
                    
                    if item_rect.collidepoint((mx, my)):
                        if self.callback:
                            self.callback(idx)
                        self.close()
                        break

    def draw(self, screen):
        if not self.is_open:
            return
            
        # Dark Background
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(160)
        dark.fill((0,0,0))
        screen.blit(dark, (0,0))
        
        # Panel Frame
        raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
        frame = pg.transform.smoothscale(raw, (self.rect.width, self.rect.height))
        screen.blit(frame, self.rect)
        
        # Title
        title = self.font.render("SELECT ITEM", True, (0,0,0))
        screen.blit(title, (self.rect.x + 40, self.rect.y + 25))
        
        # Close Button
        self.close_button.rect.topleft = (self.close_rect.x, self.close_rect.y)
        self.close_button.draw(screen)
        
        # Item List
        row_h = 80
        total_h = max(self.clip_rect.height, len(self.items) * row_h)
        temp_surface = pg.Surface((self.clip_rect.width, total_h), pg.SRCALPHA)
        
        y = 0 # Draw from 0 on temp_surface
        
        for idx, it in enumerate(self.items):
            # Separator line
            pg.draw.line(temp_surface, (200, 200, 200), (10, y + row_h - 2), (self.clip_rect.width - 30, y + row_h - 2), 2)
            
            # Icon
            icon = Sprite(it["sprite_path"], (56, 56))
            icon.rect.topleft = (10, y + 12)
            icon.draw(temp_surface)
            
            # Highlight potions
            border_col = None
            if "Heal" in it["name"]: border_col = (0, 200, 0)
            elif "Strength" in it["name"]: border_col = (200, 50, 50)
            elif "Defense" in it["name"]: border_col = (50, 50, 200)
            if border_col:
                pg.draw.rect(temp_surface, border_col, icon.rect, 2)
            
            # Name
            name = self.font.render(it["name"], True, (0,0,0))
            temp_surface.blit(name, (80, y + 15))
            
            # Count
            count = self.font_small.render(f"x{it['count']}", True, (50, 50, 50))
            temp_surface.blit(count, (self.clip_rect.width - 80, y + 30))
            
            y += row_h
            
        # Draw list with clip
        screen.set_clip(self.clip_rect)
        screen.blit(temp_surface, (self.clip_rect.x, self.clip_rect.y + self.scroll_offset))
        
        # Scrollbar
        self._draw_scrollbar(screen, self.clip_rect, total_h, self.scroll_offset)
        
        screen.set_clip(None)

    def _draw_scrollbar(self, screen, clip_rect, content_height, scroll_offset):
        if content_height <= clip_rect.height:
            return

        bar_w = 8
        margin = 4
        track_x = clip_rect.right - bar_w - margin
        track_y = clip_rect.top
        track_h = clip_rect.height

        viewable_ratio = clip_rect.height / content_height
        handle_h = max(30, track_h * viewable_ratio)
        
        scroll_ratio = abs(scroll_offset) / (content_height - clip_rect.height)
        track_scrollable_h = track_h - handle_h
        handle_y = track_y + (track_scrollable_h * scroll_ratio)

        pg.draw.rect(screen, self.COLOR_SCROLL_HANDLE, (track_x, handle_y, bar_w, handle_h), border_radius=4)