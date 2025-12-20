import pygame as pg
from src.utils import GameSettings
from src.core import GameManager
from src.interface.components.component import UIComponent
from src.interface.components.button import Button
from src.core.services import input_manager
from src.sprites import Sprite
from typing import List, Tuple


class NavigationPanel(UIComponent):
    """導航面板，顯示目的地清單並提供自動導航功能。"""

    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.is_open = False
        self.is_navigating = False
        self.navigation_path: List[Tuple[int, int]] = []
        self.current_path_index = 0
        self.navigation_text = "AUTO NAVIGATING"
        self.dot_animation_timer = 0.0
        self.dot_animation_speed = 0.5

        # ---------------------------------------------------
        # UI 畫框 (600x500)
        # ---------------------------------------------------
        raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
        frame_w, frame_h = 600, 500 
        self.surface = pg.transform.smoothscale(raw, (frame_w, frame_h))

        x = (GameSettings.SCREEN_WIDTH - frame_w) // 2
        y = (GameSettings.SCREEN_HEIGHT - frame_h) // 2
        self.rect = pg.Rect(x, y, frame_w, frame_h)

        # Fonts
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 32)
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 22)
        self.font_nav = pg.font.Font("assets/fonts/Minecraft.ttf", 20)

        # 關閉按鈕
        self.close_button = Sprite("UI/button_x.png", (35, 35))
        self.close_rect = pg.Rect(x + frame_w - 50, y + 20, 35, 35)

        # 滾動偏移
        self.scroll_offset = 0
        self.scroll_speed = 25

        # 內容裁切區域
        self.clip_rect = pg.Rect(x + 40, y + 80, 520, 390)

        # ---------------------------------------------------
        # 目的地清單
        # ---------------------------------------------------
        self.destinations = [
            # 原有地點
            {"name": "SHOP", "position": (17, 29), "map": "map.tmx"},
            {"name": "GYM", "position": (24, 24), "map": "map.tmx"},
            {"name": "START", "position": (16, 29), "map": "map.tmx"},
            {"name": "EDEN", "position": (25, 25), "map": "map.tmx"},
            
            # New Map 地點
            {"name": "HOSPITAL", "position": (43, 37), "map": "new map.tmx"},
            {"name": "ALTAR", "position": (25, 45), "map": "new map.tmx"},
            
            # [新增] 賭場與系統
            {"name": "CASINO",   "position": (47, 28), "map": "new map.tmx"}, # Thermal 區 (拉霸)
            {"name": "ROULETTE", "position": (3, 27), "map": "new map.tmx"}, # Aqua 區 (轉盤)
            {"name": "STORY", "position": (25, 7), "map": "new map.tmx"}, # Aerial 區 
        ]

        # 預載 Banner 圖片
        self.banner_surface = pg.image.load("assets/images/UI/raw/UI_Flat_Banner02a.png").convert_alpha()
        self.banner_surface = pg.transform.smoothscale(self.banner_surface, (420, 50))

        # 目的地按鈕
        self.destination_buttons = []
        self._init_destination_buttons()

    def _init_destination_buttons(self):
        """初始化目的地按鈕。"""
        self.destination_buttons = []
        row_height = 65 
        
        for i, dest in enumerate(self.destinations):
            y_pos = self.rect.top + 90 + i * row_height
            btn_x = self.rect.left + 40 + 420 + 20 

            btn = Button(
                img_path="UI/button_play.png",
                img_hovered_path="UI/button_play_hover.png",
                x=btn_x,
                y=y_pos, 
                width=64,
                height=40,
                on_click=lambda d=dest: self._navigate_to_destination(d)
            )
            self.destination_buttons.append(btn)

    def _navigate_to_destination(self, destination: dict):
        """開始導航到指定目的地 (含跨地圖與特殊地點邏輯)。"""
        if not self.game_manager.player:
            return

        current_map_name = self.game_manager.current_map.path_name
        target_map_name = destination["map"]
        target_grid_pos = destination["position"]
        dest_name = destination["name"]

        print(f"--- [NAV] 導航開始: 前往 {dest_name} ---")
        
        # ==========================================================
        # 情況 A: 跨地圖導航 (Cross-Map)
        # ==========================================================
        if current_map_name != target_map_name:
            print(f"偵測到跨地圖移動...")
            
            teleport_grid_x = 0
            teleport_grid_y = 0
            
            if target_map_name == "new map.tmx":
                print(f"跨地圖前往 new map.tmx，強制設定傳送點為 (26, 20)")
                teleport_grid_x = 26
                teleport_grid_y = 20
                
            else:
                # 這是從 new map 回到主地圖的情況 (map.tmx)
                start_node = next((d for d in self.destinations if d["name"] == "START"), None)
                if start_node:
                    teleport_grid_x = start_node["position"][0]
                    teleport_grid_y = start_node["position"][1]
                else:
                    teleport_grid_x = 16
                    teleport_grid_y = 29
                    print("警告: 找不到 START 節點，使用預設座標。")

            # 執行傳送設置
            pixel_x = teleport_grid_x * GameSettings.TILE_SIZE
            pixel_y = teleport_grid_y * GameSettings.TILE_SIZE
            
            self.game_manager.target_map_name = target_map_name
            self.game_manager.target_position = (pixel_x, pixel_y)
            self.game_manager.next_map = target_map_name
            
            # 設定 "傳送後要繼續導航的最終目標"
            self.game_manager.pending_navigation_destination = target_grid_pos 
            self.game_manager.should_change_scene = True
            
            self.close()
            return

        # ==========================================================
        # 情況 B: 同地圖導航 (Same-Map)
        # ==========================================================
        print("同地圖導航模式")
        start_grid_pos = (
            int(self.game_manager.player.position.x // GameSettings.TILE_SIZE),
            int(self.game_manager.player.position.y // GameSettings.TILE_SIZE)
        )
        end_grid_pos = target_grid_pos

        path = self._find_path(start_grid_pos, end_grid_pos, self.game_manager.current_map, self.game_manager)
        if path and len(path) > 1:
            self.navigation_path = path
            self.current_path_index = 0
            self.is_navigating = True
            self.game_manager.navigation_active = True
            self.close()
        else:
            print("無法找到路徑或已在目的地附近。")

    def _find_path(self, start: Tuple[int, int], end: Tuple[int, int], map_obj, game_manager) -> List[Tuple[int, int]]:
        """使用 BFS 尋找最短路徑，避免碰撞區塊。"""
        if not map_obj or not hasattr(map_obj, 'tmxdata'):
            return []

        width = map_obj.tmxdata.width
        height = map_obj.tmxdata.height

        if (start[0] < 0 or start[0] >= width or start[1] < 0 or start[1] >= height or
            end[0] < 0 or end[0] >= width or end[1] < 0 or end[1] >= height):
            return []

        # 創建碰撞地圖
        collision_map = [[False for _ in range(height)] for _ in range(width)]

        # 標記地圖靜態碰撞
        if hasattr(map_obj, '_collision_map'):
            for rect in map_obj._collision_map:
                grid_x = int(rect.x // GameSettings.TILE_SIZE)
                grid_y = int(rect.y // GameSettings.TILE_SIZE)
                grid_w = int(rect.width // GameSettings.TILE_SIZE)
                grid_h = int(rect.height // GameSettings.TILE_SIZE)
                
                for x in range(grid_x, min(grid_x + grid_w, width)):
                    for y in range(grid_y, min(grid_y + grid_h, height)):
                        collision_map[x][y] = True

        # 標記敵方訓練家動態碰撞
        if game_manager:
            for enemy_trainer in game_manager.current_enemy_trainers:
                enemy_x = int(enemy_trainer.position.x // GameSettings.TILE_SIZE)
                enemy_y = int(enemy_trainer.position.y // GameSettings.TILE_SIZE)
                if 0 <= enemy_x < width and 0 <= enemy_y < height:
                    collision_map[enemy_x][enemy_y] = True

        # BFS
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        queue = [(start, [start])]
        visited = set([start])

        while queue:
            (current, path) = queue.pop(0)

            if current == end:
                return path

            for dx, dy in directions:
                nx, ny = current[0] + dx, current[1] + dy

                if (0 <= nx < width and 0 <= ny < height and
                    not collision_map[nx][ny] and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))

        return []

    def update(self, dt: float):
        if not self.is_open and not self.is_navigating:
            return

        if self.is_open:
            # 關閉按鈕
            if self.close_rect.collidepoint(input_manager.mouse_pos) and input_manager.mouse_pressed(1):
                self.close()

            # ESC 關閉
            if input_manager.key_pressed(pg.K_ESCAPE):
                self.close()

            # 更新目的地按鈕位置 (與滾動連動)
            row_height = 65
            for i, btn in enumerate(self.destination_buttons):
                base_y = self.rect.top + 90 + i * row_height
                btn.hitbox.y = base_y - self.scroll_offset
                btn.update(dt)

            # 滾動處理
            if self.clip_rect.collidepoint(input_manager.mouse_pos):
                wheel = input_manager.mouse_wheel
                if wheel != 0:
                    self.scroll_offset += wheel * self.scroll_speed
                    # 限制滾動範圍
                    total_content_height = len(self.destinations) * row_height
                    max_scroll = max(0, total_content_height - self.clip_rect.height + 20)
                    self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        elif self.is_navigating:
            self._update_navigation(dt)

    def _update_navigation(self, dt: float):
        """更新自動導航邏輯 (平滑移動 + 轉向 + 動畫)。"""
        if not self.game_manager.player or not self.navigation_path:
            self.is_navigating = False
            self.game_manager.navigation_active = False
            return

        # 玩家手動介入則取消導航 (除非在絕對劇情鎖定模式，但這通常由 GameScene 控制 update)
        keys = [pg.K_w, pg.K_a, pg.K_s, pg.K_d]
        for key in keys:
            if input_manager.key_pressed(key):
                self.is_navigating = False
                self.game_manager.navigation_active = False
                return

        self.dot_animation_timer += dt
        if self.dot_animation_timer >= self.dot_animation_speed:
            self.dot_animation_timer = 0.0

        while self.current_path_index < len(self.navigation_path):
            target_tile = self.navigation_path[self.current_path_index]
            target_x = target_tile[0] * GameSettings.TILE_SIZE
            target_y = target_tile[1] * GameSettings.TILE_SIZE

            player = self.game_manager.player
            player_x = player.position.x
            player_y = player.position.y

            dx = target_x - player_x
            dy = target_y - player_y
            distance = (dx**2 + dy**2)**0.5

            if distance < 5:
                # 吸附並前往下一點
                player.position.x = float(target_x)
                player.position.y = float(target_y)
                self.current_path_index += 1
                
                if self.current_path_index >= len(self.navigation_path):
                    self.is_navigating = False
                    self.game_manager.navigation_active = False
                    # 到達終點，切換回 IDLE 動畫 (避免原地踏步)
                    if hasattr(player, 'animation'):
                        # 這裡簡單重設為第一幀，或者您可以根據最後方向設 idle
                        pass 
                    return
                continue

            # 移動
            speed = 300
            move_dist = speed * dt
            if move_dist > distance:
                move_dist = distance

            if distance > 0:
                move_x = (dx / distance) * move_dist
                move_y = (dy / distance) * move_dist
                player.position.x += move_x
                player.position.y += move_y

                # [修正] 轉向邏輯 (不再是月球漫步)
                if abs(dx) > abs(dy):
                    # 水平移動為主
                    if dx > 0:
                        player.animation.switch("right")
                    else:
                        player.animation.switch("left")
                else:
                    # 垂直移動為主
                    if dy > 0:
                        player.animation.switch("down")
                    else:
                        player.animation.switch("up")
                
                # [修正] 強制更新動畫，讓腳動起來
                player.animation.update(dt)
            
            break

    def draw(self, screen: pg.Surface):
        if not self.is_open and not self.is_navigating:
            return

        if self.is_open:
            self._draw_panel(screen)
        elif self.is_navigating:
            self._draw_navigation_overlay(screen)

    def _draw_panel(self, screen: pg.Surface):
        """繪製導航面板。"""
        # 半透明背景
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(140)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        # 主面板
        screen.blit(self.surface, self.rect)

        # 標題
        title = self.font_title.render("NAVIGATION", True, (0, 0, 0))
        title_x = self.rect.centerx - title.get_width() // 2
        screen.blit(title, (title_x, self.rect.top + 25))

        # -----------------------------------------------
        # 繪製滾動區域 (Clipping)
        # -----------------------------------------------
        row_height = 65
        content_height = max(self.clip_rect.height, len(self.destinations) * row_height)
        temp_surface = pg.Surface((self.clip_rect.width, content_height), pg.SRCALPHA)
        
        for i, dest in enumerate(self.destinations):
            # 相對 temp_surface 的 y 位置
            item_y = i * row_height
            
            # 1. 繪製 Banner (底圖)
            banner_rect = self.banner_surface.get_rect(topleft=(0, item_y + 10))
            temp_surface.blit(self.banner_surface, banner_rect)

            # 2. 繪製文字 (置中於 Banner)
            name_surf = self.font_text.render(dest["name"], True, (0, 0, 0))
            
            text_x = banner_rect.centerx - name_surf.get_width() // 2
            text_y = banner_rect.centery - name_surf.get_height() // 2
            
            temp_surface.blit(name_surf, (text_x, text_y))

        # 將 temp_surface 繪製到螢幕上
        screen.set_clip(self.clip_rect)
        
        src_rect = pg.Rect(0, self.scroll_offset, self.clip_rect.width, self.clip_rect.height)
        screen.blit(temp_surface, self.clip_rect.topleft, area=src_rect)
        
        screen.set_clip(None)

        # -----------------------------------------------
        # 繪製按鈕
        # -----------------------------------------------
        for btn in self.destination_buttons:
            # 只繪製在裁切區域內的按鈕
            if self.clip_rect.top - 10 <= btn.hitbox.y <= self.clip_rect.bottom - 20:
                btn.draw(screen)

        # 關閉按鈕
        self.close_button.rect.topleft = (self.close_rect.x, self.close_rect.y)
        self.close_button.draw(screen)

    def _draw_navigation_overlay(self, screen: pg.Surface):
        """繪製導航中覆蓋層。"""
        dots = "." * ((int(self.dot_animation_timer / self.dot_animation_speed * 4) % 4))
        nav_text = self.font_nav.render(f"{self.navigation_text}{dots}", True, (255, 255, 255))

        text_x = (GameSettings.SCREEN_WIDTH - nav_text.get_width()) // 2
        text_y = 50

        shadow_text = self.font_nav.render(f"{self.navigation_text}{dots}", True, (0, 0, 0))
        screen.blit(shadow_text, (text_x + 2, text_y + 2))
        screen.blit(nav_text, (text_x, text_y))

    def open(self):
        self.is_open = True
        self.scroll_offset = 0

    def close(self):
        self.is_open = False