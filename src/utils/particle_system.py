import pygame
import random
import math
from typing import List, Tuple
from dataclasses import dataclass
from src.utils import Position, PositionCamera

@dataclass
class Particle:
    x: float
    y: float
    vx: float  # X軸速度
    vy: float  # Y軸速度
    life: float  # 剩餘壽命 (秒)
    max_life: float
    size: float
    color: Tuple[int, int, int]
    alpha: float = 255.0
    fade_speed: float = 0.0  # 透明度消失速度

class ParticleManager:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit(self, x: float, y: float, count: int = 1, 
             color: Tuple[int, int, int] = (255, 255, 255), 
             speed: float = 50.0, life: float = 1.0, size: float = 5.0):
        """發射一般粒子"""
        for _ in range(count):
            angle = random.uniform(0, 3.14159 * 2)
            spd = random.uniform(speed * 0.5, speed * 1.5)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            
            p = Particle(
                x=x, y=y, vx=vx, vy=vy,
                life=life, max_life=life,
                size=random.uniform(size * 0.5, size * 1.5),
                color=color,
                alpha=255.0,
                fade_speed=255.0 / life
            )
            self.particles.append(p)

    def create_dark_fog(self, camera: PositionCamera, screen_width: int, screen_height: int):
        """專門為 Dark Map 設計的迷霧效果"""
        # 限制粒子上限，避免太吃效能
        if len(self.particles) < 100:  
            # 隨機在相機視野內生成
            # 注意：這裡使用 camera.x 和 camera.y 取得當前鏡頭左上角的絕對世界座標
            offset_x = random.randint(0, screen_width)
            offset_y = random.randint(0, screen_height)
            world_x = camera.x + offset_x
            world_y = camera.y + offset_y
            
            p = Particle(
                x=world_x, y=world_y,
                vx=random.uniform(-10, 10), # 飄動很慢
                vy=random.uniform(-5, 5),
                life=random.uniform(3.0, 6.0), # 活久一點
                max_life=5.0,
                size=random.uniform(20, 60), # 很大顆
                color=(20, 20, 30), # 深藍灰色
                alpha=0.0, # 初始透明
                fade_speed=-50 # 負值代表淡入
            )
            p.alpha = 0
            self.particles.append(p)

    def update(self, dt: float):
        for p in self.particles[:]:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            
            # 處理透明度
            if p.color == (20, 20, 30): # 針對迷霧的特殊邏輯
                # 迷霧邏輯：先淡入再淡出
                if p.life > p.max_life * 0.5:
                    p.alpha = min(100, p.alpha + 100 * dt) # 淡入到 max 100
                else:
                    p.alpha = max(0, p.alpha - 50 * dt) # 慢慢淡出
            else:
                # 一般粒子邏輯
                p.alpha -= p.fade_speed * dt

            if p.life <= 0 or p.alpha <= 0:
                self.particles.remove(p)

    def draw(self, screen: pygame.Surface, camera: PositionCamera):
        for p in self.particles:
            # 【修正點】：手動計算螢幕座標，而不是呼叫 transform_coords
            # 螢幕座標 = 世界座標 - 攝影機座標
            draw_x = p.x - camera.x
            draw_y = p.y - camera.y
            
            # 簡單優化：如果在畫面外就不畫
            if not (-p.size <= draw_x <= screen.get_width() + p.size and -p.size <= draw_y <= screen.get_height() + p.size):
                continue

            # 建立帶有 Alpha 的 Surface
            radius = int(p.size)
            if radius < 1: continue
            
            # 繪製粒子
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*p.color, int(p.alpha)), (radius, radius), radius)
            screen.blit(surf, (draw_x - radius, draw_y - radius))