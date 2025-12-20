import pygame as pg
from src.utils import GameSettings
from src.interface.components.button import Button
from src.core.services import input_manager

class StoryConfirmationPanel:
    def __init__(self, on_confirm, on_cancel):
        self.is_open = False
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        
        # --- UI 外觀設定 ---
        self.width = 500
        self.height = 300
        self.x = (GameSettings.SCREEN_WIDTH - self.width) // 2
        self.y = (GameSettings.SCREEN_HEIGHT - self.height) // 2
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        
        # 背景：深紅色半透明 (警告感)
        self.bg_surface = pg.Surface((self.width, self.height), pg.SRCALPHA)
        self.bg_surface.fill((30, 0, 0, 230)) 
        
        # 字體
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 32)
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
        
        # --- 按鈕設定 ---
        btn_y = self.y + 200
        btn_w = 120
        btn_h = 50
        
        # 1. Yes 按鈕位置
        yes_x = self.x + 80
        # [修改] 自己記錄 Rect，避免依賴 Button 內部的實作
        self.rect_yes = pg.Rect(yes_x, btn_y, btn_w, btn_h)
        
        self.btn_yes = Button(
            "UI/raw/UI_Flat_Button02a_2.png", 
            "UI/raw/UI_Flat_Button02a_1.png", 
            yes_x, btn_y, btn_w, btn_h, self._confirm_click
        )

        # 2. No 按鈕位置
        no_x = self.x + 300
        # [修改] 自己記錄 Rect
        self.rect_no = pg.Rect(no_x, btn_y, btn_w, btn_h)

        self.btn_no = Button(
            "UI/raw/UI_Flat_Button02a_2.png", 
            "UI/raw/UI_Flat_Button02a_1.png", 
            no_x, btn_y, btn_w, btn_h, self._cancel_click
        )

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def _confirm_click(self):
        self.close()
        if self.on_confirm:
            self.on_confirm()

    def _cancel_click(self):
        self.close()
        if self.on_cancel:
            self.on_cancel()

    def update(self, dt):
        if not self.is_open: return
        
        self.btn_yes.update(dt)
        self.btn_no.update(dt)
        
        # 鍵盤支援 (Y / N)
        if input_manager.key_pressed(pg.K_y):
            self._confirm_click()
        elif input_manager.key_pressed(pg.K_n) or input_manager.key_pressed(pg.K_ESCAPE):
            self._cancel_click()

    def draw(self, screen):
        if not self.is_open: return
        
        # 1. 畫背景與邊框
        screen.blit(self.bg_surface, (self.x, self.y))
        pg.draw.rect(screen, (200, 50, 50), self.rect, 4, border_radius=10)
        
        # 2. 標題
        title = self.font_title.render("WARNING", True, (255, 50, 50))
        screen.blit(title, (self.x + self.width//2 - title.get_width()//2, self.y + 30))
        
        # 3. 內文
        msg1 = self.font_text.render("Anomalous signal detected.", True, (255, 255, 255))
        msg2 = self.font_text.render("Enter Memory Sequence?", True, (255, 255, 255))
        
        screen.blit(msg1, (self.x + self.width//2 - msg1.get_width()//2, self.y + 90))
        screen.blit(msg2, (self.x + self.width//2 - msg2.get_width()//2, self.y + 120))
        
        # 4. 畫按鈕圖片
        self.btn_yes.draw(screen)
        self.btn_no.draw(screen)
        
        # 5. 畫按鈕文字 (使用我們自己記錄的 rect_yes/rect_no 來置中)
        yes_txt = self.font_text.render("YES (Y)", True, (0, 0, 0))
        no_txt = self.font_text.render("NO (N)", True, (0, 0, 0))
        
        screen.blit(yes_txt, (self.rect_yes.centerx - yes_txt.get_width()//2, self.rect_yes.centery - yes_txt.get_height()//2))
        screen.blit(no_txt, (self.rect_no.centerx - no_txt.get_width()//2, self.rect_no.centery - no_txt.get_height()//2))