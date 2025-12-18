import pygame as pg
from src.utils import GameSettings
from src.core import GameManager
from src.interface.components.component import UIComponent
from src.core.services import input_manager
from src.sprites import Sprite


class PokemonSwitchPanel(UIComponent):
    """
    Panel for switching Pokemon during battle.
    Displays HP bar and EXP bar.
    """

    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.is_open = False
        self.selected_index = -1  
        self.callback = None 

        # UI Frame (保持 700x550)
        raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
        frame_w, frame_h = 700, 550
        self.surface = pg.transform.smoothscale(raw, (frame_w, frame_h))

        x = (GameSettings.SCREEN_WIDTH - frame_w) // 2
        y = (GameSettings.SCREEN_HEIGHT - frame_h) // 2
        self.rect = pg.Rect(x, y, frame_w, frame_h)

        # ★★★ 修改點：Banner 加寬至 600 (原 450)，填滿列表寬度 ★★★
        banner_raw = pg.image.load("assets/images/UI/raw/UI_Flat_Banner03a.png").convert_alpha()
        self.banner = pg.transform.smoothscale(banner_raw, (600, 80))

        # Fonts
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 36)
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 22)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        self.font_tiny = pg.font.Font("assets/fonts/Minecraft.ttf", 14)

        # Close Button
        self.close_button = Sprite("UI/button_x.png", (45, 45))
        self.close_rect = pg.Rect(x + frame_w - 65, y + 20, 45, 45)

        # Scroll offset
        self.scroll_offset = 0
        self.SCROLL_SPEED = 25

        # Content clipping rect
        self.clip_rect = pg.Rect(x + 40, y + 80, 620, 440)

        self.pokemon_rects = []
        
        # Colors
        self.COLOR_HP_HIGH = (46, 204, 113)
        self.COLOR_HP_MED = (241, 196, 15)
        self.COLOR_HP_LOW = (231, 76, 60)
        self.COLOR_EXP = (52, 152, 219)
        self.COLOR_BG_BAR = (50, 50, 50)
        self.COLOR_SCROLL_HANDLE = (50, 50, 50)

    def open(self, callback=None):
        self.is_open = True
        self.selected_index = -1
        self.callback = callback
        self.scroll_offset = 0

    def close(self):
        self.is_open = False

    def update(self, dt: float):
        if not self.is_open:
            return

        if self.close_rect.collidepoint(input_manager.mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
            return

        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return

        mx, my = input_manager.mouse_pos
        wheel = input_manager.mouse_wheel

        if wheel != 0 and self.clip_rect.collidepoint((mx, my)):
            self.scroll_offset += wheel * self.SCROLL_SPEED

        # Clamp scroll
        row_h = 90
        content_h = max(self.clip_rect.height, len(self.game_manager.bag._monsters_data) * row_h)
        min_scroll = self.clip_rect.height - content_h
        
        if self.scroll_offset < min_scroll: self.scroll_offset = min_scroll
        if self.scroll_offset > 0: self.scroll_offset = 0

        # Pokemon selection
        if input_manager.mouse_pressed(1):
            for idx, rect in enumerate(self.pokemon_rects):
                # rect is in world coords
                if rect.collidepoint((mx, my)):
                    monster = self.game_manager.bag._monsters_data[idx]
                    if monster.get('is_dead', False):
                        from src.utils import Logger
                        Logger.warning(f"{monster.get('name')} is dead and cannot be switched in!")
                        continue
                    
                    self.selected_index = idx
                    if self.callback:
                        self.callback(idx)
                    break

    def draw(self, screen: pg.Surface):
        if not self.is_open:
            return

        # Dark background
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(160)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        screen.blit(self.surface, self.rect)

        title = self.font_title.render("SWITCH POKEMON", True, (0, 0, 0))
        screen.blit(title, (self.rect.left + 30, self.rect.top + 25))

        monsters = self.game_manager.bag._monsters_data
        row_h = 90
        total_h = max(self.clip_rect.height, len(monsters) * row_h)
        temp_surface = pg.Surface((self.clip_rect.width, total_h), pg.SRCALPHA)
        
        y = 0 # Draw from 0 on temp surface
        self.pokemon_rects = []

        for idx, mon in enumerate(monsters):
            # Banner
            temp_surface.blit(self.banner, (0, y + 5))

            # Store hit rect (apply scroll offset)
            card_rect = pg.Rect(
                self.clip_rect.x,
                self.clip_rect.y + y + self.scroll_offset,
                self.banner.get_width(),
                self.banner.get_height()
            )
            self.pokemon_rects.append(card_rect)

            is_dead = mon.get('is_dead', False)
            
            # Icon
            icon = Sprite(mon["sprite_path"], (64, 64))
            icon.rect.topleft = (15, y + 12)
            icon.draw(temp_surface)

            if is_dead:
                gray = pg.Surface((64, 64), pg.SRCALPHA)
                gray.fill((50, 50, 50, 150))
                temp_surface.blit(gray, (15, y + 12))
                dead_txt = self.font_small.render("DEAD", True, (255, 0, 0))
                temp_surface.blit(dead_txt, (20, y + 35))

            info_x = 100
            
            # Name
            name_color = (0, 0, 0)
            name = self.font_text.render(mon["name"], True, name_color)
            temp_surface.blit(name, (info_x, y + 10))

            lv = self.font_text.render(f"Lv.{mon['level']}", True, (0, 0, 0))
            temp_surface.blit(lv, (info_x + 200, y + 10))

            # Stats
            curr_hp = mon.get('hp', 0)
            max_hp = mon.get('max_hp', 100)
            hp_pct = curr_hp / max_hp if max_hp > 0 else 0
            
            level = mon.get('level', 1)
            max_exp = mon.get('max_exp', (level + 1) * 10)
            curr_exp = mon.get('exp', 0)
            exp_pct = min(1.0, curr_exp / max_exp) if max_exp > 0 else 0

            # HP Bar
            bar_w = 280
            bar_h = 14
            bar_x = info_x
            bar_y = y + 45
            
            if hp_pct > 0.5: hp_col = self.COLOR_HP_HIGH
            elif hp_pct > 0.2: hp_col = self.COLOR_HP_MED
            else: hp_col = self.COLOR_HP_LOW
            if is_dead: hp_col = (100, 100, 100)

            pg.draw.rect(temp_surface, self.COLOR_BG_BAR, (bar_x, bar_y, bar_w, bar_h), border_radius=7)
            if hp_pct > 0:
                pg.draw.rect(temp_surface, hp_col, (bar_x, bar_y, int(bar_w * hp_pct), bar_h), border_radius=7)
            
            hp_str = f"{int(curr_hp)}/{int(max_hp)}"
            hp_surf = self.font_tiny.render(hp_str, True, (0,0,0))
            temp_surface.blit(hp_surf, (bar_x + bar_w + 10, bar_y - 2))

            # EXP Bar
            exp_y = bar_y + 18
            exp_h = 6
            pg.draw.rect(temp_surface, self.COLOR_BG_BAR, (bar_x, exp_y, bar_w, exp_h), border_radius=3)
            if exp_pct > 0:
                pg.draw.rect(temp_surface, self.COLOR_EXP, (bar_x, exp_y, int(bar_w * exp_pct), exp_h), border_radius=3)

            y += row_h

        screen.set_clip(self.clip_rect)
        screen.blit(temp_surface, (self.clip_rect.x, self.clip_rect.y + self.scroll_offset))
        
        self._draw_scrollbar(screen, self.clip_rect, total_h, self.scroll_offset)
        
        screen.set_clip(None)

        # Close button
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