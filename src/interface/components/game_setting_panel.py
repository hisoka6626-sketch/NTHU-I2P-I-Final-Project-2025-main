import pygame as pg
from src.utils import GameSettings
from src.core.services import sound_manager
from src.interface.components import Button, Slider, Checkbox


class GameSettingPanel:

    # CHECKPOINT2: 設定面板（被 Overlay 與 SettingScene 重用），含儲存/讀取、音量與靜音選項

    def __init__(self, game_manager, on_back):
        self.game_manager = game_manager
        self.on_back = on_back

        # UI 畫框
        raw_frame = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
        frame_w, frame_h = 500, 450
        self.ui_surface = pg.transform.smoothscale(raw_frame, (frame_w, frame_h))

        self.rect = pg.Rect(
            (GameSettings.SCREEN_WIDTH - frame_w) // 2,
            (GameSettings.SCREEN_HEIGHT - frame_h) // 2,
            frame_w, frame_h
        )

        # 字型
        self.font36 = pg.font.Font("assets/fonts/Minecraft.ttf", 30)
        self.font24 = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
        self.font18 = pg.font.Font("assets/fonts/Minecraft.ttf", 18)

        x, y = self.rect.x, self.rect.y

        # 關閉按鈕 (X)
        self.close_button = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            x + frame_w - 50, y + 10, 35, 35,
            on_click=on_back
        )

        # 音量滑桿
        slider_w = 300
        slider_x = x + (frame_w - slider_w) // 2
        slider_y = y + 120

        def on_vol(v: float):
            # 當滑桿改變時被呼叫：更新全域音量設定並立刻套用到正在播放的 BGM
            # 目的：提供設定面板中即時預覽音量的能力（Checkpoint2: Slider）
            GameSettings.AUDIO_VOLUME = v
            if sound_manager.current_bgm:
                sound_manager.current_bgm.set_volume(v)

        self.volume_slider = Slider(
            slider_x, slider_y, slider_w,
            height=16, min_value=0.0, max_value=1.0,
            initial_value=GameSettings.AUDIO_VOLUME,
            label="", show_percentage=False, on_change=on_vol
        )

        # 靜音勾選框
        self.mute_checkbox = Checkbox(
            x=slider_x, y=slider_y + 70,
            size=28, label="", is_checked=GameSettings.MUTED,
            on_change=self._toggle_mute
        )

        # 按鈕（儲存 / 載入 / 返回）
        btn_w, btn_h = 80, 70
        spacing = 20
        start_x = x + (frame_w - (btn_w * 3 + spacing * 2)) // 2
        btn_y = y + frame_h - 100

        # Save
        self.save_button = Button(
            "UI/button_save.png", "UI/button_save_hover.png",
            start_x, btn_y, btn_w, btn_h,
            on_click=self._save_game
        )
        # === CHECKPOINT2 04 SETTING OVERLAY START ===
        # Spec 04 (Setting Overlay): Save button 呼叫 GameManager.save()，需能儲存目前遊戲狀態到檔案。
        # 此處 on_click 綁定 _save_game()，而 _save_game 會呼叫 game_manager.save("saves/game0.json").
        # === CHECKPOINT2 04 SETTING OVERLAY END ===

        # Load
        self.load_button = Button(
            "UI/button_load.png", "UI/button_load_hover.png",
            start_x + btn_w + spacing, btn_y, btn_w, btn_h,
            on_click=self._load_game
        )
        # === CHECKPOINT2 04 SETTING OVERLAY START ===
        # Spec 04 (Setting Overlay): Load button 呼叫 GameManager.load() 並以 copy_from 將狀態套回當前 manager。
        # 此處 on_click 綁定 _load_game()，會處理載入與複寫。
        # === CHECKPOINT2 04 SETTING OVERLAY END ===

        # Back
        self.back_button = Button(
            "UI/button_back.png", "UI/button_back_hover.png",
            start_x + (btn_w + spacing) * 2, btn_y, btn_w, btn_h,
            on_click=on_back
        )


    # ------------------------------------------------------------------
    # 靜音處理函式
    # ------------------------------------------------------------------
    def _toggle_mute(self, checked: bool):
        """切換靜音狀態。"""
        GameSettings.MUTED = bool(checked)
        if hasattr(sound_manager, 'set_muted'):
            sound_manager.set_muted(GameSettings.MUTED)
        else:
            if sound_manager.current_bgm:
                if GameSettings.MUTED:
                    sound_manager.current_bgm.set_volume(0.0)
                else:
                    sound_manager.current_bgm.set_volume(GameSettings.AUDIO_VOLUME)


    # ------------------------------------------------------------------
    # 儲存 / 載入 處理
    # ------------------------------------------------------------------
    def _save_game(self):
        """呼叫 game_manager.save() 將遊戲寫入檔案。

        目的：由設定面板的 Save 按鈕觸發，封裝儲存行為並在失敗時顯示錯誤。
        使用 GameManager.save() 實作的序列化格式與路徑為 `saves/game0.json`。
        """
        try:
            self.game_manager.save("saves/game0.json")
            print("[SAVE] Game saved!")
        except Exception as e:
            print(f"[ERROR] Save failed: {e}")

    def _load_game(self):
        """呼叫 game_manager.load() 並把讀取的狀態套回目前的 manager。

        目的：由設定面板的 Load 按鈕觸發，使用 GameManager.load() 還原檔案，
        再以 GameManager.copy_from() 將新載入的狀態正確套回當前 manager，
        包含 Player、Maps、EnemyTrainer 與 Bag 等結構。
        """
        try:
            new_manager = self.game_manager.load("saves/game0.json")
            if new_manager:
                # 使用 GameManager.copy_from 來正確複製所有狀態
                # copy_from 會建立新的 Player 並把它的 game_manager 指回目前的 manager
                self.game_manager.copy_from(new_manager)
                print("[LOAD] Game loaded!")
        except Exception as e:
            print(f"[ERROR] Load failed: {e}")


    # ------------------------------------------------------------------
    # 更新（UI 元件）
    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.close_button.update(dt)
        self.volume_slider.update(dt)
        self.mute_checkbox.update(dt)

        self.save_button.update(dt)
        self.load_button.update(dt)
        self.back_button.update(dt)


    # ------------------------------------------------------------------
    # 繪製
    # ------------------------------------------------------------------
    def draw(self, screen: pg.Surface):
        screen.blit(self.ui_surface, self.rect)

        # 標題
        title = self.font36.render("SETTINGS", True, (255, 255, 255))
        screen.blit(title, (self.rect.centerx - title.get_width() // 2,
                            self.rect.top + 30))

        # 音量文字
        sx, sy = self.volume_slider.track_rect.x, self.volume_slider.track_rect.y
        percent = int(self.volume_slider.value * 100)
        volume_label = self.font24.render(f"Volume: {percent}%", True, (255, 255, 255))
        screen.blit(volume_label, (sx, sy - 35))

        # Slider
        self.volume_slider.draw(screen)

        # 靜音顯示
        mx, my = self.mute_checkbox.hitbox.x, self.mute_checkbox.hitbox.y
        mute_label = self.font24.render("Mute:", True, (255, 255, 255))
        screen.blit(mute_label, (mx - 80, my))
        self.mute_checkbox.draw(screen)

        # 按鈕群（儲存 / 載入 / 返回）
        self.save_button.draw(screen)
        self.load_button.draw(screen)
        self.back_button.draw(screen)

        # Hint
        hint = self.font18.render("Press ESC to close", True, (255, 255, 255))
        screen.blit(hint, (self.rect.centerx - hint.get_width() // 2,
                           self.rect.bottom - 30))

        # Close button
        self.close_button.draw(screen)
