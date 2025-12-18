from enum import Enum
from dataclasses import dataclass
import random


class BattleAction(Enum):
    ATTACK = "attack"
    RUN_AWAY = "run_away"


@dataclass
class BattleState:
    player_hp: float
    player_max_hp: float
    enemy_hp: float
    enemy_max_hp: float
    is_player_turn: bool
    battle_log: list[str]
    player_level: int = 1
    enemy_level: int = 1
    player_element: str = "non"
    enemy_element: str = "non"
    player_atk: int = 10
    enemy_atk: int = 10
    shield_active: bool = False
    field_id: int = 1  # 1: Forest, 2: Beach, 3: Snow
    
    # ★★★ 新增藥水狀態 ★★★
    strength_up: bool = False
    defense_up: bool = False

    def add_log(self, message: str) -> None:
        self.battle_log.append(message)


class BattleSystem:
    """
    Turn-based battle system with Elemental Logic, Level Bonus, Field Effects, and Potions.
    """

    def __init__(
        self, 
        player_max_hp: float = 100, 
        enemy_max_hp: float = 50, 
        player_level: int = 1, 
        enemy_level: int = 1,
        player_element: str = "non",
        enemy_element: str = "non",
        player_atk: int = 10,
        enemy_atk: int = 10,
        field_id: int = 1
    ):
        self.player_max_hp = player_max_hp
        self.enemy_max_hp = enemy_max_hp
        self.player_level = player_level
        self.enemy_level = enemy_level
        
        self.state = BattleState(
            player_hp=player_max_hp,
            player_max_hp=player_max_hp,
            enemy_hp=enemy_max_hp,
            enemy_max_hp=enemy_max_hp,
            is_player_turn=True,
            battle_log=[],
            player_level=player_level,
            enemy_level=enemy_level,
            player_element=player_element,
            enemy_element=enemy_element,
            player_atk=player_atk,
            enemy_atk=enemy_atk,
            shield_active=False,
            field_id=field_id,
            strength_up=False,
            defense_up=False
        )

    # ------------------------------
    # Helper: Check Elemental Advantage
    # ------------------------------
    def check_elemental_advantage(self, attacker_elem: str, defender_elem: str) -> float:
        """
        Returns multiplier: 1.5 (Strong), 1.0 (Neutral)
        """
        if attacker_elem in ["light", "non"] or defender_elem in ["light", "non"]:
            return 1.0
        
        if attacker_elem == "water" and defender_elem == "fire":
            return 1.5
        elif attacker_elem == "fire" and defender_elem == "grass":
            return 1.5
        elif attacker_elem == "grass" and defender_elem == "water":
            return 1.5
        elif attacker_elem == "fire" and defender_elem == "ice":
            return 1.5
        elif attacker_elem == "ice" and defender_elem == "fire":
            return 1.5
        
        return 1.0

    # ------------------------------
    # Helper: Calculate Attack Components
    # ------------------------------
    def get_atk_breakdown(self, is_player: bool) -> tuple[int, int, int]:
        """
        Returns (base_atk, level_bonus, terrain_bonus)
        """
        if is_player:
            base_atk = self.state.player_atk
            my_level = self.state.player_level
            opp_level = self.state.enemy_level
            element = self.state.player_element
        else:
            base_atk = self.state.enemy_atk
            my_level = self.state.enemy_level
            opp_level = self.state.player_level
            element = self.state.enemy_element

        # 1. Level Bonus
        level_bonus = 0
        if my_level > opp_level:
            level_bonus = (my_level - opp_level) * 10
        
        # 2. Field Bonus
        field = self.state.field_id
        terrain_bonus = 0
        
        if field == 1: # Forest
            if element == "grass": terrain_bonus = int(base_atk * 0.5)
            elif element == "water": terrain_bonus = -int(base_atk * 0.5)
        elif field == 2: # Beach
            if element in ["fire", "light", "non"]: terrain_bonus = int(base_atk * 0.5)
            elif element in ["water", "ice", "grass"]: terrain_bonus = -int(base_atk * 0.5)
        elif field == 3: # Snow
            if element in ["water", "ice"]: terrain_bonus = int(base_atk * 0.5)
            elif element in ["fire", "non", "light"]: terrain_bonus = -int(base_atk * 0.5)

        return base_atk, level_bonus, terrain_bonus

    # ------------------------------
    # Player actions
    # ------------------------------
    def player_attack(self) -> dict:
        if not self.state.is_player_turn:
            return {"success": False, "message": ""}

        # 1. Get Base Effective Attack
        base, lv_bonus, field_bonus = self.get_atk_breakdown(is_player=True)
        effective_atk = base + lv_bonus + field_bonus
        
        # ★★★ Strength Potion Logic ★★★
        # 使用 Strength Potion 後，總攻擊力 * 1.2
        if self.state.strength_up:
            effective_atk = int(effective_atk * 1.2)
        
        # 2. Apply Elemental Multiplier
        multiplier = self.check_elemental_advantage(
            self.state.player_element, 
            self.state.enemy_element
        )
        
        final_damage = int(effective_atk * multiplier)
        
        msg_parts = []
        if self.state.strength_up:
            msg_parts.append("STR Up!")
        if multiplier > 1.0:
            msg_parts.append("Super effective!")
        
        prefix = " ".join(msg_parts) if msg_parts else "Hit."
        
        self.state.enemy_hp = max(0, self.state.enemy_hp - final_damage)

        # Check enemy defeat
        if self.state.enemy_hp <= 0:
            return {
                "success": True,
                "message": f"{prefix} Dealt {final_damage} dmg!",
                "damage": final_damage,
                "battle_end": True,
                "winner": "player",
            }

        self.state.is_player_turn = False
        return {
            "success": True,
            "message": f"{prefix} Dealt {final_damage} dmg!",
            "damage": final_damage,
            "battle_end": False,
        }

    # ------------------------------
    # Enemy action
    # ------------------------------
    def enemy_attack(self) -> dict:
        if self.state.is_player_turn:
            return {"success": False, "message": ""}

        if self.state.shield_active:
            self.state.shield_active = False
            self.state.is_player_turn = True 
            return {
                "success": True,
                "message": "shield_blocked",
                "damage": 0,
                "battle_end": False,
            }

        # 1. Get Effective Attack Power
        base, lv_bonus, field_bonus = self.get_atk_breakdown(is_player=False)
        effective_atk = base + lv_bonus + field_bonus

        # ★★★ Defense Potion Logic ★★★
        # 使用 Defense Potion 後，敵方總攻擊力 * 0.8 (受傷減少)
        if self.state.defense_up:
            effective_atk = int(effective_atk * 0.8)

        # 2. Apply Elemental Multiplier
        multiplier = self.check_elemental_advantage(
            self.state.enemy_element, 
            self.state.player_element
        )
        
        final_damage = int(effective_atk * multiplier)
        
        msg_parts = []
        if self.state.defense_up:
            msg_parts.append("DEF Up!")
        if multiplier > 1.0:
            msg_parts.append("Super effective!")
            
        msg = " ".join(msg_parts) if msg_parts else "Hit."

        self.state.player_hp = max(0, self.state.player_hp - final_damage)

        if self.state.player_hp <= 0:
            return {
                "success": True,
                "message": f"{msg} Took {final_damage} dmg!",
                "damage": final_damage,
                "battle_end": True,
                "winner": "enemy",
            }

        self.state.is_player_turn = True
        return {
            "success": True,
            "message": f"{msg} Took {final_damage} dmg!",
            "damage": final_damage,
            "battle_end": False,
        }

    # ------------------------------
    # Accessors & Mutators
    # ------------------------------
    def get_state(self) -> BattleState:
        return self.state

    def switch_player_pokemon(self, new_player_hp: float, new_player_max_hp: float, new_element: str, new_atk: int, new_level: int) -> None:
        """Switch to a new pokemon (updates player HP, Element, Atk, and Level)."""
        self.player_max_hp = new_player_max_hp
        self.state.player_max_hp = new_player_max_hp
        self.state.player_hp = new_player_hp
        
        self.state.player_element = new_element
        self.state.player_atk = new_atk
        self.state.player_level = new_level
        # Switch 時藥水效果通常會繼承或消失，這裡假設繼承 (不重置 strength_up/defense_up)