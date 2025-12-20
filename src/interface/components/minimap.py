import pygame as pg
from src.utils import GameSettings, Logger, Position
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.maps.map import Map
    from src.entities.player import Player


class Minimap:
    """
    Minimap 組件，顯示當前地圖的縮小視圖和玩家位置。
    """
    
    def __init__(self, map_obj: "Map", player: "Player"):
        self.map = map_obj
        self.player = player
        
        # Minimap 尺寸設置
        self.minimap_width = 250
        self.minimap_height = 200
        self.border_thickness = 2
        
        # Minimap 位置（右上角）
        margin = 10
        self.minimap_x = GameSettings.SCREEN_WIDTH - self.minimap_width - margin
        self.minimap_y = margin
        self.minimap_rect = pg.Rect(
            self.minimap_x,
            self.minimap_y,
            self.minimap_width,
            self.minimap_height
        )
        
        # 地圖像素尺寸
        self.map_pixel_width = self.map.tmxdata.width * GameSettings.TILE_SIZE
        self.map_pixel_height = self.map.tmxdata.height * GameSettings.TILE_SIZE
        
        # 計算縮放比例
        self.scale_x = self.minimap_width / self.map_pixel_width if self.map_pixel_width > 0 else 1
        self.scale_y = self.minimap_height / self.map_pixel_height if self.map_pixel_height > 0 else 1
        
        # 為了保持縱橫比，使用相同的縮放比例（取較小值）
        self.scale = min(self.scale_x, self.scale_y)
        
        # 重新計算實際的 minimap 尺寸
        self.actual_minimap_width = int(self.map_pixel_width * self.scale)
        self.actual_minimap_height = int(self.map_pixel_height * self.scale)
        
        # 邊框色和玩家標記
        self.border_color = (200, 200, 200)  # 白色邊框
        self.bg_color = (50, 50, 50)  # 深灰色背景
        self.player_color = (0, 255, 0)  # 綠色玩家標記
        
        # 字體
        self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        
        # 緩存的 minimap 縮放圖像
        self.minimap_surface = self._create_minimap_surface()
        
    def _create_minimap_surface(self) -> pg.Surface:
        """
        根據地圖的 _surface 創建縮放後的 minimap 圖像。
        """
        try:
            # 從地圖的預渲染表面縮放
            scaled_surface = pg.transform.scale(
                self.map._surface,
                (self.actual_minimap_width, self.actual_minimap_height)
            )
            return scaled_surface
        except Exception as e:
            Logger.error(f"Failed to create minimap surface: {e}")
            # 如果失敗，創建一個純色表面作為備用
            fallback = pg.Surface((self.actual_minimap_width, self.actual_minimap_height))
            fallback.fill(self.bg_color)
            return fallback
    
    def set_map(self, map_obj: "Map"):
        """
        更新 minimap 對應的地圖物件。
        當玩家傳送到新地圖時調用此方法以重新生成 minimap。
        """
        self.map = map_obj
        
        # 重新計算地圖像素尺寸
        self.map_pixel_width = self.map.tmxdata.width * GameSettings.TILE_SIZE
        self.map_pixel_height = self.map.tmxdata.height * GameSettings.TILE_SIZE
        
        # 計算縮放比例
        self.scale_x = self.minimap_width / self.map_pixel_width if self.map_pixel_width > 0 else 1
        self.scale_y = self.minimap_height / self.map_pixel_height if self.map_pixel_height > 0 else 1
        
        # 為了保持縱橫比，使用相同的縮放比例（取較小值）
        self.scale = min(self.scale_x, self.scale_y)
        
        # 重新計算實際的 minimap 尺寸
        self.actual_minimap_width = int(self.map_pixel_width * self.scale)
        self.actual_minimap_height = int(self.map_pixel_height * self.scale)
        
        # 重新生成 minimap 表面
        self.minimap_surface = self._create_minimap_surface()
        Logger.info(f"Minimap updated for new map: {map_obj.path_name}")
    
    # [新增] 空的 update 方法，防止 GameScene 呼叫時崩潰
    def update(self, dt: float):
        pass

    def draw(self, screen: pg.Surface):
        """繪製 minimap。"""
        
        # 繪製背景
        bg_rect = pg.Rect(
            self.minimap_x - 5,
            self.minimap_y - 30,
            self.actual_minimap_width + 10,
            self.actual_minimap_height + 35
        )
        pg.draw.rect(screen, self.bg_color, bg_rect)
        pg.draw.rect(screen, self.border_color, bg_rect, self.border_thickness)
        
        # 繪製 minimap 地圖內容
        screen.blit(self.minimap_surface, (self.minimap_x, self.minimap_y))
        
        # 繪製玩家位置
        if self.player:
            player_x = self.player.position.x
            player_y = self.player.position.y
            
            # 計算玩家在 minimap 上的位置
            minimap_player_x = self.minimap_x + (player_x * self.scale)
            minimap_player_y = self.minimap_y + (player_y * self.scale)
            
            # 繪製玩家為一個小圓點
            player_radius = 5
            pg.draw.circle(
                screen,
                self.player_color,
                (int(minimap_player_x), int(minimap_player_y)),
                player_radius
            )
            # 添加黑色邊框使玩家位置更明顯
            pg.draw.circle(
                screen,
                (0, 0, 0),
                (int(minimap_player_x), int(minimap_player_y)),
                player_radius,
                1
            )
        
        # 繪製標題
        title = self.font.render("MINIMAP", True, self.border_color)
        screen.blit(
            title,
            (self.minimap_x + 5, self.minimap_y - 25)
        )