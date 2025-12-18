import pygame as pg

from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override

class MenuScene(Scene):
    # 背景圖 (Menu 場景用)
    background: BackgroundSprite
    # 按鈕元件
    play_button: Button
    setting_button: Button
    
    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background1.png")

        base_x = GameSettings.SCREEN_WIDTH // 2
        base_y = GameSettings.SCREEN_HEIGHT * 3 // 4
        button_spacing = 150  
        
        # CHECKPOINT1 TODO1: 選單按鈕 — 設定按鈕（點擊切換到設定場景）
        # CHECKPOINT1 TODO1: 建立設定按鈕，hover 與 click 行為由 Button 處理
        self.setting_button = Button(
            "UI/button_setting.png", "UI/button_setting_hover.png",
            base_x - button_spacing, base_y, 100, 100,
            lambda: scene_manager.change_scene("setting")
        )
        
        # CHECKPOINT1 TODO1: 建立 Play 按鈕（點擊切換到遊戲場景）
        # 按鈕圖檔包含預設與 hover 狀態，Button 會自動處理滑鼠事件
        self.play_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            base_x + 50, base_y, 100, 100,
            lambda: scene_manager.change_scene("game")
        )
        
    @override
    def enter(self) -> None:
        # 進入 Menu Scene 時播放背景音樂
        sound_manager.play_bgm("RBY 101 Opening (Part 1).ogg")
        return

    @override
    def exit(self) -> None:
        # 離開 Menu Scene 無需額外清理
        return

    @override
    def update(self, dt: float) -> None:
        if input_manager.key_pressed(pg.K_SPACE):
            scene_manager.change_scene("game")
            return
        self.play_button.update(dt)
        self.setting_button.update(dt)

    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        self.play_button.draw(screen)
        self.setting_button.draw(screen)
