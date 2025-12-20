import pygame as pg
import random
import math
from src.utils import GameSettings, Logger
from src.interface.components.button import Button
from src.core import services

class RoulettePanel:
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.is_open = False
        
        # --- 全螢幕設定 ---
        self.width = GameSettings.SCREEN_WIDTH - 40
        self.height = GameSettings.SCREEN_HEIGHT - 40
        self.x = 20
        self.y = 20
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        
        # 顏色定義
        self.COLOR_BG = (0, 50, 0)       
        self.COLOR_GOLD = (255, 215, 0)  
        self.COLOR_RED = (200, 0, 0)
        self.COLOR_BLACK = (20, 20, 20)
        self.COLOR_TEXT = (255, 255, 255)
        
        # 字體
        self.font_large = pg.font.Font("assets/fonts/Minecraft.ttf", 48)
        self.font_medium = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        self.font_wheel = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        
        # --- 關閉按鈕 ---
        close_x = self.x + self.width - 40
        close_y = self.y + 10
        self.close_btn_rect = pg.Rect(close_x, close_y, 30, 30)
        self.btn_close = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            close_x, close_y, 30, 30,
            self.close
        )
        
        # --- 輪盤資料 ---
        self.wheel_numbers = [
            0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 
            10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
        ]
        self.red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

        # --- 遊戲狀態 ---
        self.wager_amount = 100 
        self.current_spin_bet = 0 
        self.selected_bet_key = None 
        self.state = "IDLE"    
        self.result_number = 0
        self.message = "PLACE YOUR BET"
        self.message_color = self.COLOR_GOLD
        
        # --- 動畫變數 (基於時間插值) ---
        self.angle = 0.0         
        self.ball_angle = 0.0    
        self.spin_timer = 0.0
        self.total_spin_time = 11.0 
        
        self.start_angle = 0.0
        self.start_ball_angle = 0.0
        self.total_rotation_needed = 0.0

        self.wheel_center_x = self.x + 220 
        self.wheel_center_y = self.y + self.height // 2 - 20
        self.wheel_radius = 180 

        # --- 建構賭桌區域 ---
        self.bet_zones = {} 
        self._init_betting_table()

        # Spin 按鈕
        spin_x = self.wheel_center_x - 100
        spin_y = self.wheel_center_y + 200
        self.spin_btn_rect = pg.Rect(spin_x, spin_y, 200, 50)
        self.btn_spin = Button(
            "UI/button_play.png", "UI/button_play_hover.png", 
            spin_x, spin_y, 200, 50, 
            self.start_spin
        )

        # --- 金額調整按鈕 ---
        self.bet_ui_elements = [] 
        btn_w = 60
        btn_h = 30
        gap = 10
        start_x = self.x + self.width - (btn_w * 5 + gap * 4) - 20 
        start_y = self.y + self.height - 50
        
        bet_opts = [
            ("CLR", 0), ("+10", 10), ("+100", 100), ("+1k", 1000), ("MAX", -1)
        ]
        
        for i, (label, val) in enumerate(bet_opts):
            bx = start_x + i * (btn_w + gap)
            by = start_y
            brect = pg.Rect(bx, by, btn_w, btn_h)
            
            if val == 0:
                func = lambda: self.set_wager(0)
            elif val == -1:
                func = lambda: self.max_wager()
            else:
                func = lambda v=val: self.adjust_wager(v)
            
            # 使用新的淺色按鈕圖片
            b_obj = Button(
                "UI/raw/UI_Flat_Button02a_2.png", 
                "UI/raw/UI_Flat_Button02a_1.png", 
                bx, by, btn_w, btn_h, func
            )
            self.bet_ui_elements.append((b_obj, brect, label))

    def _init_betting_table(self):
        table_x = self.x + 480
        table_y = self.y + 100
        cell_w = 55
        cell_h = 65
        
        for n in range(1, 37):
            col = (n - 1) // 3
            row = 2 - ((n - 1) % 3)
            rx = table_x + col * cell_w
            ry = table_y + row * cell_h
            self.bet_zones[f"NUM_{n}"] = pg.Rect(rx, ry, cell_w, cell_h)

        self.bet_zones["NUM_0"] = pg.Rect(table_x - cell_w, table_y, cell_w, cell_h * 3)

        bottom_y = table_y + cell_h * 3 + 15
        section_w = (cell_w * 12) // 6 
        
        options = ["1-18", "EVEN", "RED", "BLACK", "ODD", "19-36"]
        for i, opt in enumerate(options):
            rx = table_x + i * section_w
            self.bet_zones[opt] = pg.Rect(rx, bottom_y, section_w, 60)

    def open(self):
        self.is_open = True
        self.state = "IDLE"
        self.message = "CHOOSE BET AMOUNT & TABLE"
        self.message_color = self.COLOR_GOLD
        self.selected_bet_key = None
        self.wager_amount = 100 

    def close(self):
        self.is_open = False
        try:
            services.sound_manager.stop_bgm() 
        except:
            pass

    def get_player_money(self):
        for item in self.game_manager.bag._items_data:
            if item['name'] == 'Coins':
                return item['count']
        return 0

    def adjust_wager(self, amount):
        if self.state != "IDLE": return
        money = self.get_player_money()
        if self.wager_amount + amount <= money:
            self.wager_amount += amount
        else:
            self.wager_amount = money 

    def set_wager(self, amount):
        if self.state != "IDLE": return
        self.wager_amount = amount

    def max_wager(self):
        if self.state != "IDLE": return
        self.wager_amount = self.get_player_money()

    def handle_table_click(self, pos):
        if self.state != "IDLE": return
        
        for key, rect in self.bet_zones.items():
            if rect.collidepoint(pos):
                self.selected_bet_key = key
                if "NUM" in key:
                    num = key.split("_")[1]
                    self.message = f"BET ON {num} (x35)"
                else:
                    self.message = f"BET ON {key} (x1)"
                self.message_color = self.COLOR_TEXT
                return

    def start_spin(self):
        if self.state != "IDLE": return
        
        if self.wager_amount <= 0:
            self.message = "PLEASE SET A BET AMOUNT!"
            self.message_color = (255, 50, 50)
            return

        if self.selected_bet_key is None:
            self.message = "PLEASE SELECT A SPOT ON TABLE!"
            self.message_color = (255, 50, 50)
            return

        from src.core.dev_tools import dev_tool
        
        if not (dev_tool.active and dev_tool.casino_hack_mode):
            player_bag = self.game_manager.bag
            has_coins = False
            coin_item = None
            for item in player_bag._items_data:
                if item['name'] == 'Coins' and item['count'] >= self.wager_amount:
                    has_coins = True
                    coin_item = item
                    break
            
            if not has_coins:
                self.message = "NOT ENOUGH MONEY!"
                self.message_color = (255, 50, 50)
                return
            
            coin_item['count'] -= self.wager_amount
            Logger.info(f"[Roulette] Deducted {self.wager_amount} coins.")
        
        self.current_spin_bet = self.wager_amount
        
        self.state = "SPINNING"
        self.spin_timer = 0.0
        self.message = "GOOD LUCK!"
        self.message_color = self.COLOR_GOLD
        
        try:
            services.sound_manager.play_sound("roulette-game-429833.mp3")
        except:
            pass

        if dev_tool.active and dev_tool.casino_hack_mode:
            target = 0
            key = self.selected_bet_key
            if "NUM" in key: target = int(key.split("_")[1])
            elif key == "RED": target = 1 
            elif key == "BLACK": target = 2 
            elif key == "EVEN": target = 2
            elif key == "ODD": target = 1
            elif key == "1-18": target = 1
            elif key == "19-36": target = 36
            self.final_target = target
        else:
            # === 黑心邏輯開始 (Black Heart Logic) ===
            # 1. 先隨機產生一個結果
            candidate = random.choice(self.wheel_numbers)
            
            # 2. 判斷這個結果是否會讓玩家贏
            will_win = False
            k = self.selected_bet_key
            n = candidate
            
            is_red = n in self.red_numbers
            is_black = n not in self.red_numbers and n != 0
            is_even = (n % 2 == 0) and n != 0
            is_odd = (n % 2 != 0) and n != 0
            is_low = (1 <= n <= 18)
            is_high = (19 <= n <= 36)

            if k == f"NUM_{n}": will_win = True
            elif k == "RED" and is_red: will_win = True
            elif k == "BLACK" and is_black: will_win = True
            elif k == "EVEN" and is_even: will_win = True
            elif k == "ODD" and is_odd: will_win = True
            elif k == "1-18" and is_low: will_win = True
            elif k == "19-36" and is_high: will_win = True
            
            # 3. 黑心操作：如果玩家會贏，有 30% 機率強制換成會輸的數字
            RIG_CHANCE = 0.3  # 30% 機率作弊
            
            if will_win and random.random() < RIG_CHANCE:
                # 找出所有會導致輸的數字
                losing_candidates = []
                for x in self.wheel_numbers:
                    # 模擬檢查 x 是否會贏
                    w = False
                    xr = x in self.red_numbers
                    xb = x not in self.red_numbers and x != 0
                    xe = (x % 2 == 0) and x != 0
                    xo = (x % 2 != 0) and x != 0
                    xl = (1 <= x <= 18)
                    xh = (19 <= x <= 36)
                    
                    if k == f"NUM_{x}": w = True
                    elif k == "RED" and xr: w = True
                    elif k == "BLACK" and xb: w = True
                    elif k == "EVEN" and xe: w = True
                    elif k == "ODD" and xo: w = True
                    elif k == "1-18" and xl: w = True
                    elif k == "19-36" and xh: w = True
                    
                    if not w:
                        losing_candidates.append(x)
                
                # 如果有會輸的數字，從中隨機挑一個取代原本的結果
                if losing_candidates:
                    candidate = random.choice(losing_candidates)
                    Logger.info(f"[Roulette] Black Heart triggered! Changed win to loss ({candidate})")
            
            self.final_target = candidate
            # === 黑心邏輯結束 ===

        self.start_angle = self.angle
        self.start_ball_angle = self.ball_angle
        
        target_idx = self.wheel_numbers.index(self.final_target)
        slice_angle = 360.0 / 37.0
        target_relative_angle = target_idx * slice_angle + (slice_angle / 2.0)
        
        current_relative_angle = (self.start_ball_angle - self.start_angle) % 360.0
        diff = (current_relative_angle - target_relative_angle) % 360.0
        laps = 15
        self.total_rotation_needed = diff + 360.0 * laps

    def update(self, dt, input_manager):
        if not self.is_open: return
        
        self.btn_close.update(dt)
        
        if self.state == "IDLE":
            self.btn_spin.update(dt)
            for btn, rect, label in self.bet_ui_elements:
                btn.update(dt)

            if pg.mouse.get_pressed()[0]: 
                mouse_pos = pg.mouse.get_pos()
                clicked_ui = False
                if self.spin_btn_rect.collidepoint(mouse_pos): clicked_ui = True
                if self.close_btn_rect.collidepoint(mouse_pos): clicked_ui = True
                for btn, rect, label in self.bet_ui_elements:
                    if rect.collidepoint(mouse_pos): clicked_ui = True
                
                if not clicked_ui:
                     self.handle_table_click(mouse_pos)

        elif self.state == "SPINNING":
            self.spin_timer += dt
            t = min(self.spin_timer / self.total_spin_time, 1.0)
            ease_val = t * (2 - t)
            
            current_rotation = self.total_rotation_needed * ease_val
            
            ball_delta = current_rotation * (1.0 / 1.3)
            wheel_delta = current_rotation * (0.3 / 1.3)
            
            self.ball_angle = (self.start_ball_angle - ball_delta) % 360.0
            self.angle = (self.start_angle + wheel_delta) % 360.0
            
            if t >= 1.0:
                self.state = "RESULT"
                self.check_win()

    def check_win(self):
        res = self.final_target
        
        is_red = res in self.red_numbers
        is_black = res not in self.red_numbers and res != 0
        is_even = (res % 2 == 0) and res != 0
        is_odd = (res % 2 != 0) and res != 0
        is_low = (1 <= res <= 18)
        is_high = (19 <= res <= 36)
        
        won = False
        multiplier = 0
        
        key = self.selected_bet_key
        
        if key == f"NUM_{res}": won = True; multiplier = 35
        elif key == "RED" and is_red: won = True; multiplier = 1
        elif key == "BLACK" and is_black: won = True; multiplier = 1
        elif key == "EVEN" and is_even: won = True; multiplier = 1
        elif key == "ODD" and is_odd: won = True; multiplier = 1
        elif key == "1-18" and is_low: won = True; multiplier = 1
        elif key == "19-36" and is_high: won = True; multiplier = 1
            
        if won:
            payout = self.current_spin_bet + (self.current_spin_bet * multiplier)
            self.message = f"WIN! NUMBER: {res} | PAYOUT: {payout}"
            self.message_color = (0, 255, 0)
            Logger.info(f"[Roulette] Player Won! Payout: {payout}")
            
            found = False
            for item in self.game_manager.bag._items_data:
                if item['name'] == 'Coins':
                    item['count'] += payout
                    found = True
                    break
            if not found:
                 self.game_manager.bag._items_data.append({
                    "name": "Coins", "count": payout, "sprite_path": "ingame_ui/coin.png", "option": 0
                })
        else:
            self.message = f"RESULT: {res}. YOU LOST {self.current_spin_bet}."
            self.message_color = (255, 50, 50)
            Logger.info(f"[Roulette] Player Lost. Result: {res}")
            
        pg.time.set_timer(pg.USEREVENT + 1, 4000) 
        self.state = "IDLE"

    def draw(self, screen):
        if not self.is_open: return
        
        overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        overlay.fill(self.COLOR_BG) 
        screen.blit(overlay, (0, 0))
        
        pg.draw.rect(screen, self.COLOR_GOLD, self.rect, 8, border_radius=5) 
        pg.draw.rect(screen, (0, 0, 0), self.rect, 2, border_radius=5) 
        
        self.btn_close.draw(screen)
        self._draw_wheel(screen)
        self._draw_betting_table(screen)
        
        title = self.font_large.render("ROULETTE", True, self.COLOR_GOLD)
        title_shadow = self.font_large.render("ROULETTE", True, (0,0,0))
        screen.blit(title_shadow, (self.x + 32, self.y + 22))
        screen.blit(title, (self.x + 30, self.y + 20))
        
        money = self.get_player_money()
        money_txt = self.font_medium.render(f"COINS: {money}", True, self.COLOR_GOLD)
        screen.blit(money_txt, (self.x + 40, self.y + self.height - 50))

        # BET 文字位置
        wager_txt = self.font_medium.render(f"BET: {self.wager_amount}", True, self.COLOR_TEXT)
        screen.blit(wager_txt, (self.x + 450, self.y + self.height - 50))

        msg_y = self.y + self.height - 120
        msg_bg = pg.Surface((self.width - 40, 50))
        msg_bg.set_alpha(150)
        msg_bg.fill((0, 0, 0))
        screen.blit(msg_bg, (self.x + 20, msg_y))
        
        msg_surf = self.font_medium.render(self.message, True, self.message_color)
        screen.blit(msg_surf, (self.x + self.width//2 - msg_surf.get_width()//2, msg_y + 10))

        if self.state == "IDLE":
            self.btn_spin.draw(screen)
            for btn, rect, label in self.bet_ui_elements:
                btn.draw(screen)
                l_surf = self.font_small.render(label, True, (0, 0, 0))
                lx = rect.centerx - l_surf.get_width() // 2
                ly = rect.centery - l_surf.get_height() // 2
                screen.blit(l_surf, (lx, ly))

    def _draw_wheel(self, screen):
        cx, cy = self.wheel_center_x, self.wheel_center_y
        rad = self.wheel_radius
        
        pg.draw.circle(screen, (80, 50, 20), (cx, cy), rad + 15)
        pg.draw.circle(screen, self.COLOR_GOLD, (cx, cy), rad + 15, 6)
        
        num_count = 37
        slice_angle = 360 / num_count
        
        for i, num in enumerate(self.wheel_numbers):
            start_a = i * slice_angle + self.angle
            end_a = (i + 1) * slice_angle + self.angle
            start_rad = math.radians(start_a)
            end_rad = math.radians(end_a)
            
            points = [(cx, cy)]
            steps = 4
            for j in range(steps + 1):
                a = start_rad + (end_rad - start_rad) * j / steps
                px = cx + math.cos(a) * rad
                py = cy + math.sin(a) * rad
                points.append((px, py))
            
            if num == 0: color = (0, 150, 0)
            elif num in self.red_numbers: color = (180, 0, 0)
            else: color = (30, 30, 30)
            
            pg.draw.polygon(screen, color, points)
            
            mid_angle = start_a + (end_a - start_a) / 2
            mid_rad = math.radians(mid_angle)
            text_dist = rad * 0.88
            tx = cx + math.cos(mid_rad) * text_dist
            ty = cy + math.sin(mid_rad) * text_dist
            
            rot_angle = -mid_angle - 90 
            num_surf = self.font_wheel.render(str(num), True, (255, 255, 255))
            rotated_num = pg.transform.rotate(num_surf, rot_angle)
            r_rect = rotated_num.get_rect(center=(tx, ty))
            screen.blit(rotated_num, r_rect)
            
        ball_dist = rad * 0.75
        bx = cx + math.cos(math.radians(self.ball_angle)) * ball_dist
        by = cy + math.sin(math.radians(self.ball_angle)) * ball_dist
        
        pg.draw.circle(screen, (0, 0, 0), (bx + 2, by + 2), 7)
        pg.draw.circle(screen, (220, 220, 220), (bx, by), 7)
        pg.draw.circle(screen, (255, 255, 255), (bx - 2, by - 2), 3)
        
        pg.draw.circle(screen, self.COLOR_GOLD, (cx, cy), rad * 0.65, 3)
        pg.draw.circle(screen, (0,0,0), (cx, cy), rad * 0.65, 1)
        pg.draw.circle(screen, self.COLOR_GOLD, (cx, cy), 15)
        
        pg.draw.polygon(screen, self.COLOR_GOLD, [
            (cx, cy - rad - 20),
            (cx - 10, cy - rad - 5),
            (cx + 10, cy - rad - 5)
        ])

    def _draw_betting_table(self, screen):
        mouse_pos = pg.mouse.get_pos()
        
        for key, rect in self.bet_zones.items():
            color = (0, 80, 0)
            if "NUM" in key:
                n = int(key.split("_")[1])
                if n == 0: color = (0, 120, 0)
                elif n in self.red_numbers: color = (150, 0, 0)
                else: color = (30, 30, 30)
            elif key == "RED": color = (150, 0, 0)
            elif key == "BLACK": color = (30, 30, 30)
            
            border_color = (150, 150, 150)
            border_width = 1
            
            if key == self.selected_bet_key:
                border_color = self.COLOR_GOLD
                border_width = 4
            elif rect.collidepoint(mouse_pos) and self.state == "IDLE":
                border_color = (255, 255, 255)
                border_width = 2
            
            pg.draw.rect(screen, color, rect)
            pg.draw.rect(screen, border_color, rect, border_width)
            
            label = key
            if "NUM" in key:
                label = str(key.split("_")[1])
                
            txt_surf = self.font_medium.render(label, True, (255, 255, 255))
            if len(label) > 3: 
                txt_surf = self.font_small.render(label, True, (255, 255, 255))
            
            tx = rect.centerx - txt_surf.get_width() // 2
            ty = rect.centery - txt_surf.get_height() // 2
            screen.blit(txt_surf, (tx, ty))
            
            if key == self.selected_bet_key:
                pg.draw.circle(screen, self.COLOR_GOLD, rect.center, 18)
                pg.draw.circle(screen, (255, 255, 255), rect.center, 12, 1)
                pg.draw.circle(screen, (255, 255, 255), rect.center, 16, 1)