import pygame as pg
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent


class Slider(UIComponent):
    """
    === CHECKPOINT2 02 SETTING COMPONENTS START ===
    - Spec 02 (Setting Components): 需要在設定場景中提供可操作的 Slider（例如音量調整）。
    - 此類別實作：點擊軌道跳轉、拖曳滑塊更新 value、on_change callback。
    === CHECKPOINT2 02 SETTING COMPONENTS END ===
    """
    track_rect: pg.Rect
    knob_rect: pg.Rect
    is_dragging: bool
    value: float
    min_value: float
    max_value: float
    on_change: Callable[[float], None] | None
    label: str
    show_percentage: bool
    
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int = 16,
        min_value: float = 0.0,
        max_value: float = 1.0,
        initial_value: float = 0.5,
        label: str = "",
        show_percentage: bool = True,
        on_change: Callable[[float], None] | None = None
    ):
        self.track_rect = pg.Rect(x, y, width, height)
        self.min_value = min_value
        self.max_value = max_value
        self.value = max(min_value, min(max_value, initial_value))
        self.label = label
        self.show_percentage = show_percentage
        self.on_change = on_change
        self.is_dragging = False
        
        # 初始化滑塊位置
        knob_size = 16
        normalized_value = (self.value - min_value) / (max_value - min_value)
        knob_x = x + normalized_value * (width - knob_size)
        self.knob_rect = pg.Rect(knob_x, y, knob_size, height)
    
    def _update_value_from_position(self, mouse_x: int) -> None:
        """根據滑鼠 x 座標更新滑桿的值與滑塊位置。"""
        relative_x = mouse_x - self.track_rect.x
        normalized = max(0.0, min(1.0, relative_x / self.track_rect.width))
        self.value = self.min_value + normalized * (self.max_value - self.min_value)
        
        # 更新滑塊位置
        knob_size = self.knob_rect.width
        self.knob_rect.centerx = max(
            self.track_rect.left + knob_size // 2,
            min(mouse_x, self.track_rect.right - knob_size // 2)
        )
        
        if self.on_change:
            self.on_change(self.value)
    
    @override
    def update(self, dt: float) -> None:
        mouse_pos = input_manager.mouse_pos
        
        # 檢查是否點擊在滑塊上
        if input_manager.mouse_pressed(1):
            if self.knob_rect.collidepoint(mouse_pos):
                self.is_dragging = True
            elif self.track_rect.collidepoint(mouse_pos):
                # 點擊軌道會把滑塊移到該位置
                self._update_value_from_position(mouse_pos[0])
        
        # 處理拖曳行為
        if self.is_dragging and input_manager.mouse_down(1):
            self._update_value_from_position(mouse_pos[0])
        else:
            self.is_dragging = False
    
    @override
    def draw(self, screen: pg.Surface) -> None:
        # 若有提供 label 則繪製文字（可顯示百分比或實值）
        if self.label:
            font = pg.font.SysFont(None, 24)
            label_text = self.label
            if self.show_percentage:
                percentage = (self.value - self.min_value) / (self.max_value - self.min_value) * 100
                label_text += f": {int(percentage)}%"
            else:
                label_text += f": {self.value:.2f}"
            
            text_surface = font.render(label_text, True, (0, 0, 0))
            text_rect = text_surface.get_rect(
                topleft=(self.track_rect.left, self.track_rect.top - 30)
            )
            screen.blit(text_surface, text_rect)
        
        # 繪製軌道
        track_color = (200, 200, 200)
        pg.draw.rect(screen, track_color, self.track_rect)
        pg.draw.rect(screen, (0, 0, 0), self.track_rect, 1)
        
        # 繪製已填充的部分（代表當前值）
        filled_width = self.knob_rect.centerx - self.track_rect.left
        filled_rect = pg.Rect(
            self.track_rect.left,
            self.track_rect.top,
            filled_width,
            self.track_rect.height
        )
        pg.draw.rect(screen, (100, 150, 255), filled_rect)
        
        # 繪製滑塊
        knob_color = (50, 100, 200) if self.is_dragging else (100, 150, 255)
        pg.draw.rect(screen, knob_color, self.knob_rect)
        pg.draw.rect(screen, (0, 0, 0), self.knob_rect, 1)
