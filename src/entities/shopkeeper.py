from __future__ import annotations
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import override, Callable

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera


@dataclass
class IdleMovement:
    def update(self, shopkeeper: "Shopkeeper", dt: float) -> None:
        return


class Shopkeeper(Entity):
    """商人 NPC，固定為 ow8，具有視角檢測、警告標誌、UI 互動功能。"""
    
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction
    on_interact: Callable[[], None] | None  # 當按 SPACE 時呼叫的回調函數

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        facing: Direction | None = None,
        on_interact: Callable[[], None] | None = None,
    ) -> None:
        # 強制設定為 ow8，不使用隨機化
        super().__init__(x, y, game_manager, sprite_path="character/ow8.png")
        self._movement = IdleMovement()
        if facing is None:
            facing = Direction.DOWN
        self._set_direction(facing)
        
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False
        self.on_interact = on_interact

    @override
    def update(self, dt: float) -> None:
        """更新移動、視線檢查、互動邏輯。"""
        self._movement.update(self, dt)
        self._has_los_to_player()
        
        # 按下 SPACE 觸發互動回調
        if self.detected and input_manager.key_pressed(pygame.K_SPACE):
            if self.on_interact:
                self.on_interact()
        
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        """繪製商人及警告標誌。"""
        super().draw(screen, camera)
        if self.detected:
            self.warning_sign.draw(screen, camera)
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)

    def _set_direction(self, direction: Direction) -> None:
        """設定商人面向方向。"""
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
        self.los_direction = self.direction

    def _get_los_rect(self) -> pygame.Rect | None:
        """建立視線範圍矩形。"""
        vision_depth = 3 * GameSettings.TILE_SIZE
        vision_width = 2 * GameSettings.TILE_SIZE
        
        if self.los_direction == Direction.UP:
            return pygame.Rect(
                self.position.x - vision_width // 2,
                self.position.y - vision_depth,
                vision_width,
                vision_depth
            )
        elif self.los_direction == Direction.DOWN:
            return pygame.Rect(
                self.position.x - vision_width // 2,
                self.position.y + GameSettings.TILE_SIZE,
                vision_width,
                vision_depth
            )
        elif self.los_direction == Direction.LEFT:
            return pygame.Rect(
                self.position.x - vision_depth,
                self.position.y - vision_width // 2,
                vision_depth,
                vision_width
            )
        elif self.los_direction == Direction.RIGHT:
            return pygame.Rect(
                self.position.x + GameSettings.TILE_SIZE,
                self.position.y - vision_width // 2,
                vision_depth,
                vision_width
            )
        return None

    def _has_los_to_player(self) -> None:
        """檢查玩家是否在視線範圍內。"""
        player = self.game_manager.player
        if player is None:
            self.detected = False
            return
        
        los_rect = self._get_los_rect()
        if los_rect is None:
            self.detected = False
            return
        
        player_rect = pygame.Rect(
            player.position.x,
            player.position.y,
            GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE
        )
        
        self.detected = los_rect.colliderect(player_rect)

    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "Shopkeeper":
        """從字典加載商人資料。"""
        facing_val = data.get("facing")
        facing: Direction | None = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                facing = Direction[facing_val]
            elif isinstance(facing_val, Direction):
                facing = facing_val
        if facing is None:
            facing = Direction.DOWN
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            facing,
            on_interact=None,  # 在加載時不設置回調，由 GameScene 設置
        )

    @override
    def to_dict(self) -> dict[str, object]:
        """轉換為字典格式以保存。"""
        base: dict[str, object] = super().to_dict()
        base["facing"] = self.direction.name
        return base
