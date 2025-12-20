import pygame as pg
from src.utils import GameSettings
from src.core import GameManager
from src.interface.components.component import UIComponent
from src.core.services import input_manager
from src.sprites import Sprite

class BackpackPanel(UIComponent):
    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.is_open = False

        # ------------------------------
        # UI 畫框與基礎設定 (更寬版)
        # ------------------------------
        raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
        # [修改 1] 寬度增加到 1100，高度維持 650
        frame_w, frame_h = 1100, 650 
        self.surface = pg.transform.smoothscale(raw, (frame_w, frame_h))

        x = (GameSettings.SCREEN_WIDTH - frame_w) // 2
        y = (GameSettings.SCREEN_HEIGHT - frame_h) // 2
        self.rect = pg.Rect(x, y, frame_w, frame_h)

        # 橫幅圖片 (配合列表加寬)
        banner_raw = pg.image.load("assets/images/UI/raw/UI_Flat_Banner03a.png").convert_alpha()
        # [修改 2] 橫幅拉寬到 470
        self.banner = pg.transform.smoothscale(banner_raw, (470, 80)) 

        # Fonts
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 36)
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 22)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        self.font_tiny = pg.font.Font("assets/fonts/Minecraft.ttf", 14)

        # 關閉按鈕
        self.close_button = Sprite("UI/button_x.png", (45, 45))
        self.close_rect = pg.Rect(x + frame_w - 65, y + 25, 45, 45)

        # ------------------------------
        # 滾動與裁切區域
        # ------------------------------
        self.scroll_monster = 0
        self.scroll_item = 0
        self.SCROLL_SPEED = 30

        # [修改 3] 定義區域：列表寬度增加到 480
        # 左側(怪物) 起點 x+50
        self.clip_mon = pg.Rect(x + 50, y + 100, 480, 510)
        # 右側(道具) 起點 x+570 (留中間間距)
        self.clip_item = pg.Rect(x + 570, y + 100, 480, 510)

        # 顏色定義
        self.COLOR_HP_HIGH = (46, 204, 113)   # Green
        self.COLOR_HP_MED = (241, 196, 15)    # Yellow/Orange
        self.COLOR_HP_LOW = (231, 76, 60)     # Red
        self.COLOR_EXP = (52, 152, 219)       # Blue
        self.COLOR_BG_BAR = (50, 50, 50)      # Dark Grey
        self.COLOR_SCROLL_HANDLE = (50, 50, 50) 

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False

    def update(self, dt: float):
        if not self.is_open:
            return

        # 關閉與 ESC
        if self.close_rect.collidepoint(input_manager.mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()

        # 滾動偵測
        mx, my = input_manager.mouse_pos
        wheel = input_manager.mouse_wheel

        if wheel != 0:
            if self.clip_mon.collidepoint((mx, my)):
                self.scroll_monster += wheel * self.SCROLL_SPEED
            if self.clip_item.collidepoint((mx, my)):
                self.scroll_item += wheel * self.SCROLL_SPEED

        # 限制滾動範圍
        mon_count = len(self.game_manager.bag._monsters_data)
        mon_h = max(self.clip_mon.height, mon_count * 90)
        min_scr_mon = self.clip_mon.height - mon_h
        self.scroll_monster = max(min_scr_mon, min(0, self.scroll_monster))

        item_count = len(self.game_manager.bag._items_data)
        item_h = max(self.clip_item.height, item_count * 70)
        min_scr_item = self.clip_item.height - item_h
        self.scroll_item = max(min_scr_item, min(0, self.scroll_item))

    def draw(self, screen: pg.Surface):
        if not self.is_open:
            return

        # 1. 背景遮罩
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(160)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        # 2. 主面板
        screen.blit(self.surface, self.rect)

        # 3. 標題與分隔線
        title = self.font_title.render("ADVENTURE BAG", True, (0, 0, 0))
        title_x = self.rect.centerx - title.get_width() // 2
        screen.blit(title, (title_x, self.rect.top + 30))

        # 垂直分隔線
        line_x = self.rect.centerx
        pg.draw.line(screen, (100, 100, 100), (line_x, self.rect.top + 90), (line_x, self.rect.bottom - 40), 3)

        # 標籤頭
        mon_lbl = self.font_text.render("Pokemons", True, (0, 0, 0))
        screen.blit(mon_lbl, (self.clip_mon.x + 10, self.clip_mon.y - 30))
        
        item_lbl = self.font_text.render("Items", True, (0, 0, 0))
        screen.blit(item_lbl, (self.clip_item.x + 10, self.clip_item.y - 30))

        # ================================
        # 左側：怪物列表
        # ================================
        monsters = self.game_manager.bag._monsters_data
        mon_row_h = 90
        total_mon_h = max(self.clip_mon.height, len(monsters) * mon_row_h)
        surf_mon = pg.Surface((self.clip_mon.width, total_mon_h), pg.SRCALPHA)
        
        y = self.scroll_monster
        for mon in monsters:
            surf_mon.blit(self.banner, (0, y + 5))

            is_dead = mon.get('is_dead', False)

            # 圖示
            icon = Sprite(mon["sprite_path"], (64, 64))
            icon.rect.topleft = (15, y + 12)
            icon.draw(surf_mon)

            if is_dead:
                gray = pg.Surface((64, 64), pg.SRCALPHA)
                gray.fill((50, 50, 50, 150))
                surf_mon.blit(gray, (15, y + 12))
                dead_txt = self.font_small.render("DEAD", True, (255, 0, 0))
                surf_mon.blit(dead_txt, (20, y + 35))

            # 資訊區塊偏移
            info_x = 100
            
            name_txt = self.font_text.render(mon["name"], True, (0, 0, 0))
            surf_mon.blit(name_txt, (info_x, y + 10))

            lv_txt = self.font_text.render(f"Lv.{mon['level']}", True, (0, 0, 0))
            # [修改] 等級文字靠右一點
            surf_mon.blit(lv_txt, (info_x + 250, y + 10))

            # HP計算
            curr_hp = mon.get('hp', 0)
            max_hp = mon.get('max_hp', 100)
            hp_pct = curr_hp / max_hp if max_hp > 0 else 0
            
            curr_exp = mon.get('exp', 0)
            level = mon.get('level', 1)
            max_exp = mon.get('max_exp', (level + 1) * 10)
            exp_pct = min(1.0, curr_exp / max_exp) if max_exp > 0 else 0

            # --- HP Bar (隨列表變寬) ---
            bar_w = 320 # 加寬血條
            bar_h = 12
            bar_x = info_x
            bar_y = y + 45
            
            if hp_pct > 0.5: hp_col = self.COLOR_HP_HIGH
            elif hp_pct > 0.2: hp_col = self.COLOR_HP_MED
            else: hp_col = self.COLOR_HP_LOW
            if is_dead: hp_col = (100, 100, 100)

            pg.draw.rect(surf_mon, self.COLOR_BG_BAR, (bar_x, bar_y, bar_w, bar_h), border_radius=6)
            if hp_pct > 0:
                pg.draw.rect(surf_mon, hp_col, (bar_x, bar_y, int(bar_w * hp_pct), bar_h), border_radius=6)
            
            hp_str = f"{int(curr_hp)}/{int(max_hp)}"
            hp_surf = self.font_tiny.render(hp_str, True, (0, 0, 0))
            surf_mon.blit(hp_surf, (bar_x + bar_w - hp_surf.get_width(), bar_y - 15))

            # --- EXP Bar ---
            exp_y = bar_y + 18
            exp_h = 6
            pg.draw.rect(surf_mon, self.COLOR_BG_BAR, (bar_x, exp_y, bar_w, exp_h), border_radius=3)
            if exp_pct > 0:
                pg.draw.rect(surf_mon, self.COLOR_EXP, (bar_x, exp_y, int(bar_w * exp_pct), exp_h), border_radius=3)

            y += mon_row_h

        # 繪製 Monster 列表
        screen.set_clip(self.clip_mon)
        screen.blit(surf_mon, self.clip_mon.topleft)
        self._draw_scrollbar(screen, self.clip_mon, total_mon_h, self.scroll_monster)
        screen.set_clip(None)

        # ================================
        # 右側：道具列表
        # ================================
        items = self.game_manager.bag._items_data
        item_row_h = 70
        total_item_h = max(self.clip_item.height, len(items) * item_row_h)
        surf_item = pg.Surface((self.clip_item.width, total_item_h), pg.SRCALPHA)
        
        iy = self.scroll_item
        
        if not items:
            empty_txt = self.font_text.render("Empty Bag", True, (0, 0, 0))
            surf_item.blit(empty_txt, (50, 50))
        else:
            for it in items:
                # 分隔線
                line_w = self.clip_item.width - 20
                pg.draw.line(surf_item, (200, 200, 200), (10, iy + item_row_h - 2), (10 + line_w, iy + item_row_h - 2), 1)

                # 圖示
                icon = Sprite(it["sprite_path"], (50, 50))
                icon.rect.topleft = (10, iy + 10)
                icon.draw(surf_item)

                # 名稱
                name_s = self.font_text.render(it["name"], True, (0, 0, 0))
                surf_item.blit(name_s, (70, iy + 20))

                # [修改 4] 數量靠右對齊計算
                cnt_str = f"x{it['count']}"
                cnt_s = self.font_text.render(cnt_str, True, (0, 0, 0))
                
                # 計算靠右的位置：總寬度 - 文字寬度 - 右邊距(50)
                right_align_x = self.clip_item.width - cnt_s.get_width() - 50
                surf_item.blit(cnt_s, (right_align_x, iy + 20))

                iy += item_row_h

        # 繪製 Item 列表
        screen.set_clip(self.clip_item)
        screen.blit(surf_item, self.clip_item.topleft)
        self._draw_scrollbar(screen, self.clip_item, total_item_h, self.scroll_item)
        screen.set_clip(None)

        # 關閉按鈕
        self.close_button.rect.topleft = (self.close_rect.x, self.close_rect.y)
        self.close_button.draw(screen)

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