from __future__ import annotations
import pygame as pg
import math
from .entity import Entity
from src.core.services import input_manager
from src.utils import Position, PositionCamera, GameSettings, Direction
from src.core import GameManager
from typing import override


class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager
    _last_teleport_time: float
    _teleport_cooldown: float

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)
        self._last_teleport_time = 0.0
        self._teleport_cooldown = 2.0  # 2 seconds cooldown

    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # CAMERA — 永遠將玩家置中（Hackathon 3）
    # ---------------------------------------------------------
    @property
    def camera(self) -> PositionCamera:
        """
        回傳一個相機 (PositionCamera) 物件，使渲染時玩家位於畫面中央。

        目的：符合 Checkpoint 1 的相機控制要求（玩家永遠置中）。
        實作方法：以玩家世界座標為基準，減去畫面寬高的一半，並加上半個 Tile 的偏移
        （確保以 Tile 的中心對齊），回傳一個可供渲染系統用來轉換座標的 PositionCamera。
        """
        cam_x = int(self.position.x - GameSettings.SCREEN_WIDTH // 2 + GameSettings.TILE_SIZE // 2)
        cam_y = int(self.position.y - GameSettings.SCREEN_HEIGHT // 2 + GameSettings.TILE_SIZE // 2)
        return PositionCamera(cam_x, cam_y)

    # ---------------------------------------------------------
    # 與敵人碰撞檢查
    # ---------------------------------------------------------
    def _check_collision_with_enemy(self, enemy: Entity) -> bool:
        player_rect = pg.Rect(
            self.position.x,
            self.position.y,
            GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE
        )
        enemy_rect = pg.Rect(
            enemy.position.x,
            enemy.position.y,
            GameSettings.TILE_SIZE,
            GameSettings.TILE_SIZE
        )
        return player_rect.colliderect(enemy_rect)

    # ---------------------------------------------------------
    # 移動、碰撞與傳送 (Hackathon 2 / Hackathon 4 / Hackathon 6)
    # ---------------------------------------------------------
    @override
    def update(self, dt: float) -> None:

        # 如果導航活躍中，不處理玩家輸入
        if self.game_manager.navigation_active:
            # 仍然更新動畫位置
            self.animation.update_pos(self.position)
            self.animation.update(dt)
            return

        # 如果聊天活躍中，不處理玩家輸入
        if self.game_manager.chat_active:
            # 仍然更新動畫位置
            self.animation.update_pos(self.position)
            self.animation.update(dt)
            return

        dis = Position(0, 0)

        # ---------------------------------------
        # 輸入：WASD 與方向鍵控制移動
        # ---------------------------------------
        if input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
            dis.x -= 1
            self.direction = Direction.LEFT
            self.animation.switch("left")

        if input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
            dis.x += 1
            self.direction = Direction.RIGHT
            self.animation.switch("right")

        if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
            dis.y -= 1
            self.direction = Direction.UP
            self.animation.switch("up")

        if input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
            dis.y += 1
            self.direction = Direction.DOWN
            self.animation.switch("down")

        # ---------------------------------------
        # 歸一化移動速度（Checkpoint1/2: Player Movement）
        # 目的：確保斜向行走不會比水平或垂直走更快（向量長度一樣時速度相同）
        # 方法：計算輸入向量的長度，將向量單位化(unit vector)，再乘上速度與時間差 dt
        # 注意：如果 dis 為 (0,0) 則不用計算以避免除以零
        # ---------------------------------------
        if dis.x != 0 or dis.y != 0:
            length = math.sqrt(dis.x * dis.x + dis.y * dis.y)
            dis.x = dis.x / length * self.speed * dt*2
            dis.y = dis.y / length * self.speed * dt*2

        # ---------------------------------------------------------
        # 平滑碰撞處理（Checkpoint1: Collision）
        # 目的：避免在角落或斜向移動時卡住，並且允許在一個軸無碰撞的情況下滑過障礙
        # 方法：將移動分成 X 與 Y 兩階段處理
        #  1) 先嘗試更新 X，檢查是否與地圖或敵人碰撞，若碰撞則將 X 回退到先前格線位置
        #  2) 再嘗試更新 Y，檢查是否碰撞，若碰撞則將 Y 回退到先前格線位置
        # 這種做法可讓角色在貼著牆面移動時沿牆滑動（而不是同時阻止 X 與 Y）
        # ---------------------------------------------------------

        # ------------ X movement ------------
        new_x = self.position.x + dis.x
        old_x = self.position.x
        self.position.x = new_x

        collision_x = False

        # collision with map
        if self.game_manager.current_map.check_collision(self.position):
            collision_x = True

        # collision with enemies
        for enemy in self.game_manager.current_enemy_trainers:
            if self._check_collision_with_enemy(enemy):
                collision_x = True
                break

        if collision_x:
            self.position.x = self._snap_to_grid(old_x)

        # ------------ Y movement ------------
        new_y = self.position.y + dis.y
        old_y = self.position.y
        self.position.y = new_y

        collision_y = False

        if self.game_manager.current_map.check_collision(self.position):
            collision_y = True

        for enemy in self.game_manager.current_enemy_trainers:
            if self._check_collision_with_enemy(enemy):
                collision_y = True
                break

        if collision_y:
            self.position.y = self._snap_to_grid(old_y)

        # ---------------------------------------------------------
        # 傳送 (Teleport) 檢查 (Hackathon 6)
        # ---------------------------------------------------------
        tp = self.game_manager.current_map.check_teleport(self.position)
        if tp:
            current_time = pg.time.get_ticks() / 1000.0
            if current_time - self._last_teleport_time >= self._teleport_cooldown:
                # Pass the Teleport object so GameManager can determine the
                # corresponding entrance in the destination map and place the
                # player at the proper entrance (avoids spawning inside collision).
                from src.utils import Logger
                Logger.info(f"[TELEPORT] Detected at {tp.pos.x}, {tp.pos.y} -> {tp.destination}")
                self.game_manager.switch_map(tp)
                self._last_teleport_time = current_time
            else:
                from src.utils import Logger
                current_time = pg.time.get_ticks() / 1000.0
                time_left = self._teleport_cooldown - (current_time - self._last_teleport_time)
                Logger.info(f"[TELEPORT] In cooldown ({time_left:.2f}s left)")

        # Animation update
        super().update(dt)

    # ---------------------------------------------------------
    # DRAW
    # ---------------------------------------------------------
    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        super().draw(screen, camera)

    # ---------------------------------------------------------
    # SAVE → JSON
    # ---------------------------------------------------------
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()

    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        player = cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager
        )
        return player
