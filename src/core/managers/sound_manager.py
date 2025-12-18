import pygame as pg
from src.utils import load_sound, GameSettings

class SoundManager:
    def __init__(self):
        pg.mixer.init()
        pg.mixer.set_num_channels(GameSettings.MAX_CHANNELS)
        self.current_bgm = None
        self.muted = False
        
    def play_bgm(self, filepath: str):
        """
        播放背景音樂 (瞬間切換)
        :param filepath: 音樂路徑
        """
        # 1. 如果有舊音樂，直接停止
        if self.current_bgm:
            self.current_bgm.stop()
        
        try:
            # 2. 載入新音樂
            audio = load_sound(filepath)
            
            # 3. 設定音量
            target_volume = 0.0 if self.muted else GameSettings.AUDIO_VOLUME
            audio.set_volume(target_volume)
            
            # 4. 播放 (無限循環, 無淡入)
            audio.play(loops=-1)
            
            self.current_bgm = audio
        except Exception as e:
            print(f"Failed to play BGM {filepath}: {e}")
        
    def pause_all(self):
        pg.mixer.pause()

    def resume_all(self):
        pg.mixer.unpause()
        
    def play_sound(self, filepath, volume=0.7):
        if self.muted:
            return
        try:
            sound = load_sound(filepath)
            sound.set_volume(volume)
            sound.play()
        except Exception as e:
            print(f"Failed to play sound {filepath}: {e}")

    def stop_all_sounds(self):
        pg.mixer.stop()
        self.current_bgm = None
        
    def update_volume(self):
        if self.current_bgm:
            self.current_bgm.set_volume(0.0 if self.muted else GameSettings.AUDIO_VOLUME)

    def set_muted(self, muted: bool):
        self.muted = bool(muted)
        if self.current_bgm:
            self.current_bgm.set_volume(0.0 if self.muted else GameSettings.AUDIO_VOLUME)
        if self.muted:
            pg.mixer.pause()
        else:
            pg.mixer.unpause()