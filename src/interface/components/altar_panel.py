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
# UI 專用的動畫精靈 (Altar 版)
# ==============================================================
class UIAnimatedSprite(pg.sprite.Sprite):
    def __init__(self, sprite_path: str, center_pos: tuple[int, int], scale: int = 5):
        super().__init__()
        self.sprite_path = sprite_path
        self.monster_id = self._get_monster_id(sprite_path)
        self.scale = scale
        self.center_pos = center_pos
        
        # 載入動畫 Frames
        self.frames = self._load_idle_frames(self.monster_id)
        if not self.frames:
            s = pg.Surface((64, 64))
            s.fill((100, 100, 100))
            self.frames = [s]
            
        self.frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.25 
        
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
        except Exception:
            pass
        return frames

    def update(self, dt: float):
        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_rect(center=self.center_pos)

    def change_sprite(self, new_id: int):
        self.monster_id = new_id
        self.frames = self._load_idle_frames(new_id)
        if not self.frames:
            s = pg.Surface((64, 64))
            s.fill((100, 100, 100))
            self.frames = [s]
        self.frame_index = 0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=self.center_pos)

    def draw(self, screen: pg.Surface, blink_alpha: int = 0):
        screen.blit(self.image, self.rect)
        if blink_alpha > 0:
            mask = pg.mask.from_surface(self.image)
            white_surf = mask.to_surface(setcolor=(255, 255, 255, blink_alpha), unsetcolor=(0, 0, 0, 0))
            for ox in [-2, 0, 2]:
                for oy in [-2, 0, 2]:
                    screen.blit(white_surf, (self.rect.x + ox, self.rect.y + oy))


