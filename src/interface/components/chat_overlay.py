import pygame as pg
from src.utils import GameSettings
from src.interface.components.component import UIComponent

class ChatOverlay(UIComponent):
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.active = False
        self.input_text = ""
        self.messages = [] # List of dicts: [{'id': 1, 'msg': 'hi'}, ...]
        
        # Fonts
        self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        
        # Dimensions
        self.width = 400
        self.height = 300
        self.x = 10
        self.y = GameSettings.SCREEN_HEIGHT - self.height - 10
        
        # Surface
        self.surface = pg.Surface((self.width, self.height), pg.SRCALPHA)
        
        # Input box
        self.input_rect = pg.Rect(self.x, self.y + self.height - 40, self.width, 35)
        self.cursor_blink = 0

    def toggle(self):
        self.active = not self.active
        # Clear input when opening
        if self.active:
            self.input_text = ""

    def set_state_change_callback(self, callback):
        self.on_state_change = callback

    def update(self, dt: float):
        if self.active:
            self.cursor_blink += dt

    def handle_input(self, event):
        if not self.active:
            return

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pg.K_RETURN:
                # Do nothing here, GameScene handles sending
                pass
            else:
                # Limit length
                if len(self.input_text) < 50:
                    self.input_text += event.unicode

    def draw(self, screen: pg.Surface):
        # Draw active background and input
        if self.active:
            # Draw semi-transparent background
            bg = pg.Surface((self.width, self.height), pg.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            screen.blit(bg, (self.x, self.y))
            
            # Draw input box
            pg.draw.rect(screen, (255, 255, 255), self.input_rect, 2)
            
            # Draw input text
            txt_surf = self.font.render(self.input_text, True, (255, 255, 255))
            screen.blit(txt_surf, (self.input_rect.x + 5, self.input_rect.y + 8))
            
            # Draw cursor
            if int(self.cursor_blink * 2) % 2 == 0:
                cx = self.input_rect.x + 5 + txt_surf.get_width()
                pg.draw.line(screen, (255, 255, 255), (cx, self.input_rect.y + 5), (cx, self.input_rect.y + 25), 2)

        # Draw messages (Reverse order to show newest at bottom)
        # Pick last 8 messages
        to_show = self.messages[-8:]
        
        start_y = self.y + self.height - 60
        
        for i, msg_data in enumerate(reversed(to_show)):
            # 解析訊息內容
            if isinstance(msg_data, dict):
                content = str(msg_data.get('msg', ''))
                pid = str(msg_data.get('id', '?'))
                display_text = f"P{pid}: {content}"
            else:
                display_text = str(msg_data)

            # ★★★ 修改點 1: 如果聊天室沒開，顯示最近 3 則 (原本是2) ★★★
            if not self.active and i >= 3:
                break
                
            # Render text
            shadow = self.font.render(display_text, True, (0, 0, 0))
            text = self.font.render(display_text, True, (255, 255, 255))
            
            # ★★★ 修改點 2: 計算淡出效果 (Alpha) ★★★
            if not self.active:
                # i=0 (最新): 255
                # i=1: 175
                # i=2: 95
                alpha = max(0, 255 - (i * 80))
                
                # 設定透明度
                shadow.set_alpha(alpha)
                text.set_alpha(alpha)
            else:
                # 開啟時保持全不透明
                shadow.set_alpha(255)
                text.set_alpha(255)
            
            # Position
            draw_y = start_y - i * 25
            
            # Draw
            screen.blit(shadow, (self.x + 7, draw_y + 1))
            screen.blit(text, (self.x + 5, draw_y))