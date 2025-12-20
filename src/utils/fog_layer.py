import pygame as pg
from src.utils import GameSettings

class FogLayer:
    def __init__(self):
        self.active = False
        self.alpha = 0
        # 簡單的白色半透明 (約 40% 透明度)
        self.target_alpha = 100 
        
        # 建立一個全螢幕的純白色表面
        self.fog_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.fog_surface.fill((255, 255, 255)) 

    def activate(self):
        self.active = True
        if self.alpha == 0:
            self.alpha = 0

    def deactivate(self):
        self.active = False

    def update(self, dt):
        speed = 100 # 淡入速度
        if self.active:
            if self.alpha < self.target_alpha:
                self.alpha += dt * speed
                if self.alpha > self.target_alpha:
                    self.alpha = self.target_alpha
        else:
            if self.alpha > 0:
                self.alpha -= dt * speed
                if self.alpha < 0:
                    self.alpha = 0

    def draw(self, screen):
        if self.alpha > 0:
            self.fog_surface.set_alpha(int(self.alpha))
            screen.blit(self.fog_surface, (0, 0))