import pygame as pg
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent


class Checkbox(UIComponent):
    """
    === CHECKPOINT2 02 SETTING COMPONENTS START ===
    - Spec 02 (Setting Components): Checkbox 為設定面板的基本元件之一，會在點擊時呼叫 on_change 並切換 is_checked。
    === CHECKPOINT2 02 SETTING COMPONENTS END ===
    """
    hitbox: pg.Rect
    is_checked: bool
    on_change: Callable[[bool], None] | None
    checkbox_size: int
    label: str
    
    def __init__(
        self,
        x: int,
        y: int,
        size: int = 30,
        label: str = "",
        is_checked: bool = False,
        on_change: Callable[[bool], None] | None = None
    ):
        self.hitbox = pg.Rect(x, y, size, size)
        self.is_checked = is_checked
        self.checkbox_size = size
        self.label = label
        self.on_change = on_change
    
    @override
    def update(self, dt: float) -> None:
        if self.hitbox.collidepoint(input_manager.mouse_pos):
            if input_manager.mouse_pressed(1):
                self.is_checked = not self.is_checked
                Logger.info(f"Checkbox '{self.label}' changed to {self.is_checked}")
                if self.on_change:
                    self.on_change(self.is_checked)
    
    @override
    def draw(self, screen: pg.Surface) -> None:
        # 繪製勾選框背景
        bg_color = (200, 200, 200)
        pg.draw.rect(screen, bg_color, self.hitbox)
        pg.draw.rect(screen, (0, 0, 0), self.hitbox, 2)
        
        # 若被勾選則繪製勾勾
        if self.is_checked:
            # Draw a simple checkmark using circles and line
            check_y = int(self.hitbox.centery)
            check_x1 = int(self.hitbox.left + self.checkbox_size * 0.25)
            check_x2 = int(self.hitbox.left + self.checkbox_size * 0.45)
            check_x3 = int(self.hitbox.right - self.checkbox_size * 0.2)
            check_y1 = check_y
            check_y2 = int(self.hitbox.bottom - self.checkbox_size * 0.25)
            check_y3 = int(self.hitbox.top + self.checkbox_size * 0.2)
            
            pg.draw.line(screen, (0, 150, 0), (check_x1, check_y1), (check_x2, check_y2), 3)
            pg.draw.line(screen, (0, 150, 0), (check_x2, check_y2), (check_x3, check_y3), 3)
        
        # 若有提供 label 則繪製文字
        if self.label:
            font = pg.font.SysFont(None, 24)
            text_surface = font.render(self.label, True, (0, 0, 0))
            text_rect = text_surface.get_rect(
                left=self.hitbox.right + 10,
                centery=self.hitbox.centery
            )
            screen.blit(text_surface, text_rect)
