import pygame as pg
import json
from src.utils import GameSettings
from src.utils.definition import Monster, Item


class Bag:
    _monsters_data: list[Monster]
    _items_data: list[Item]

    def __init__(self, monsters_data: list[Monster] | None = None, items_data: list[Item] | None = None):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []

    def update(self, dt: float):
        pass

    def draw(self, screen: pg.Surface):
        pass

    def to_dict(self) -> dict[str, object]:
        return {
            "monsters": list(self._monsters_data),
            "items": list(self._items_data)
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        monsters = data.get("monsters") or []
        items = data.get("items") or []
        bag = cls(monsters, items)
        return bag

    # ★★★ 新增：取得金幣數量 ★★★
    def get_coins(self) -> int:
        for item in self._items_data:
            # 確保 item 是字典型態 (JSON 載入後通常是 dict)
            if isinstance(item, dict):
                if item.get("name") == "Coins":
                    return int(item.get("count", 0))
        return 0

    # ★★★ 新增：增加/減少金幣 ★★★
    def add_coins(self, amount: int) -> None:
        found = False
        for item in self._items_data:
            if isinstance(item, dict) and item.get("name") == "Coins":
                current = int(item.get("count", 0))
                # 確保金幣不小於 0
                item["count"] = max(0, current + amount)
                found = True
                break
        
        # 如果背包裡還沒有 Coins 這個項目（雖然通常會有），則新增一個
        if not found and amount > 0:
            self._items_data.append({
                "name": "Coins",
                "count": amount,
                "sprite_path": "ingame_ui/coin.png",
                "option": 0
            })