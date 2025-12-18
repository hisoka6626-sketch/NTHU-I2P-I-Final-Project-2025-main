from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pygame as pg

from src.utils import Logger, GameSettings
from src.utils.definition import get_menu_sprite_path
import random

if TYPE_CHECKING:
    from src.maps.map import Map
    from src.entities.player import Player
    from src.entities.enemy_trainer import EnemyTrainer
    from src.data.bag import Bag

class GameManager:
    # Entities
    player: "Player | None"
    enemy_trainers: dict[str, list["EnemyTrainer"]]
    bag: "Bag"

    # Map properties
    current_map_key: str
    maps: dict[str, "Map"]

    # Changing Scene properties (for fade transition + teleport)
    should_change_scene: bool
    next_map: str

    # Teleport cooldown
    _last_teleport_time: float
    _teleport_cooldown: float

    # ★★★ Dark World Event Properties (新增) ★★★
    is_triggering_dark_event: bool  # 是否正在觸發掉入裡世界的事件
    flicker_map_key: str            # 原本想去的地圖 (用於視覺閃爍特效)

    def __init__(
        self,
        maps: dict[str, "Map"],
        start_map: str,
        player: "Player | None",
        enemy_trainers: dict[str, list["EnemyTrainer"]],
        bag: "Bag | None" = None,
    ) -> None:
        from src.data.bag import Bag as _Bag

        # Game Properties
        self.maps = maps
        self.current_map_key = start_map
        self.player = player
        self.enemy_trainers = enemy_trainers
        self.bag = bag if bag is not None else _Bag([], [])

        # Map switching state (used by GameScene for淡入淡出)
        self.should_change_scene = False
        self.next_map = ""

        # ★★★ 初始化黑暗事件狀態 ★★★
        self.is_triggering_dark_event = False
        self.flicker_map_key = ""

        # Navigation target (used by NavigationPanel)
        self.target_map_name = ""
        self.target_position = (0, 0)
        self.pending_navigation_destination = (0, 0)  # Final destination after cross-map teleport
        self.navigation_active = False  # Flag to indicate if navigation is currently active
        self.chat_active = False  # Flag to indicate if chat is currently active

        # Teleport cooldown（避免連續觸發傳送）
        self._last_teleport_time = 0.0
        self._teleport_cooldown = 1.0  # 秒

    # ------------------------------------------------------
    # 便利屬性
    # ------------------------------------------------------
    @property
    def current_map(self) -> "Map":
        return self.maps[self.current_map_key]

    @property
    def current_enemy_trainers(self) -> list["EnemyTrainer"]:
        return self.enemy_trainers.get(self.current_map_key, [])

    # ------------------------------------------------------
    # 傳送 / 換地圖
    # ------------------------------------------------------
    def switch_map(self, dest_or_tp) -> None:
        """
        標記要換地圖但不立即完成切換（配合淡出/淡入動畫）。
        在此處加入 30% 機率掉入 Dark Map 的判定。
        """
        current_time = pg.time.get_ticks() / 1000.0
        if current_time - self._last_teleport_time < self._teleport_cooldown:
            return

        # Determine destination map and possible entrance teleporter
        teleporter_used = None
        if hasattr(dest_or_tp, 'destination') and hasattr(dest_or_tp, 'pos'):
            teleporter_used = dest_or_tp
            dest = teleporter_used.destination
        else:
            dest = dest_or_tp

        if dest not in self.maps:
            Logger.warning(f"Map '{dest}' not loaded; cannot switch.")
            return

        # -----------------------------------------------------------
        # ★★★ Dark World Trigger Logic ★★★
        # -----------------------------------------------------------
        DARK_MAP_KEY = "dark map.tmx"
        
        # 只有當目標不是 dark map，且當前不在 dark map 時才觸發 (避免無限迴圈或從地獄掉到地獄)
        # 這裡設定機率 0.3 (30%)
        if dest != DARK_MAP_KEY and self.current_map_key != DARK_MAP_KEY and DARK_MAP_KEY in self.maps:
            if random.random() < 0.3:
                Logger.info("!!! DARK WORLD EVENT TRIGGERED !!!")
                
                # 1. 標記事件觸發
                self.is_triggering_dark_event = True
                
                # 2. 記錄原本想去哪裡 (例如 map B)，GameScene 繪圖時會用到這個來做閃爍效果
                self.flicker_map_key = dest
                
                # 3. 強制改變目的地為 Dark Map
                self.next_map = DARK_MAP_KEY
                
                # 4. 因為是強制傳送，我們通常不使用原本傳送點的座標邏輯，而是使用 Dark Map 的預設 Spawn
                #    或者你可以設計一個機制，根據 map B 的入口計算 dark map 的對應位置
                self._next_spawn = self.maps[DARK_MAP_KEY].spawn 
                
                self.should_change_scene = True
                self._last_teleport_time = current_time
                return
        # -----------------------------------------------------------

        # Save next map and (optionally) next spawn position derived from teleporter
        self.next_map = dest
        self.should_change_scene = True
        self._last_teleport_time = current_time

        # compute next spawn if teleporter info available
        self._next_spawn = None
        if teleporter_used:
            dest_map = self.maps[dest]
            # find teleporters in destination map that lead back to current map
            candidates = [t for t in dest_map.teleporters if t.destination == self.current_map_key]
            if candidates:
                # choose the first matching entrance
                self._next_spawn = candidates[0].pos


    def try_switch_map(self) -> None:
        """
        真正執行地圖切換的函式（在 GameScene 的 fade-out 或 flicker 動畫完成後由場景呼叫）。
        """
        if not self.should_change_scene:
            return

        # ✔ 換地圖
        self.current_map_key = self.next_map
        self.next_map = ""
        self.should_change_scene = False
        
        # ★★★ 切換完成，重置黑暗事件標記 ★★★
        self.is_triggering_dark_event = False
        self.flicker_map_key = ""

        # Check if this is a navigation target switch
        navigation_target = None
        if self.target_map_name and self.target_position:
            if self.current_map_key == self.target_map_name:
                navigation_target = self.target_position
            self.target_map_name = ""
            self.target_position = (0, 0)

        # ✔ 將玩家放到新地圖的 spawn（若有預設下一個 spawn，優先使用）
        if self.player:
            target_pos = getattr(self, '_next_spawn', None)
            if navigation_target:
                # Use navigation target position
                target_pos = type('Pos', (), {'x': navigation_target[0] * GameSettings.TILE_SIZE, 'y': navigation_target[1] * GameSettings.TILE_SIZE})()
            elif target_pos is not None:
                # Place player AWAY from teleporter entrance to avoid re-triggering
                # Try offset: 2 tiles down from teleporter
                base_x = target_pos.x
                base_y = target_pos.y + 2 * GameSettings.TILE_SIZE
                
                # Check if base offset is walkable; if not, try other directions
                test_rect = pg.Rect(base_x, base_y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
                if not self.check_collision(test_rect):
                    self.player.position.x = base_x
                    self.player.position.y = base_y
                else:
                    # Fallback: try 2 tiles up, left, right
                    offsets = [(0, -2), (-2, 0), (2, 0), (0, 2), (1, 1), (-1, 1), (1, -1), (-1, -1)]
                    found = False
                    for ox, oy in offsets:
                        new_x = target_pos.x + ox * GameSettings.TILE_SIZE
                        new_y = target_pos.y + oy * GameSettings.TILE_SIZE
                        rect = pg.Rect(new_x, new_y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
                        if not self.check_collision(rect):
                            self.player.position.x = new_x
                            self.player.position.y = new_y
                            found = True
                            break
                    if not found:
                        # Last resort: use target_pos directly
                        self.player.position = target_pos
            else:
                self.player.position = self.current_map.spawn

            # Double-check: if placement still collided, micro-adjust
            if self.check_collision(pg.Rect(self.player.position.x, self.player.position.y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)):
                # offsets in tiles to try (including diagonals)
                offsets = [(0,0),(1,0),(-1,0),(0,1),(0,-1),(2,0),(-2,0),(0,2),(0,-2),(1,1),(-1,1),(1,-1),(-1,-1)]
                found = False
                for ox, oy in offsets:
                    new_x = self.player.position.x + ox * GameSettings.TILE_SIZE
                    new_y = self.player.position.y + oy * GameSettings.TILE_SIZE
                    rect = pg.Rect(new_x, new_y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
                    if not self.check_collision(rect):
                        self.player.position.x = new_x
                        self.player.position.y = new_y
                        found = True
                        break
                if not found:
                    Logger.warning("Teleported player into collision and failed to find nearby free tile; leaving at spawn")

        # clear any stored next_spawn
        if hasattr(self, '_next_spawn'):
            self._next_spawn = None


    # ------------------------------------------------------
    # 碰撞檢查
    # ------------------------------------------------------
    def check_collision(self, rect: pg.Rect) -> bool:
        if self.current_map.check_collision(rect):
            return True
        for entity in self.current_enemy_trainers:
            if rect.colliderect(entity.animation.rect):
                return True
        return False

    # ------------------------------------------------------
    # SAVE GAME
    # ------------------------------------------------------
    def save(self, path: str) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
            Logger.info(f"Game saved to {path}")
        except Exception as e:
            Logger.error(f"Failed to save game: {e}")

    def to_dict(self) -> dict[str, object]:
        map_blocks: list[dict[str, object]] = []

        for key, m in self.maps.items():
            block = m.to_dict()  # {"path", "teleport", "player": spawn ...}
            block["enemy_trainers"] = [
                t.to_dict() for t in self.enemy_trainers.get(key, [])
            ]
            map_blocks.append(block)

        return {
            "map": map_blocks,
            "current_map": self.current_map_key,
            "player": self.player.to_dict() if self.player is not None else None,
            "bag": self.bag.to_dict(),
        }

    # ------------------------------------------------------
    # LOAD GAME FROM FILE
    # ------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "GameManager | None":
        if not os.path.exists(path):
            Logger.error(f"No file found: {path}")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            Logger.error(f"JSON load failed ({path}): {e}")
            return None

        return cls.from_dict(data)

    # ------------------------------------------------------
    # CREATE NEW GAME (Fresh Start)
    # ------------------------------------------------------
    @classmethod
    def new_game(cls) -> "GameManager | None":
        if not os.path.exists("saves/game0.json"):
            Logger.error("No default game file found: saves/game0.json")
            return None

        try:
            with open("saves/game0.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            Logger.error(f"JSON load failed (saves/game0.json): {e}")
            return None

        manager = cls.from_dict(data)

        # Try to load recorded monsters from saves/backup.json as wild_pool (preferred)
        try:
            backup_path = "saves/backup.json"
            if os.path.exists(backup_path):
                with open(backup_path, 'r', encoding='utf-8') as f:
                    bdata = json.load(f)
                    bag = bdata.get('bag', {}) or {}
                    monsters = bag.get('monsters') or []
                    if monsters:
                        manager.wild_pool = [dict(m) for m in monsters]
        except Exception:
            pass

        # Fallback: ensure there's a default wild_pool using menu_sprites 1..16
        if not hasattr(manager, 'wild_pool') or manager.wild_pool is None:
            try:
                pool = []
                names = [f"MONSTER{i}" for i in range(1, 17)]
                for i in range(1, 17):
                    name = names[i-1]
                    lvl = 8 + i * 2
                    max_hp = 60 + i * 10
                    pool.append({
                        'name': name,
                        'level': lvl,
                        'max_hp': max_hp,
                        'hp': max_hp,
                        'sprite_path': get_menu_sprite_path(i),
                    })
                manager.wild_pool = pool
            except Exception:
                manager.wild_pool = []

        Logger.info("New game created from default state")
        return manager

    # ------------------------------------------------------
    # CONVERT JSON → GAME STATE
    # ------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "GameManager":
        from src.maps.map import Map
        from src.entities.player import Player
        from src.entities.enemy_trainer import EnemyTrainer
        from src.data.bag import Bag

        maps: dict[str, Map] = {}
        trainers: dict[str, list[EnemyTrainer]] = {}

        maps_data = data["map"]

        for entry in maps_data:
            path = entry["path"]
            maps[path] = Map.from_dict(entry)
            trainers[path] = []

        current_map = data["current_map"]

        bag = Bag.from_dict(data.get("bag", {}))

        gm = cls(
            maps=maps,
            start_map=current_map,
            player=None,
            enemy_trainers=trainers,
            bag=bag,
        )

        for entry in maps_data:
            path = entry["path"]
            raw_list = entry.get("enemy_trainers", [])
            gm.enemy_trainers[path] = [
                EnemyTrainer.from_dict(t, gm) for t in raw_list
            ]

        if data.get("player"):
            gm.player = Player.from_dict(data["player"], gm)

        return gm

    # ------------------------------------------------------
    # COPY GAME STATE
    # ------------------------------------------------------
    def copy_from(self, other: "GameManager") -> None:
        self.current_map_key = other.current_map_key
        self.maps = other.maps
        self.enemy_trainers = other.enemy_trainers
        for key, trainers in self.enemy_trainers.items():
            for t in trainers:
                try:
                    t.game_manager = self
                except Exception:
                    pass
        self.bag = other.bag

        if other.player:
            from src.entities.player import Player

            self.player = Player(
                other.player.position.x,
                other.player.position.y,
                self,
            )
        else:
            self.player = None