# ==============================================================
# Altar Panel (Evolution UI)
# ==============================================================
class AltarPanel(UIComponent):
    """祭壇面板：用於進化滿足條件的寶可夢。"""

    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.is_open = False

        self.EVO_GROUP_29 = {1: 2, 7: 8, 12: 13}
        self.EVO_GROUP_49 = {2: 3, 8: 9, 13: 14}

        try:
            raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame01a.png").convert_alpha()
        except:
            raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
            
        # ★★★ 修改點 1: 尺寸加大到 1000 x 650 ★★★
        frame_w, frame_h = 1000, 650
        self.surface = pg.transform.smoothscale(raw, (frame_w, frame_h))

        x = (GameSettings.SCREEN_WIDTH - frame_w) // 2
        y = (GameSettings.SCREEN_HEIGHT - frame_h) // 2
        self.rect = pg.Rect(x, y, frame_w, frame_h)

        # 列表項目的背景橫幅 (加寬到 360，容納 READY 字樣)
        banner_raw = pg.image.load("assets/images/UI/raw/UI_Flat_Banner03a.png").convert_alpha()
        self.banner = pg.transform.smoothscale(banner_raw, (360, 70))

        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 36)
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 22)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        self.font_btn = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        self.font_msg = pg.font.Font("assets/fonts/Minecraft.ttf", 48)

        self.close_button = Sprite("UI/button_x.png", (45, 45))
        self.close_rect = pg.Rect(x + frame_w - 65, y + 25, 45, 45)
        
        self.scroll_offset = 0
        self.SCROLL_SPEED = 25
        
        # 列表顯示區域加大
        self.clip_rect = pg.Rect(x + 50, y + 100, 380, 500)
        self.click_rects = []
        
        self.selected_mon_data = None 
        self.selected_mon_sprite = None 
        
        # ★★★ 修改點 2: 按鈕位置調整 ★★★
        self.btn_x = self.rect.right - 320
        self.btn_y = self.rect.bottom - 100
        self.btn_w = 160
        self.btn_h = 60

        self.evolve_button = Button(
            img_path="UI/raw/UI_Flat_Button02a_2.png",
            img_hovered_path="UI/raw/UI_Flat_Button02a_1.png",
            x=self.btn_x, 
            y=self.btn_y, 
            width=self.btn_w, 
            height=self.btn_h,
            label="EVOLVE",
            font=self.font_btn,
            on_click=self._on_evolve_click
        )
        
        self.is_evolving = False
        self.evolve_timer = 0.0
        self.EVOLVE_DURATION = 3.0 
        self.blink_alpha = 0
        self.show_success_msg = False
        self.success_timer = 0.0

    def open(self):
        self.is_open = True
        self.scroll_offset = 0
        self.selected_mon_data = None
        self.selected_mon_sprite = None
        self.is_evolving = False
        self.show_success_msg = False

    def close(self):
        self.is_open = False
        self.is_evolving = False

    def _get_monster_id(self, path: str) -> int:
        try:
            match = re.search(r'(\d+)', path)
            if match: return int(match.group(1))
        except: pass
        return 0

    def _get_evolution_candidates(self):
        candidates = []
        if not hasattr(self.game_manager.bag, '_monsters_data'):
            return []

        for mon in self.game_manager.bag._monsters_data:
            if mon.get('is_dead', False): continue
            
            mid = self._get_monster_id(mon['sprite_path'])
            lvl = mon.get('level', 1)
            exp = mon.get('exp', 0)
            max_exp = mon.get('max_exp', (lvl+1)*10)
            
            if exp < max_exp: continue
            
            can_evolve = False
            if lvl == 29 and mid in self.EVO_GROUP_29:
                can_evolve = True
            elif lvl == 49 and mid in self.EVO_GROUP_49:
                can_evolve = True
                
            if can_evolve:
                candidates.append(mon)
        return candidates

    def update(self, dt: float):
        if not self.is_open:
            return

        if self.is_evolving:
            self.evolve_timer -= dt
            
            if self.evolve_timer > 0:
                import math
                self.blink_alpha = int(abs(math.sin(self.evolve_timer * 10)) * 255)
            else:
                self._perform_evolution_update()
                self.is_evolving = False
                self.blink_alpha = 0
                self.show_success_msg = True
                self.success_timer = 2.0 
            
            if self.selected_mon_sprite:
                self.selected_mon_sprite.update(dt)
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
        if wheel != 0 and self.clip_rect.collidepoint((mx, my)):
            self.scroll_offset += wheel * self.SCROLL_SPEED

        candidates = self._get_evolution_candidates()
        max_scroll = -(len(candidates) * 80 - self.clip_rect.height)
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
            self.evolve_button.update(dt)

    def _select_monster(self, monster):
        self.selected_mon_data = monster
        # ★★★ 修改點 3: 精靈位置下移至 top + 320 ★★★
        center_x = self.rect.right - 280 
        center_y = self.rect.top + 320
        self.selected_mon_sprite = UIAnimatedSprite(monster["sprite_path"], (center_x, center_y), scale=5)
        Logger.info(f"Selected for evolution: {monster['name']}")

    def _on_evolve_click(self):
        if not self.selected_mon_data: return
        Logger.info("Starting evolution sequence...")
        self.is_evolving = True
        self.evolve_timer = self.EVOLVE_DURATION

    def _perform_evolution_update(self):
        mon = self.selected_mon_data
        if not mon: return

        old_id = self._get_monster_id(mon['sprite_path'])
        lvl = mon['level']
        
        new_id = old_id
        if lvl == 29 and old_id in self.EVO_GROUP_29:
            new_id = self.EVO_GROUP_29[old_id]
        elif lvl == 49 and old_id in self.EVO_GROUP_49:
            new_id = self.EVO_GROUP_49[old_id]
            
        if new_id != old_id:
            mon['level'] += 1
            new_lvl = mon['level']
            mon['sprite_path'] = f"menu_sprites/menusprite{new_id}.png"
            mon['max_hp'] = new_lvl * 100
            mon['hp'] = mon['max_hp'] 
            mon['attack'] = new_lvl * 10
            mon['exp'] = 0
            mon['max_exp'] = (new_lvl + 1) * 10
            
            if self.selected_mon_sprite:
                self.selected_mon_sprite.change_sprite(new_id)
                
            Logger.info(f"Evolution Complete! ID {old_id} -> {new_id} (Lv.{new_lvl})")

    def draw(self, screen: pg.Surface):
        if not self.is_open:
            return

        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(140)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        screen.blit(self.surface, self.rect)

        title = self.font_title.render("ALTAR OF EVOLUTION", True, (0, 0, 0))
        screen.blit(title, (self.rect.left + 50, self.rect.top + 35))

        candidates = self._get_evolution_candidates()
        
        if not candidates and not self.is_evolving and not self.show_success_msg:
            no_data = self.font_text.render("No pokemon ready to evolve.", True, (100, 100, 100))
            screen.blit(no_data, (self.clip_rect.centerx - no_data.get_width()//2, self.clip_rect.centery))
        elif not self.show_success_msg:
            content_h = max(self.clip_rect.height, len(candidates) * 80)
            temp_surface = pg.Surface((self.clip_rect.width, content_h), pg.SRCALPHA)
            
            y = 0 
            self.click_rects = []

            for mon in candidates:
                item_rect = pg.Rect(0, y, 360, 70)
                self.click_rects.append((item_rect, mon))
                
                temp_surface.blit(self.banner, (0, y))
                
                icon = Sprite(mon["sprite_path"], (55, 55))
                icon.rect.topleft = (12, y + 8)
                icon.draw(temp_surface)
                
                name = self.font_text.render(mon["name"], True, (80, 80, 80))
                temp_surface.blit(name, (80, y + 6))
                
                lv = self.font_text.render(f"Lv.{mon['level']}", True, (80, 80, 80))
                temp_surface.blit(lv, (230, y + 6))
                
                bar_x = 80
                curr_hp = mon.get('hp', 0)
                max_hp = mon.get('max_hp', 100)
                fill_hp = int((curr_hp / max_hp) * 180) if max_hp > 0 else 0
                pg.draw.rect(temp_surface, (200, 200, 200), (bar_x, y + 32, 180, 8))
                pg.draw.rect(temp_surface, (0, 200, 0), (bar_x, y + 32, fill_hp, 8))
                
                pg.draw.rect(temp_surface, (200, 200, 200), (bar_x, y + 44, 180, 6))
                pg.draw.rect(temp_surface, (255, 140, 0), (bar_x, y + 44, 180, 6))
                
                # READY Text (靠右對齊)
                ready_txt = self.font_small.render("READY", True, (255, 140, 0))
                temp_surface.blit(ready_txt, (285, y + 40))

                y += 80

            screen.set_clip(self.clip_rect)
            screen.blit(temp_surface, (self.clip_rect.x, self.clip_rect.y - self.scroll_offset))
            screen.set_clip(None)

        if self.selected_mon_data:
            # 調整預覽裁剪區域，以適應精靈下移
            preview_rect = pg.Rect(self.rect.centerx, self.rect.top + 50, self.rect.width//2 - 20, self.rect.height - 50)
            screen.set_clip(preview_rect)
            
            if self.selected_mon_sprite:
                self.selected_mon_sprite.draw(screen, blink_alpha=self.blink_alpha)
            
            screen.set_clip(None)
            
            if not self.is_evolving and not self.show_success_msg:
                self.evolve_button.draw(screen)
                
                info_txt = self.font_small.render("Evolution is ready.", True, (0, 0, 0))
                screen.blit(info_txt, (self.btn_x + 15, self.btn_y - 30))

        if self.show_success_msg:
            msg = self.font_msg.render("Your Pokemon Has Evolved!", True, (0, 200, 0))
            shadow = self.font_msg.render("Your Pokemon Has Evolved!", True, (0, 0, 0))
            
            cx = GameSettings.SCREEN_WIDTH // 2 - msg.get_width() // 2
            cy = GameSettings.SCREEN_HEIGHT // 2 - msg.get_height() // 2
            
            screen.blit(shadow, (cx+3, cy+3))
            screen.blit(msg, (cx, cy))

        self.close_button.rect.topleft = (self.close_rect.x, self.close_rect.y)
        self.close_button.draw(screen)