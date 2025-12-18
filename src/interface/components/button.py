from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent


class Button(UIComponent):
    img_button_default: Sprite
    img_button_hover: Sprite
    img_button: Sprite
    hitbox: pg.Rect
    on_click: Callable[[], None] | None

    # CHECKPOINT2: 按鈕元件（可顯示文字），被多處設定畫面與介面重用
    # --- 新增：文字 ---
    label: str
    font: pg.font.Font | None
    label_surface: pg.Surface | None

    """
    可重用的按鈕元件，支援一般與 hover 圖片、碰撞箱、以及點擊回呼。

    目的：滿足 Checkpoint1（Menu button 切換場景）與 Checkpoint2（設定面板、背包按鈕、Overlay 開關）
    的 UI 元件需求。按鈕使用 `input_manager` 讀取游標位置與滑鼠事件，並在 detect click 時呼叫
    傳入的 `on_click` callback。
    """

    def __init__(
        self,
        img_path: str,
        img_hovered_path: str,
        x: int, y: int,
        width: int, height: int,
        on_click: Callable[[], None] | None = None,
        label: str = "",
        font: pg.font.Font | None = None
    ):
        # 圖片資源（一般與滑鼠懸停狀態）
        self.img_button_default = Sprite(img_path, (width, height))
        self.img_button_hover = Sprite(img_hovered_path, (width, height))
        self.img_button = self.img_button_default

        # 碰撞框（按鈕可互動區域）
        self.hitbox = pg.Rect(x, y, width, height)
        self.on_click = on_click

        # 按鈕文字（選用）
        self.label = label
        self.font = font
        if self.label and self.font:
            self.label_surface = self.font.render(self.label, True, (0, 0, 0))
        else:
            self.label_surface = None

    @override
    def update(self, dt: float) -> None:
        mouse_pos = input_manager.mouse_pos
        inside = self.hitbox.collidepoint(mouse_pos)

        if inside:
            self.img_button = self.img_button_hover
            # 當滑鼠在按鈕範圍內，切換為 hover 圖片；如果偵測到按下事件，執行 on_click
            # 使用 input_manager.mouse_pressed(1) 而非 mouse_down，以便在按鍵被按下的那一幀觸發一次
            if input_manager.mouse_pressed(1) and self.on_click:
                Logger.info(f"Button clicked: {self.label}")
                self.on_click()
        else:
            self.img_button = self.img_button_default

    @override
    def draw(self, screen: pg.Surface) -> None:
        # Draw image
        screen.blit(self.img_button.image, self.hitbox)

        # Draw label
        if self.label_surface:
            rect = self.label_surface.get_rect(center=self.hitbox.center)
            screen.blit(self.label_surface, rect)
        # NOTE: draw 只負責呈現，按鈕互動邏輯全部在 update 中處理。
