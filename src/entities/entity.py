from __future__ import annotations
import pygame as pg
from typing import override
from src.sprites import Animation
from src.utils import Position, PositionCamera, Direction, GameSettings
from src.core import GameManager


class Entity:
    animation: Animation
    direction: Direction
    position: Position
    game_manager: GameManager
    
    def __init__(self, x: float, y: float, game_manager: GameManager, sprite_path: str | None = None) -> None:
        # Sprite selection: keep player as ow1, randomize NPCs (exclude ow1)
        import random
        if sprite_path is None:
            # default player sprite is 'ow1'; other entities pick a random sprite excluding 'ow1'
            if self.__class__.__name__ == "Player":
                sprite_path = "character/ow5.png"
            else:
                npc_sprites = [f"character/ow{i}.png" for i in range(2, 11)]
                sprite_path = random.choice(npc_sprites)
        self.animation = Animation(
            sprite_path, ["down", "left", "right", "up"], 4,
            (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        )
        
        self.position = Position(x, y)
        self.direction = Direction.DOWN
        self.animation.update_pos(self.position)
        self.game_manager = game_manager

    def update(self, dt: float) -> None:
        self.animation.update_pos(self.position)
        self.animation.update(dt)
        
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        self.animation.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            self.animation.draw_hitbox(screen, camera)
        
    @staticmethod
    def _snap_to_grid(value: float) -> int:
        return round(value / GameSettings.TILE_SIZE) * GameSettings.TILE_SIZE
    
    @property
    def camera(self) -> PositionCamera:
        
        screen_width = GameSettings.SCREEN_WIDTH
        screen_height = GameSettings.SCREEN_HEIGHT
        
        
        camera_x = int(self.position.x - screen_width // 2)
        camera_y = int(self.position.y - screen_height // 2)
        
        return PositionCamera(camera_x, camera_y)
        
    def to_dict(self) -> dict[str, object]:
        return {
            "x": self.position.x / GameSettings.TILE_SIZE,
            "y": self.position.y / GameSettings.TILE_SIZE,
        }
        
    @classmethod
    def from_dict(cls, data: dict[str, float | int], game_manager: GameManager) -> Entity:
        x = float(data["x"])
        y = float(data["y"])
        return cls(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE, game_manager)
        