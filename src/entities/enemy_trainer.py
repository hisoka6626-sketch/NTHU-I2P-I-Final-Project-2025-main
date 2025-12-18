from __future__ import annotations
import pygame
import math
from enum import Enum
from dataclasses import dataclass
from typing import override

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera, Logger


class EnemyTrainerClassification(Enum):
    STATIONARY = "stationary"

@dataclass
class IdleMovement:
    def update(self, enemy: "EnemyTrainer", dt: float) -> None:
        # 保持不動
        return

class EnemyTrainer(Entity):
    classification: EnemyTrainerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction
    
    # Dark Map 模式開關
    is_dark_map: bool 

    # 恐怖效果計時器
    _horror_timer: float
    
    # 擊敗狀態 (避免重複戰鬥)
    is_defeated: bool

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
        is_dark_map: bool = False,
    ) -> None:
        # 指定使用 ow1.png (訓練家圖案)，避免變成隨機 NPC
        sprite_path = "character/ow1.png"
        super().__init__(x, y, game_manager, sprite_path=sprite_path)
        
        self.classification = classification
        self.max_tiles = max_tiles
        self.is_dark_map = is_dark_map
        self._horror_timer = 0.0
        self.is_defeated = False

        if self.is_dark_map:
            Logger.info(f"[EnemyTrainer] Horror mode activated at ({x}, {y})")

        if classification == EnemyTrainerClassification.STATIONARY:
            self._movement = IdleMovement()
            if facing is None:
                Logger.warning(f"Idle EnemyTrainer at ({x}, {y}) missing 'facing'! Defaulting to DOWN.")
                facing = Direction.DOWN
            self._set_direction(facing)
        else:
            raise ValueError("Invalid classification")
        
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False

    @override
    def update(self, dt: float) -> None:
        # 如果已擊敗，停止更新
        if self.is_defeated:
            return

        # 1. 基礎移動 (IdleMovement = 不動)
        self._movement.update(self, dt)
        
        # 2. 視線檢查
        self._has_los_to_player()
        
        # 更新恐怖計時器 (只影響視覺閃爍，不影響移動)
        if self.is_dark_map:
            self._horror_timer += dt

        # 3. 戰鬥觸發邏輯
        # 條件: 被發現 (detected) 且按下空白鍵
        if self.detected and input_manager.key_pressed(pygame.K_SPACE):
            from src.core.services import scene_manager
            
            has_live_pokemon = False
            if hasattr(self.game_manager.bag, '_monsters_data'):
                for mon in self.game_manager.bag._monsters_data:
                    if mon.get('hp', 0) > 0 and not mon.get('is_dead', False):
                        has_live_pokemon = True
                        break
            
            if has_live_pokemon:
                Logger.info(f"Battle triggered with trainer at ({self.position.x}, {self.position.y}).")
                # 標記為已擊敗，避免戰鬥結束後卡在原地重複觸發
                self.is_defeated = True
                scene_manager.change_scene("battle")
            else:
                Logger.info("Cannot fight trainer: No live pokemon!")
                game_scene = scene_manager._scenes.get("game")
                if game_scene:
                    game_scene.show_no_pokemon_warning = True
                    game_scene.warning_timer = 2.0

        # 更新動畫位置
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        # 已擊敗則不畫 (消失)
        if self.is_defeated:
            return

        # ==========================================
        # 1. 一般模式 (Normal Mode)
        # ==========================================
        if not self.is_dark_map:
            super().draw(screen, camera)
            if self.detected:
                self.warning_sign.draw(screen, camera)
            if GameSettings.DRAW_HITBOXES:
                los_rect = self._get_los_rect()
                if los_rect is not None:
                    pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)
            return

        # ==========================================
        # 2. 暗黑模式 (Horror Mode)
        # ==========================================
        
        # A. 畫視線 (Flashlight)
        los_rect = self._get_los_rect()
        if los_rect is not None:
            los_surf = pygame.Surface((los_rect.width, los_rect.height), pygame.SRCALPHA)
            
            if self.detected:
                # 被發現：紅色快閃
                alpha = int(100 + 50 * math.sin(self._horror_timer * 15))
                los_color = (255, 0, 0, alpha) 
            else:
                # 沒發現：手電筒呼吸燈
                alpha = int(30 + 10 * math.sin(self._horror_timer * 2))
                los_color = (200, 200, 220, alpha)

            los_surf.fill(los_color)
            screen.blit(los_surf, camera.transform_rect(los_rect))

        # B. 畫變暗的人物
        # 使用 self.animation.image 確保是用 Entity 切割好的圖
        current_frame = self.animation.image
        darkened_image = current_frame.copy()
        
        tint_color = (150, 80, 80) if self.detected else (60, 60, 80)
        darkened_image.fill(tint_color, special_flags=pygame.BLEND_RGB_MULT)
        
        # 計算繪製位置
        rect = darkened_image.get_rect(topleft=(self.position.x, self.position.y))
        transformed_rect = camera.transform_rect(rect)
        
        screen.blit(darkened_image, transformed_rect)

        # C. 畫發光眼睛
        if self.direction != Direction.UP:
            eye_color = (255, 0, 0)
            eye_radius = 2 
            
            head_y = transformed_rect.y + (transformed_rect.height * 0.3)
            center_x = transformed_rect.x + (transformed_rect.width // 2)
            eye_spacing = transformed_rect.width * 0.15 

            if self.direction == Direction.DOWN:
                pygame.draw.circle(screen, eye_color, (center_x - eye_spacing, head_y), eye_radius)
                pygame.draw.circle(screen, eye_color, (center_x + eye_spacing, head_y), eye_radius)
            elif self.direction == Direction.RIGHT:
                pygame.draw.circle(screen, eye_color, (center_x + eye_spacing, head_y), eye_radius)
            elif self.direction == Direction.LEFT:
                pygame.draw.circle(screen, eye_color, (center_x - eye_spacing, head_y), eye_radius)

        # D. 畫驚嘆號
        if self.detected:
            offset_y = math.sin(self._horror_timer * 8) * 3
            original_sign_pos = Position(
                self.position.x + GameSettings.TILE_SIZE // 4, 
                self.position.y - GameSettings.TILE_SIZE // 2 + offset_y
            )
            self.warning_sign.update_pos(original_sign_pos)
            self.warning_sign.draw(screen, camera)

    def _set_direction(self, direction: Direction) -> None:
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
    def from_dict(cls, data: dict, game_manager: GameManager) -> "EnemyTrainer":
        classification = EnemyTrainerClassification(data.get("classification", "stationary"))
        max_tiles = data.get("max_tiles")
        facing_val = data.get("facing")
        facing: Direction | None = None
        
        if facing_val is not None:
            if isinstance(facing_val, str):
                facing = Direction[facing_val]
            elif isinstance(facing_val, Direction):
                facing = facing_val
        if facing is None and classification == EnemyTrainerClassification.STATIONARY:
            facing = Direction.DOWN
            
        # 讀取 is_dark_map
        is_dark_map = False
        if "is_dark_map" in data:
            is_dark_map = data["is_dark_map"]
        elif "properties" in data and "is_dark_map" in data["properties"]:
            is_dark_map = data["properties"]["is_dark_map"]
        
        return cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            classification,
            max_tiles,
            facing,
            is_dark_map=is_dark_map
        )

    @override
    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = super().to_dict()
        base["classification"] = self.classification.value
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        base["is_dark_map"] = self.is_dark_map
        return base