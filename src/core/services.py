from .managers import InputManager, ResourceManager, SceneManager, SoundManager

input_manager = InputManager()
resource_manager = ResourceManager()
scene_manager = SceneManager()
sound_manager = SoundManager()

# ================================
# Global Game State Flag
# ================================
# 標誌是否應該在遊戲中加載存檔
# False: 從頭開始新遊戲
# True: 加載上次保存的遊戲進度
should_load_game = False
