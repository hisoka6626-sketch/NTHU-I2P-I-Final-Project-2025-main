import pygame as pg

from src.scenes.scene import Scene
from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.interface.components.button import Button
from src.interface.components.slider import Slider
from src.interface.components.checkbox import Checkbox
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override


class SettingScene(Scene):

    # CHECKPOINT2: 設定畫面，包含音量控制、靜音選項與載入/返回按鈕

    def __init__(self):
        super().__init__()

        self.background = BackgroundSprite("backgrounds/background1.png")

        # ---------------------------------------------------------
        # UI 畫框
        # ---------------------------------------------------------
        raw_frame = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
        frame_w, frame_h = 500, 450
        self.ui_surface = pg.transform.smoothscale(raw_frame, (frame_w, frame_h))

        win_x = (GameSettings.SCREEN_WIDTH - frame_w) // 2
        win_y = (GameSettings.SCREEN_HEIGHT - frame_h) // 2
        self.window_rect = pg.Rect(win_x, win_y, frame_w, frame_h)

        # ---------------------------------------------------------
        # 字型（Minecraft 風格）
        # ---------------------------------------------------------
        self.font36 = pg.font.Font("assets/fonts/Minecraft.ttf", 30)
        self.font24 = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
        self.font18 = pg.font.Font("assets/fonts/Minecraft.ttf", 18)

        # ---------------------------------------------------------
        # 關閉按鈕（右上角）
        # ---------------------------------------------------------
        self.close_button = Button(
            "UI/button_x.png",
            "UI/button_x_hover.png",
            win_x + frame_w - 50, win_y + 10,
            35, 35,
            on_click=lambda: scene_manager.change_scene("menu")
        )

        # ---------------------------------------------------------
        # 音量滑桿
        # ---------------------------------------------------------
        slider_w = 300
        slider_x = win_x + (frame_w - slider_w) // 2
        slider_y = win_y + 120

        def on_vol(v: float):
            GameSettings.AUDIO_VOLUME = v
            # 若未全域靜音則套用音量
            if sound_manager.current_bgm and not GameSettings.MUTED:
                sound_manager.current_bgm.set_volume(v)

        self.volume_slider = Slider(
            slider_x, slider_y, slider_w,
            height=16,
            min_value=0.0, max_value=1.0,
            initial_value=GameSettings.AUDIO_VOLUME,
            label="",
            show_percentage=False,
            on_change=on_vol
        )

        # ---------------------------------------------------------
        # 靜音勾選框
        # ---------------------------------------------------------
        self.mute_checkbox = Checkbox(
            x=slider_x,
            y=slider_y + 70,
            size=28,
            label="",
            is_checked=GameSettings.MUTED,
            on_change=self._toggle_mute
        )

        # ---------------------------------------------------------
        # 按鈕：Load / Back（主選單版本只有這兩個）
        # ---------------------------------------------------------
        btn_w, btn_h = 80, 70
        spacing = 20
        start_x = win_x + (frame_w - (btn_w * 2 + spacing)) // 2
        btn_y = win_y + frame_h - 100

        # Load
        self.load_button = Button(
            "UI/button_load.png",
            "UI/button_load_hover.png",
            start_x,
            btn_y,
            btn_w, btn_h,
            on_click=lambda: None  # 之後 Hackathon 3 會使用
        )

        # Back
        self.back_button = Button(
            "UI/button_back.png",
            "UI/button_back_hover.png",
            start_x + btn_w + spacing,
            btn_y,
            btn_w, btn_h,
            on_click=lambda: scene_manager.change_scene("menu")
        )


    # ---------------------------------------------------------
    # 回呼函式（設定相關）
    # ---------------------------------------------------------
    def _toggle_mute(self, checked: bool):
        # 儲存全域靜音旗標，並交由 sound_manager 處理實際行為
        GameSettings.MUTED = bool(checked)
        if hasattr(sound_manager, 'set_muted'):
            sound_manager.set_muted(GameSettings.MUTED)
        else:
            # 備援：直接設定當前背景音量
            if sound_manager.current_bgm:
                sound_manager.current_bgm.set_volume(0.0 if GameSettings.MUTED else GameSettings.AUDIO_VOLUME)


    # ---------------------------------------------------------
    # 更新（UI 元件狀態）
    # ---------------------------------------------------------
    @override
    def update(self, dt: float):
        self.close_button.update(dt)
        self.volume_slider.update(dt)
        self.mute_checkbox.update(dt)
        self.load_button.update(dt)
        self.back_button.update(dt)

        if input_manager.key_pressed(pg.K_ESCAPE):
            scene_manager.change_scene("menu")


    # ---------------------------------------------------------
    # 繪製
    # ---------------------------------------------------------
    @override
    def draw(self, screen: pg.Surface):

        self.background.draw(screen)
        screen.blit(self.ui_surface, self.window_rect)

        # ---- 標題 ----
        title = self.font36.render("SETTINGS", True, (255, 255, 255))
        screen.blit(title, (self.window_rect.centerx - title.get_width() // 2,
                            self.window_rect.top + 30))

        # ---- 音量文字與百分比 ----
        sx, sy = self.volume_slider.track_rect.x, self.volume_slider.track_rect.y
        percent = int(self.volume_slider.value * 100)
        label = self.font24.render(f"Volume: {percent}%", True, (255, 255, 255))
        screen.blit(label, (sx, sy - 35))

        # ---- 滑桿 ----
        self.volume_slider.draw(screen)

        # ---- 靜音 ----
        mx, my = self.mute_checkbox.hitbox.x, self.mute_checkbox.hitbox.y
        mute_label = self.font24.render("Mute:", True, (255, 255, 255))
        screen.blit(mute_label, (mx - 80, my))
        self.mute_checkbox.draw(screen)

        # ---- 按鈕：載入 / 返回 ----
        self.load_button.draw(screen)
        self.back_button.draw(screen)

        # ---- 提示文字 ----
        hint = self.font18.render("Press ESC to close", True, (255, 255, 255))
        screen.blit(hint, (self.window_rect.centerx - hint.get_width() // 2,
                           self.window_rect.bottom - 30))

        # ---- Close button ----
        self.close_button.draw(screen)
