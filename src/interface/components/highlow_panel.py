import pygame as pg
import random
from src.utils import GameSettings, Logger
from src.interface.components.button import Button
from src.core import services

class HighLowPanel:
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.is_open = False
        
        # --- 全螢幕設定 ---
        self.width = GameSettings.SCREEN_WIDTH - 40
        self.height = GameSettings.SCREEN_HEIGHT - 40
        self.x = 20
        self.y = 20
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        
        # 顏色
        self.COLOR_BG = (10, 10, 15)      
        self.COLOR_ACCENT = (0, 255, 200) 
        self.COLOR_WARN = (255, 50, 50)   
        self.COLOR_TEXT = (200, 200, 200)
        self.COLOR_PANEL = (30, 30, 40)
        
        # 字體
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 48)
        self.font_freq = pg.font.Font("assets/fonts/Minecraft.ttf", 64)
        self.font_ui = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        
        # 關閉按鈕
        close_x = self.x + self.width - 40
        close_y = self.y + 10
        self.btn_close = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            close_x, close_y, 30, 30,
            self.close
        )
        
        # --- 遊戲邏輯 ---
        self.energy_cost = 100 
        self.current_val = 0   
        self.next_val = 0      
        self.state = "IDLE"    
        self.message = "SYSTEM STANDBY..."
        self.message_color = self.COLOR_ACCENT
        
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        
        # --- [修正] 建立按鈕並手動記錄 Rect (避免 Button 無 rect 屬性報錯) ---
        
        # 1. HIGH 按鈕
        high_x, high_y = cx + 60, cy + 120
        self.rect_high = pg.Rect(high_x, high_y, 100, 50)
        self.btn_high = Button(
            "UI/raw/UI_Flat_Button02a_2.png", 
            "UI/raw/UI_Flat_Button02a_1.png", 
            high_x, high_y, 100, 50, 
            lambda: self.guess("HIGH")
        )

        # 2. LOW 按鈕
        low_x, low_y = cx - 160, cy + 120
        self.rect_low = pg.Rect(low_x, low_y, 100, 50)
        self.btn_low = Button(
            "UI/raw/UI_Flat_Button02a_2.png", 
            "UI/raw/UI_Flat_Button02a_1.png", 
            low_x, low_y, 100, 50, 
            lambda: self.guess("LOW")
        )
        
        # 3. START 按鈕
        start_x, start_y = cx - 100, cy + 120
        self.rect_start = pg.Rect(start_x, start_y, 200, 60)
        self.btn_start = Button(
            "UI/button_play.png", "UI/button_play_hover.png", 
            start_x, start_y, 200, 60, self.start_tuning
        )

        # 能量調整按鈕 (右下角)
        self.bet_ui_elements = [] 
        btn_w, btn_h, gap = 60, 30, 10
        start_x_bet = self.x + self.width - (btn_w * 5 + gap * 4) - 20 
        start_y_bet = self.y + self.height - 50
        
        opts = [("CLR", 0), ("+10", 10), ("+100", 100), ("+1k", 1000), ("MAX", -1)]
        for i, (label, val) in enumerate(opts):
            bx = start_x_bet + i * (btn_w + gap)
            brect = pg.Rect(bx, start_y_bet, btn_w, btn_h)
            
            if val == 0: func = lambda: self.set_cost(0)
            elif val == -1: func = lambda: self.max_cost()
            else: func = lambda v=val: self.adjust_cost(v)
                
            b_obj = Button(
                "UI/raw/UI_Flat_Button02a_2.png", 
                "UI/raw/UI_Flat_Button02a_1.png", 
                bx, start_y_bet, btn_w, btn_h, func
            )
            self.bet_ui_elements.append((b_obj, brect, label))

    def open(self):
        self.is_open = True
        self.reset_round()

    def close(self):
        self.is_open = False

    def reset_round(self):
        self.state = "IDLE"
        self.message = "READY TO SCAN..."
        self.message_color = self.COLOR_ACCENT
        self.current_val = 0
        self.next_val = 0

    # --- 資源系統 ---
    def get_battery(self):
        for item in self.game_manager.bag._items_data:
            if item['name'] == 'Coins': return item['count']
        return 0

    def adjust_cost(self, amount):
        if self.state != "IDLE": return
        bat = self.get_battery()
        if self.energy_cost + amount <= bat: self.energy_cost += amount
        else: self.energy_cost = bat 

    def set_cost(self, amount):
        if self.state != "IDLE": return
        self.energy_cost = amount

    def max_cost(self):
        if self.state != "IDLE": return
        self.energy_cost = self.get_battery()

    # --- 遊戲流程 ---
    def start_tuning(self):
        if self.state != "IDLE": return
        
        if self.energy_cost <= 0:
            self.message = "NO ENERGY INPUT!"
            self.message_color = self.COLOR_WARN
            return
        
        bat = self.get_battery()
        if bat < self.energy_cost:
            self.message = "LOW BATTERY!"
            self.message_color = self.COLOR_WARN
            return
            
        for item in self.game_manager.bag._items_data:
            if item['name'] == 'Coins':
                item['count'] -= self.energy_cost
                break
        
        self.current_val = random.randint(1, 13)
        self.state = "TUNING"
        self.message = f"SIGNAL DETECTED: {self.get_freq_str(self.current_val)} MHz"
        self.message_color = (255, 255, 255)

    def guess(self, choice):
        if self.state != "TUNING": return
        
        self.next_val = random.randint(1, 13)
        while self.next_val == self.current_val:
            self.next_val = random.randint(1, 13)
            
        success = False
        if choice == "HIGH" and self.next_val > self.current_val: success = True
        elif choice == "LOW" and self.next_val < self.current_val: success = True
        
        self.state = "RESULT"
        next_freq = self.get_freq_str(self.next_val)
        
        if success:
            reward = self.energy_cost * 2
            self.message = f"SIGNAL LOCKED! {next_freq} MHz. CHARGED +{reward}"
            self.message_color = self.COLOR_ACCENT
            
            found = False
            for item in self.game_manager.bag._items_data:
                if item['name'] == 'Coins':
                    item['count'] += reward
                    found = True
                    break
            if not found:
                 self.game_manager.bag._items_data.append({"name": "Coins", "count": reward, "sprite_path": "ingame_ui/coin.png", "option": 0})
        else:
            self.message = f"SIGNAL LOST... STATIC NOISE DETECTED!!"
            self.message_color = self.COLOR_WARN
            
            Logger.info("[Radio] Tuning failed. The Other World is leaking in...")
            self.game_manager.is_triggering_dark_event = True
            
            try:
                services.sound_manager.play_sound("static_noise.wav") 
            except:
                pass
            
        pg.time.set_timer(pg.USEREVENT + 2, 2500) 

    def get_freq_str(self, val):
        base = 88.0
        step = 1.5
        freq = base + (val * step)
        return f"{freq:.1f}"

    def update(self, dt, input_manager):
        if not self.is_open: return
        self.btn_close.update(dt)
        
        if self.state == "IDLE":
            self.btn_start.update(dt)
            for btn, _, _ in self.bet_ui_elements: btn.update(dt)
        elif self.state == "TUNING":
            self.btn_high.update(dt)
            self.btn_low.update(dt)
            
        for event in pg.event.get():
            if event.type == pg.USEREVENT + 2:
                if self.state == "RESULT":
                    self.reset_round()
                    pg.time.set_timer(pg.USEREVENT + 2, 0)

    def draw(self, screen):
        if not self.is_open: return
        
        # 1. 背景
        overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        overlay.fill(self.COLOR_BG)
        screen.blit(overlay, (0, 0))
        
        # 網格線
        for x in range(0, self.width, 50):
            pg.draw.line(screen, (20, 30, 40), (self.x + x, self.y), (self.x + x, self.y + self.height))
        for y in range(0, self.height, 50):
            pg.draw.line(screen, (20, 30, 40), (self.x, self.y + y), (self.x + self.width, self.y + y))

        pg.draw.rect(screen, (50, 50, 70), self.rect, 4, border_radius=5)
        
        self.btn_close.draw(screen)
        
        # 2. 標題
        title = self.font_title.render("SIGNAL TUNER", True, self.COLOR_ACCENT)
        title_shadow = self.font_title.render("SIGNAL TUNER", True, (0, 20, 20))
        screen.blit(title_shadow, (self.x + 42, self.y + 32))
        screen.blit(title, (self.x + 40, self.y + 30))
        
        # 3. 資源顯示
        bat = self.get_battery()
        bat_txt = self.font_ui.render(f"BATTERY: {bat}%", True, self.COLOR_ACCENT)
        screen.blit(bat_txt, (self.x + 40, self.y + self.height - 50))
        
        # 4. 消耗顯示
        cost_txt = self.font_ui.render(f"OUTPUT POWER: {self.energy_cost}", True, self.COLOR_TEXT)
        screen.blit(cost_txt, (self.x + 300, self.y + self.height - 50))
        
        # 5. 中央訊息
        msg = self.font_ui.render(self.message, True, self.message_color)
        screen.blit(msg, (self.x + self.width//2 - msg.get_width()//2, self.y + 100))
        
        cx, cy = self.x + self.width // 2, self.y + self.height // 2
        
        # 6. 繪製頻率顯示器
        self._draw_signal_box(screen, cx - 150, cy - 80, self.current_val, "CURRENT FREQ")
        
        display_next = self.next_val if self.state == "RESULT" else 0
        self._draw_signal_box(screen, cx + 50, cy - 80, display_next, "TARGET FREQ")
        
        # 7. 繪製按鈕 (使用 self.rect_*)
        if self.state == "IDLE":
            self.btn_start.draw(screen)
            # [修正] 使用 self.rect_start
            t = self.font_ui.render("SCAN", True, (255, 255, 255))
            screen.blit(t, (self.rect_start.centerx - t.get_width()//2, self.rect_start.centery - t.get_height()//2))
            
            for btn, rect, label in self.bet_ui_elements:
                btn.draw(screen)
                font_btn = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
                l = font_btn.render(label, True, (0, 0, 0))
                screen.blit(l, (rect.centerx - l.get_width()//2, rect.centery - l.get_height()//2))
                
        elif self.state == "TUNING":
            self.btn_low.draw(screen)
            # [修正] 使用 self.rect_low
            l = self.font_ui.render("DOWN", True, (0, 0, 0))
            screen.blit(l, (self.rect_low.centerx - l.get_width()//2, self.rect_low.centery - l.get_height()//2))
            
            self.btn_high.draw(screen)
            # [修正] 使用 self.rect_high
            h = self.font_ui.render("UP", True, (0, 0, 0))
            screen.blit(h, (self.rect_high.centerx - h.get_width()//2, self.rect_high.centery - h.get_height()//2))

    def _draw_signal_box(self, screen, x, y, val, label_text):
        w, h = 180, 120
        rect = pg.Rect(x, y, w, h)
        
        pg.draw.rect(screen, self.COLOR_PANEL, rect)
        pg.draw.rect(screen, (60, 60, 80), rect, 2)
        
        if val == 0:
            for _ in range(8):
                lx = random.randint(x + 5, x + w - 5)
                ly = random.randint(y + 5, y + h - 5)
                line_w = random.randint(5, 20)
                pg.draw.line(screen, (50, 60, 70), (lx, ly), (lx + line_w, ly), 2)
            
            wait_text = self.font_ui.render("NO SIGNAL", True, (80, 80, 100))
            screen.blit(wait_text, (rect.centerx - wait_text.get_width()//2, rect.centery - wait_text.get_height()//2))
        else:
            freq_str = self.get_freq_str(val)
            txt = self.font_freq.render(freq_str, True, self.COLOR_ACCENT)
            
            if txt.get_width() > w - 10:
                scale = (w - 20) / txt.get_width()
                new_w = int(txt.get_width() * scale)
                new_h = int(txt.get_height() * scale)
                txt = pg.transform.smoothscale(txt, (new_w, new_h))
            
            screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
            
            pg.draw.line(screen, self.COLOR_ACCENT, (rect.x + 20, rect.bottom - 20), (rect.right - 20, rect.bottom - 20), 2)
            
        lbl = self.font_ui.render(label_text, True, (150, 150, 150))
        screen.blit(lbl, (rect.x, rect.y - 30))