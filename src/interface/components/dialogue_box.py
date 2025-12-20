import pygame as pg
from src.utils import GameSettings
from src.core.services import input_manager

class DialogueBox:
    def __init__(self):
        self.is_open = False
        self.finished = False # 用來通知外部「對話結束了」
        
        # --- 外觀設定 ---
        # 寬度佔螢幕 80%，高度固定
        self.width = int(GameSettings.SCREEN_WIDTH * 0.8)
        self.height = 180
        self.x = (GameSettings.SCREEN_WIDTH - self.width) // 2
        self.y = GameSettings.SCREEN_HEIGHT - self.height - 30
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        
        # 背景：半透明黑色
        self.bg_surface = pg.Surface((self.width, self.height), pg.SRCALPHA)
        self.bg_surface.fill((0, 0, 0, 210)) # Alpha 210 (約 80% 不透明)
        
        # 字體
        # 內文
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        # 名字 (稍微大一點)
        self.font_name = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
        
        # 資料
        self.lines = []       # 待顯示的對話列表
        self.current_line = 0 # 目前講到第幾句
        self.speaker_name = "" # 說話者名字
        
        # 打字機效果 (可選，這裡先做直接顯示)
        self.display_text = ""

    def start_dialogue(self, lines: list[str], speaker: str = "System"):
        """
        開始一段新的對話。
        :param lines: 字串列表，例如 ["Hello", "World"]
        :param speaker: 說話者名字
        """
        self.lines = lines
        self.speaker_name = speaker
        self.current_line = 0
        self.is_open = True
        self.finished = False

    def next_line(self):
        """跳到下一句，如果沒了就關閉"""
        self.current_line += 1
        if self.current_line >= len(self.lines):
            self.close()

    def close(self):
        self.is_open = False
        self.finished = True # 標記為結束，讓 GameScene 可以觸發後續事件

    def update(self, dt: float):
        if not self.is_open: return
        
        # 按空白鍵換下一句
        if input_manager.key_pressed(pg.K_SPACE):
            self.next_line()

    def draw(self, screen: pg.Surface):
        if not self.is_open: return
        
        # 1. 畫背景框
        screen.blit(self.bg_surface, (self.x, self.y))
        
        # 2. 畫邊框 (白色線條)
        pg.draw.rect(screen, (255, 255, 255), self.rect, 3, border_radius=10)
        
        # 3. 畫名字 (左上角，金色)
        if self.speaker_name:
            name_surf = self.font_name.render(self.speaker_name, True, (255, 215, 0))
            # 加一點陰影讓文字更清楚
            name_shadow = self.font_name.render(self.speaker_name, True, (0, 0, 0))
            screen.blit(name_shadow, (self.x + 32, self.y + 22))
            screen.blit(name_surf, (self.x + 30, self.y + 20))
        
        # 4. 畫對話內容 (白色)
        if 0 <= self.current_line < len(self.lines):
            text = self.lines[self.current_line]
            
            # 這裡做簡單的自動換行邏輯 (如果字太長)
            # 但為了簡單，先假設你的文本長度適中
            txt_surf = self.font_text.render(text, True, (255, 255, 255))
            screen.blit(txt_surf, (self.x + 40, self.y + 70))
            
        # 5. 提示按鈕 (右下角閃爍的三角形，提示玩家按鍵)
        # 利用時間做閃爍效果
        if (pg.time.get_ticks() // 500) % 2 == 0:
            triangle_points = [
                (self.x + self.width - 40, self.y + self.height - 30),
                (self.x + self.width - 20, self.y + self.height - 30),
                (self.x + self.width - 30, self.y + self.height - 20),
            ]
            pg.draw.polygon(screen, (255, 255, 255), triangle_points)