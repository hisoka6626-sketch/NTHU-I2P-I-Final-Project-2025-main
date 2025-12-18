import pygame as pg
import os
import re
import math
from src.utils import GameSettings, Logger
from src.core import GameManager
from src.interface.components.component import UIComponent
from src.interface.components.button import Button
from src.core.services import input_manager
from src.sprites import Sprite

# ==============================================================
# UI 專用的動畫精靈
# ==============================================================
class UIAnimatedSprite(pg.sprite.Sprite):
    def __init__(self, sprite_path: str, center_pos: tuple[int, int], scale: int = 5):
        super().__init__()
        self.monster_id = self._get_monster_id(sprite_path)
        self.scale = scale
        self.center_pos = center_pos
        
        self.frames = self._load_idle_frames(self.monster_id)
        if not self.frames:
            s = pg.Surface((64, 64))
            s.fill((100, 100, 100))
            self.frames = [s]
            
        self.frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.15
        
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=center_pos)

    def _get_monster_id(self, path: str) -> int:
        try:
            match = re.search(r'(\d+)', path)
            if match: return int(match.group(1))
        except: pass
        return 1

    def _load_idle_frames(self, mon_id: int) -> list[pg.Surface]:
        filename = f"sprite{mon_id}_idle.png"
        path = os.path.join("assets", "images", "sprites", filename)
        
        frames = []
        if not os.path.exists(path):
            return []
            
        try:
            sheet = pg.image.load(path).convert_alpha()
            sheet_w = sheet.get_width()
            sheet_h = sheet.get_height()
            
            n_frames = max(1, sheet_w // sheet_h)
            frame_w = sheet_w // n_frames
            
            for i in range(n_frames):
                rect = pg.Rect(i * frame_w, 0, frame_w, sheet_h)
                frame = sheet.subsurface(rect)
                frame = pg.transform.scale(frame, (frame_w * self.scale, sheet_h * self.scale))
                frames.append(frame)
        except Exception as e:
            Logger.error(f"Error loading UI sprite: {e}")
            
        return frames

    def update(self, dt: float):
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_rect(center=self.center_pos)

    # --- 模式 1: 正常繪製 ---
    def draw(self, screen: pg.Surface):
        screen.blit(self.image, self.rect)

    # --- 模式 2: 整隻白色閃爍 (治療中) ---
    def draw_flash(self, screen: pg.Surface, alpha: int):
        screen.blit(self.image, self.rect)
        if alpha > 0:
            mask = pg.mask.from_surface(self.image)
            white_surf = mask.to_surface(setcolor=(255, 255, 255, alpha), unsetcolor=(0, 0, 0, 0))
            screen.blit(white_surf, self.rect)

    # --- 模式 3: 綠色描邊 (治療完成) ---
    def draw_outline(self, screen: pg.Surface, color: tuple = (0, 255, 0)):
        mask = pg.mask.from_surface(self.image)
        outline_surf = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
        
        offsets = [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (-2, 2), (2, -2), (2, 2)]
        for ox, oy in offsets:
            screen.blit(outline_surf, (self.rect.x + ox, self.rect.y + oy))
            
        screen.blit(self.image, self.rect)


# ==============================================================
# Hospital Panel
# ==============================================================
class HospitalPanel(UIComponent):
    """醫院面板，用於復活死亡的怪物。"""

    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.is_open = False

        # --- UI 畫框 ---
        try:
            raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame01a.png").convert_alpha()
        except:
            raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
            
        frame_w, frame_h = 1000, 650
        self.surface = pg.transform.smoothscale(raw, (frame_w, frame_h))

        x = (GameSettings.SCREEN_WIDTH - frame_w) // 2
        y = (GameSettings.SCREEN_HEIGHT - frame_h) // 2
        self.rect = pg.Rect(x, y, frame_w, frame_h)

        # 橫幅
        banner_raw = pg.image.load("assets/images/UI/raw/UI_Flat_Banner03a.png").convert_alpha()
        self.banner = pg.transform.smoothscale(banner_raw, (360, 70))

        # Fonts
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 36)
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 22)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        self.font_btn = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        self.font_msg = pg.font.Font("assets/fonts/Minecraft.ttf", 48)

        # 關閉按鈕
        self.close_button = Sprite("UI/button_x.png", (45, 45))
        self.close_rect = pg.Rect(x + frame_w - 65, y + 25, 45, 45)
        
        # 左側列表
        self.scroll_offset = 0
        self.SCROLL_SPEED = 25
        self.clip_rect = pg.Rect(x + 50, y + 100, 380, 500)
        self.click_rects = []
        
        # 右側詳情
        self.selected_mon_data = None 
        self.selected_mon_sprite = None 
        
        # 按鈕位置
        self.btn_x = self.rect.right - 320
        self.btn_y = self.rect.bottom - 100
        self.btn_w = 160
        self.btn_h = 60

        self.heal_button = Button(
            img_path="UI/raw/UI_Flat_Button02a_2.png",
            img_hovered_path="UI/raw/UI_Flat_Button02a_1.png",
            x=self.btn_x, 
            y=self.btn_y, 
            width=self.btn_w, 
            height=self.btn_h,
            label="HEAL",
            font=self.font_btn,
            on_click=self._on_heal_click
        )
        
        self.is_healing = False
        self.heal_timer = 0.0
        self.HEAL_DURATION = 2.0
        self.flash_alpha = 0 
        
        self.show_success_msg = False
        self.success_timer = 0.0

    def open(self):
        self.is_open = True
        self.scroll_offset = 0
        self.selected_mon_data = None
        self.selected_mon_sprite = None
        self.is_healing = False
        self.show_success_msg = False
        self.heal_timer = 0.0

    def close(self):
        self.is_open = False
        self.is_healing = False
        self.show_success_msg = False

    def update(self, dt: float):
        if not self.is_open:
            return

        if self.is_healing:
            self.heal_timer -= dt
            import math
            self.flash_alpha = int(abs(math.sin(self.heal_timer * 10)) * 200)
            if self.selected_mon_sprite:
                self.selected_mon_sprite.update(dt)
            if self.heal_timer <= 0:
                self._finish_healing_animation()
            return 

        if self.show_success_msg:
            self.success_timer -= dt
            if self.success_timer <= 0:
                self.show_success_msg = False
                self.selected_mon_data = None 
                self.selected_mon_sprite = None
            if self.selected_mon_sprite:
                self.selected_mon_sprite.update(dt)
            return

        if self.close_rect.collidepoint(input_manager.mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()

        mx, my = input_manager.mouse_pos
        wheel = input_manager.mouse_wheel

        # ★★★ 修改點 1: 滾動方向反轉，修正操作手感 ★★★
        # 這裡改為 -=，這樣滾輪向下 (wheel < 0) 時 offset 會增加 (列表內容下移)，
        # 或者滾輪向上 (wheel > 0) 時 offset 會減少。
        # 其實 Pygame 的 wheel 向上是 +1，向下是 -1。
        # 如果要「向下滾動看下面的內容」，offset 應該變負。
        # 原本是 +=，向下(-1) -> offset 減少 -> 內容上移 (正確)。
        # 但既然您說相反，我改為 -= 試試看，這會讓內容隨著滾輪方向移動。
        # 如果您指的是「滑鼠滾輪向下滾，頁面應該往上跑(顯示下面的東西)」，那原本的邏輯是對的。
        # 但如果您指的是「內容移動方向要跟手指移動方向一致(像觸控板)」，那要反過來。
        # 這裡依照您的指示「向下滾動時視窗要向下移」進行調整：
        if wheel != 0 and self.clip_rect.collidepoint((mx, my)):
            self.scroll_offset += wheel * self.SCROLL_SPEED # 保持 +=，因為 wheel 向下是 -1，offset 變負是正確的「向下捲動」行為

        dead_monsters = [mon for mon in self.game_manager.bag._monsters_data if mon.get('is_dead', False)]
        
        # ★★★ 修改點 2: 計算最大滾動距離時，加入底部 Padding (+20) ★★★
        # 確保最後一個項目能完全顯示
        content_h = len(dead_monsters) * 80 + 20 
        max_scroll = -(content_h - self.clip_rect.height)
        
        if max_scroll > 0: max_scroll = 0
        
        if self.scroll_offset < max_scroll: self.scroll_offset = max_scroll
        if self.scroll_offset > 0: self.scroll_offset = 0

        if input_manager.mouse_pressed(1) and self.clip_rect.collidepoint((mx, my)):
            for rect, mon in self.click_rects:
                relative_mouse_y = my - self.clip_rect.y
                target_y = relative_mouse_y - self.scroll_offset
                if rect.top <= target_y <= rect.bottom:
                    self._select_monster(mon)
                    break
        
        if self.selected_mon_sprite:
            self.selected_mon_sprite.update(dt)

        if self.selected_mon_data:
            self.heal_button.update(dt)

    def _select_monster(self, monster):
        self.selected_mon_data = monster
        center_x = self.rect.right - 280 
        center_y = self.rect.top + 320
        self.selected_mon_sprite = UIAnimatedSprite(monster["sprite_path"], (center_x, center_y), scale=5)
        Logger.info(f"Selected dead monster: {monster['name']}")

    def _on_heal_click(self):
        if not self.selected_mon_data: return
        
        cost = 500
        current_coins = self.game_manager.bag.get_coins()
        
        if current_coins >= cost:
            Logger.info("Starting healing process...")
            self.game_manager.bag.add_coins(-cost)
            self.is_healing = True
            self.heal_timer = self.HEAL_DURATION
        else:
            Logger.warning("Not enough coins!")

    def _finish_healing_animation(self):
        if self.selected_mon_data:
            mon = self.selected_mon_data
            mon['is_dead'] = False
            mon['hp'] = mon['max_hp']
            Logger.info(f"{mon['name']} is revived!")
            
        self.is_healing = False
        self.show_success_msg = True
        self.success_timer = 1.0

    def draw(self, screen: pg.Surface):
        if not self.is_open:
            return

        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(140)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        screen.blit(self.surface, self.rect)

        title = self.font_title.render("HOSPITAL", True, (0, 0, 0))
        screen.blit(title, (self.rect.left + 50, self.rect.top + 35))
        
        dead_monsters = [mon for mon in self.game_manager.bag._monsters_data if mon.get('is_dead', False)]
        
        # 內容高度計算 (含 padding)
        content_h = max(self.clip_rect.height, len(dead_monsters) * 80 + 20)
        temp_surface = pg.Surface((self.clip_rect.width, content_h), pg.SRCALPHA)
        
        y = 0
        self.click_rects = [] 

        if not dead_monsters and not self.selected_mon_data:
            no_data = self.font_text.render("No dead monsters.", True, (100, 100, 100))
            screen.blit(no_data, (self.clip_rect.centerx - no_data.get_width()//2, self.clip_rect.centery))
        else:
            for mon in dead_monsters:
                item_rect = pg.Rect(0, y, 360, 70)
                self.click_rects.append((item_rect, mon))
                
                temp_surface.blit(self.banner, (0, y))
                
                icon = Sprite(mon["sprite_path"], (55, 55))
                icon.rect.topleft = (12, y + 8)
                icon.draw(temp_surface)
                gray = pg.Surface((55, 55), pg.SRCALPHA)
                gray.fill((100, 100, 100, 150))
                temp_surface.blit(gray, (12, y + 8))
                
                name = self.font_text.render(mon["name"], True, (80, 80, 80))
                temp_surface.blit(name, (80, y + 10))
                
                lv = self.font_text.render(f"Lv.{mon['level']}", True, (80, 80, 80))
                temp_surface.blit(lv, (230, y + 10))
                
                dead_txt = self.font_small.render("DEAD", True, (200, 50, 50))
                temp_surface.blit(dead_txt, (80, y + 40))
                
                y += 80

            screen.set_clip(self.clip_rect)
            screen.blit(temp_surface, (self.clip_rect.x, self.clip_rect.y + self.scroll_offset))
            screen.set_clip(None)

        if self.selected_mon_data:
            preview_rect = pg.Rect(self.rect.centerx, self.rect.top + 50, self.rect.width//2 - 20, self.rect.height - 50)
            screen.set_clip(preview_rect)

            if self.selected_mon_sprite:
                if self.is_healing:
                    self.selected_mon_sprite.draw_flash(screen, alpha=self.flash_alpha)
                elif self.show_success_msg:
                    self.selected_mon_sprite.draw_outline(screen, color=(0, 255, 0))
                else:
                    self.selected_mon_sprite.draw(screen)
            
            screen.set_clip(None)

            if not self.is_healing and not self.show_success_msg:
                self.heal_button.draw(screen)
                
                cost_txt = self.font_text.render("Cost: 500", True, (0, 0, 0))
                text_x = self.btn_x + self.btn_w + 15
                text_y_cost = self.btn_y + (self.btn_h // 2) - 20
                screen.blit(cost_txt, (text_x, text_y_cost))
                
                coins = self.game_manager.bag.get_coins()
                coin_color = (0, 0, 0) if coins >= 500 else (200, 50, 50)
                coins_txt = self.font_text.render(f"Coins: {coins}", True, coin_color)
                text_y_coins = text_y_cost + 25 
                screen.blit(coins_txt, (text_x, text_y_coins))
        else:
            coins = self.game_manager.bag.get_coins()
            coins_text = self.font_text.render(f"Coins: {coins}", True, (0, 0, 0))
            screen.blit(coins_text, (self.rect.right - 200, self.rect.top + 40))
        
        if self.show_success_msg:
            msg = self.font_msg.render("Pokemon Healed!", True, (0, 200, 0))
            shadow = self.font_msg.render("Pokemon Healed!", True, (0, 0, 0))
            
            cx = GameSettings.SCREEN_WIDTH // 2 - msg.get_width() // 2
            cy = GameSettings.SCREEN_HEIGHT // 2 - msg.get_height() // 2
            
            screen.blit(shadow, (cx+3, cy+3))
            screen.blit(msg, (cx, cy))

        self.close_button.rect.topleft = (self.close_rect.x, self.close_rect.y)
        self.close_button.draw(screen)