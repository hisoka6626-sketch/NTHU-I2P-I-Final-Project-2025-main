import pygame as pg
from src.utils import GameSettings
from src.core.services import input_manager
from src.interface.components import Button
from src.interface.components.game_setting_panel import GameSettingPanel
from typing import Callable


class Overlay:
    """
    === CHECKPOINT2 01 OVERLAY START ===
    - Spec 01 (Overlay): 提供一個可以在遊戲畫面按下後顯示在中央的覆蓋面板，並在背景暗化時顯示返回按鈕以關閉。
    - 此類別負責：dark_surface (半透明遮罩)、panel (實際 UI 面板)、open()/close()/update()/draw()。
    === CHECKPOINT2 01 OVERLAY END ===
    """

    def __init__(self, game_manager, on_close: Callable[[], None] | None = None):
        self.is_open = False
        self.game_manager = game_manager
        self.on_close = on_close

        # Overlay 背景（半透明遮罩）
        self.dark_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.dark_surface.set_alpha(140)
        self.dark_surface.fill((0, 0, 0))

        # 真正的設定面板（重用 GameSettingPanel）
        self.panel = GameSettingPanel(game_manager, on_back=self.close)

    # -- open / close ----------------------------------------------------------

    def open(self):
        self.is_open = True

    def close(self):
        self.is_open = False
        if self.on_close:
            self.on_close()

    # -- update ----------------------------------------------------------------

    def update(self, dt: float):
        if not self.is_open:
            return

        self.panel.update(dt)

        # 按 ESC 可以關閉設定覆蓋面板
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()

    # -- draw ------------------------------------------------------------------

    def draw(self, screen: pg.Surface):
        if not self.is_open:
            return

        # 繪製半透明暗背景以突顯設定面板
        screen.blit(self.dark_surface, (0, 0))

        # Draw panel UI
        self.panel.draw(screen)
