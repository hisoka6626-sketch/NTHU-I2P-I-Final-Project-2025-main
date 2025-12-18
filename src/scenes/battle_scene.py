import pygame as pg
import re
import os
import random
import math

from src.scenes.scene import Scene
from src.sprites import BackgroundSprite, Sprite
from src.interface.components import Button, PokemonSwitchPanel
from src.interface.components.item_panel import ItemPanel
from src.core.services import scene_manager, sound_manager, input_manager
from src.core.battle_system import BattleSystem
from src.utils import GameSettings, Logger, Position
from src.utils.definition import get_menu_sprite_path
from typing import override

# ==========================================
# Attack Effect Class
# ==========================================
class AttackEffect(pg.sprite.Sprite):
    def __init__(self, element: str, start_pos: tuple[int, int], target_pos: tuple[int, int], scale: int = 3):
        super().__init__()
        self.element = element
        self.pos = pg.math.Vector2(start_pos)
        self.target = pg.math.Vector2(target_pos)
        self.speed = 700  # Flight speed
        self.scale = scale
        
        self.raw_frames = self._load_frames(element)
        
        direction = self.target - self.pos
        angle = math.degrees(math.atan2(-direction.y, direction.x))
        
        self.rotated_frames = []
        for f in self.raw_frames:
            self.rotated_frames.append(pg.transform.rotate(f, angle))
            
        self.frame_index = 0
        if self.rotated_frames:
            self.image = self.rotated_frames[self.frame_index]
        else:
            self.image = pg.Surface((10,10))
            
        self.rect = self.image.get_rect(center=self.pos)
        self.animation_timer = 0.0
        self.animation_speed = 0.08

    def _load_frames(self, element: str) -> list[pg.Surface]:
        filename = f"{element}.png"
        path = os.path.join("assets", "images", "attack", filename)
        frames = []
        
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Image not found: {path}")

            sheet = pg.image.load(path).convert_alpha()
            sheet_w = sheet.get_width()
            sheet_h = sheet.get_height()
            n_frames = max(1, sheet_w // sheet_h)
            frame_w = sheet_w // n_frames
            frame_h = sheet_h
            
            for i in range(n_frames):
                rect = pg.Rect(i * frame_w, 0, frame_w, frame_h)
                frame = sheet.subsurface(rect)
                scaled_w = int(frame_w * self.scale)
                scaled_h = int(frame_h * self.scale)
                frame = pg.transform.scale(frame, (scaled_w, scaled_h))
                frames.append(frame)
                
        except Exception as e:
            fallback = pg.Surface((40, 40), pg.SRCALPHA)
            pg.draw.circle(fallback, (255, 255, 255, 200), (20, 20), 15)
            pg.draw.circle(fallback, (255, 255, 255), (20, 20), 10)
            frames = [fallback]
            
        return frames

    def update(self, dt: float):
        direction = self.target - self.pos
        distance = direction.length()
        
        if distance < 25:
            self.kill()
            return
            
        if distance > 0:
            direction = direction.normalize()
            self.pos += direction * self.speed * dt
            self.rect.center = (int(self.pos.x), int(self.pos.y))
        
        if len(self.rotated_frames) > 1:
            self.animation_timer += dt
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0.0
                self.frame_index = (self.frame_index + 1) % len(self.rotated_frames)
                self.image = self.rotated_frames[self.frame_index]
                self.rect = self.image.get_rect(center=self.rect.center)


# ==========================================
# Battle Sprite Class
# ==========================================
class BattleSprite(pg.sprite.Sprite):
    def __init__(self, monster_id: int, x: int, y: int, is_enemy: bool = False, scale: int = 4):
        super().__init__()
        self.monster_id = monster_id
        self.is_enemy = is_enemy
        self.scale = scale
        self.pos = Position(x, y)
        
        self.state = "idle" 
        self.frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.15 
        
        self.images = {
            "idle": self._load_sprite_sheet(f"sprite{monster_id}_idle.png"),
            "attack": self._load_sprite_sheet(f"sprite{monster_id}_attack.png")
        }
        
        if not self.images["idle"]:
             fallback = pg.Surface((64, 64))
             fallback.fill((255, 0, 255))
             self.image = fallback
        else:
            self.image = self.images["idle"][0]
            
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def _load_sprite_sheet(self, filename: str) -> list[pg.Surface]:
        path = os.path.join("assets", "images", "sprites", filename)
        frames = []
        try:
            if not os.path.exists(path):
                return []

            sheet = pg.image.load(path).convert_alpha()
            frame_count = 4
            sheet_width = sheet.get_width()
            sheet_height = sheet.get_height()
            frame_width = sheet_width // frame_count
            frame_height = sheet_height
            
            for i in range(frame_count):
                rect = pg.Rect(i * frame_width, 0, frame_width, frame_height)
                frame = sheet.subsurface(rect)
                frame = pg.transform.scale(frame, (frame_width * self.scale, frame_height * self.scale))
                if self.is_enemy:
                    frame = pg.transform.flip(frame, True, False)
                frames.append(frame)
        except Exception as e:
            Logger.error(f"Failed to load sprite sheet {filename}: {e}")
            frames = []
            
        if not frames:
            fallback = pg.Surface((64, 64))
            fallback.fill((255, 0, 255))
            frames = [fallback] * 4
            
        return frames

    def play_attack(self):
        if self.state != "attack":
            self.state = "attack"
            self.frame_index = 0
            self.animation_timer = 0.0

    def update(self, dt: float):
        self.animation_timer += dt
        current_frames = self.images.get(self.state, self.images["idle"])
        
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.frame_index += 1
            if self.frame_index >= len(current_frames):
                if self.state == "attack":
                    self.state = "idle"
                    self.frame_index = 0
                else:
                    self.frame_index = 0
        
        idx = self.frame_index % len(current_frames)
        self.image = current_frames[idx]
        self.rect = self.image.get_rect()
        self.rect.center = (self.pos.x, self.pos.y)

    def draw(self, screen: pg.Surface, outline_color: tuple[int, int, int] | None = None):
        if outline_color:
            mask = pg.mask.from_surface(self.image)
            mask_surf = mask.to_surface(setcolor=outline_color, unsetcolor=(0, 0, 0, 0))
            for ox in [-2, 2]:
                for oy in [-2, 2]:
                    screen.blit(mask_surf, (self.rect.x + ox, self.rect.y + oy))
        screen.blit(self.image, self.rect)

    def update_pos(self, pos: Position):
        self.pos = pos
        self.rect.center = (pos.x, pos.y)


class BattleScene(Scene):
    def __init__(self):
        super().__init__()

        self.background = None 
        # 載入暗黑背景
        self.bg_dark_raw = pg.image.load("assets/images/backgrounds/dark map battle background.webp").convert()
        self.bg_dark = pg.transform.scale(self.bg_dark_raw, (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        
        self.player_sprite = BattleSprite(1, int(GameSettings.SCREEN_WIDTH * 0.30), int(GameSettings.SCREEN_HEIGHT * 0.54), is_enemy=False)
        self.enemy_sprite = BattleSprite(3, int(GameSettings.SCREEN_WIDTH * 0.64), int(GameSettings.SCREEN_HEIGHT * 0.28), is_enemy=True)
        self.player_mon = None 
        self.enemy_mon = None
        
        self.effect_sprites = pg.sprite.Group()
        self.switch_panel = None
        self.item_panel = None

        self.pokeball_animating = False
        self.pokeball_anim_frame = 0
        self.pokeball_pos = None
        self.pokeball_target = None
        self.baricon_animating = False
        self.baricon_anim_frame = 0
        self.baricon_icons = []
        self.baricon_type = None
        self.capture_result = None
        self.capture_text_timer = 0
        
        self.showing_battle_result = False
        self.battle_result_message = ""
        self.result_text_timer = 0.0
        self.battle_result = None 
        
        # 警告訊息用 (不能逃跑/不能捕捉)
        self.warning_msg_timer = 0.0
        self.warning_msg_text = ""

        self.battle_system = BattleSystem()
        self.action_pending = False
        self._enemy_action_timer = 0.0
        self._enemy_action_delay = 0.9 
        
        # 暗黑戰鬥旗標
        self.is_dark_battle = False
        
        # 持續扣血計時器
        self._dark_damage_timer = 0.0
        
        # 紅光閃爍特效
        self._red_flash_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)).convert_alpha()
        self._red_flash_surf.fill((255, 0, 0))
        self._red_flash_alpha = 0

        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 36) 
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
        self.font_btn = pg.font.Font("assets/fonts/Minecraft.ttf", 18)

        banner_raw = pg.image.load("assets/images/UI/raw/UI_Flat_Banner03a.png").convert_alpha()
        self.banner_size = (280, 80)
        self.banner = pg.transform.smoothscale(banner_raw, self.banner_size)

        panel_height = 120
        panel_top = GameSettings.SCREEN_HEIGHT - panel_height
        btn_width = 150
        btn_height = 55
        gap = 20
        total_w = 4 * btn_width + 3 * gap
        start_x = (GameSettings.SCREEN_WIDTH - total_w) // 2
        btn_y = panel_top + 50

        def make_btn(label, x, callback):
            return Button(
                img_path="UI/raw/UI_Flat_Button02a_4.png",
                img_hovered_path="UI/raw/UI_Flat_Button02a_3.png",
                x=x, y=btn_y, width=btn_width, height=btn_height,
                on_click=callback, label=label, font=self.font_btn,
            )

        self.btn_fight = make_btn("Fight", start_x, self._player_attack)
        self.btn_item = make_btn("Item", start_x + (btn_width + gap), self._player_use_item_placeholder)
        self.btn_switch = make_btn("Switch", start_x + 2 * (btn_width + gap), self._player_switch_pokemon)
        self.btn_run = make_btn("Run", start_x + 3 * (btn_width + gap), self._player_run_away)

        self.btn_close = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            GameSettings.SCREEN_WIDTH - 48, 8, 40, 40,
            lambda: scene_manager.change_scene("game"),
        )

    def _get_monster_id(self, sprite_path: str) -> int:
        try:
            match = re.search(r'(\d+)', sprite_path)
            if match: return int(match.group(1))
        except: pass
        return 1

    def _get_element(self, sprite_id: int) -> str:
        if sprite_id in [1, 2, 3, 15, 16]: return "grass"
        elif sprite_id in [7, 8, 9]: return "fire"
        elif sprite_id in [12, 13, 14]: return "water"
        elif sprite_id == 6: return "ice"
        elif sprite_id in [10, 11]: return "light"
        return "non"

    @override
    def enter(self) -> None:
        # 1. 判斷是否為暗黑戰鬥
        game_scene = scene_manager._scenes.get("game")
        if game_scene:
            self.is_dark_battle = getattr(game_scene.game_manager, "is_dark_battle", False)
        else:
            self.is_dark_battle = False
            
        # 2. 播放音樂
        if self.is_dark_battle:
            # ★★★ 修改：暗黑戰鬥使用 horror-thriller-action-247745.mp3 ★★★
            sound_manager.play_bgm("horror-thriller-action-247745.mp3") 
        else:
            sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        
        # 3. 設定背景 (如果是正常戰鬥)
        if not self.is_dark_battle:
            field_id = random.randint(1, 3)
            self.background = BackgroundSprite(f"backgrounds/background{field_id}.png")
            Logger.info(f"Battle started on Field ID: {field_id}")
        else:
            Logger.info("Battle started in Dark World!")
        
        self.effect_sprites.empty()
        self._dark_damage_timer = 0.0
        self._red_flash_alpha = 0
        self.warning_msg_timer = 0.0

        # 4. 初始化玩家寶可夢
        gm = None
        try:
            if game_scene and hasattr(game_scene, "game_manager"):
                gm = game_scene.game_manager
                if gm.bag._monsters_data:
                    selected_mon = None
                    for mon in gm.bag._monsters_data:
                        if not mon.get('is_dead', False) and mon.get('hp', 0) > 0:
                            selected_mon = mon
                            break
                    if selected_mon is None:
                        selected_mon = gm.bag._monsters_data[0]
                    self.player_mon = selected_mon
                    p_id = self._get_monster_id(self.player_mon["sprite_path"])
                    self.player_sprite = BattleSprite(p_id, int(GameSettings.SCREEN_WIDTH * 0.30), int(GameSettings.SCREEN_HEIGHT * 0.54), is_enemy=False)
        except Exception as e:
            Logger.error(f"Failed to init player: {e}")

        # 5. 初始化敵人 (包含暗黑強化)
        try:
            p_max = self.player_mon.get('max_hp', 100) if self.player_mon else 100
            p_hp = self.player_mon.get('hp', 100) if self.player_mon else 100
            p_lv = self.player_mon.get('level', 1) if self.player_mon else 1
            p_atk = self.player_mon.get('attack', 10) if self.player_mon else 10
            p_elem = self._get_element(self._get_monster_id(self.player_mon["sprite_path"])) if self.player_mon else "non"

            e_lv = 1
            if gm and hasattr(gm.bag, '_monsters_data') and gm.bag._monsters_data:
                levels = [m.get('level', 1) for m in gm.bag._monsters_data]
                if levels:
                    e_lv = random.randint(min(levels), max(levels) + 5)
            
            e_max = e_lv * 100
            e_hp = e_max
            e_atk = e_lv * 10

            # 暗黑強化：HP 與 ATK 1.5 倍
            if self.is_dark_battle:
                e_max = int(e_max * 1.5)
                e_hp = e_max
                e_atk = int(e_atk * 1.5)

            candidates = getattr(gm, 'wild_pool', None) or getattr(gm.bag, '_monsters_data', []) or []
            fallback = [{'name': 'WildEnemy', 'sprite_path': "menu_sprites/menusprite3.png"}]
            pool = candidates if candidates else fallback
            choice_template = random.choice(pool)
            
            self.enemy_mon = {
                'name': choice_template.get('name', 'WildEnemy'),
                'level': e_lv,
                'max_hp': e_max,
                'hp': e_hp,
                'attack': e_atk,
                'sprite_path': choice_template.get('sprite_path', "menu_sprites/menusprite3.png")
            }

            e_id = self._get_monster_id(self.enemy_mon['sprite_path'])
            e_elem = self._get_element(e_id)
            
            self.enemy_sprite = BattleSprite(e_id, int(GameSettings.SCREEN_WIDTH * 0.64), int(GameSettings.SCREEN_HEIGHT * 0.28), is_enemy=True)

            self.battle_system = BattleSystem(
                player_max_hp=p_max, 
                enemy_max_hp=e_max,
                player_level=p_lv,
                enemy_level=e_lv,
                player_element=p_elem,
                enemy_element=e_elem,
                player_atk=p_atk,
                enemy_atk=e_atk,
                field_id=1 
            )
            self.battle_system.state.player_hp = p_hp
            self.battle_system.state.enemy_hp = e_hp
            
            self.battle_system.state.is_player_turn = True
            self.action_pending = False
            self._enemy_action_timer = 0.0
            
            self.pokeball_animating = False
            self.baricon_animating = False
            self.showing_battle_result = False
                
        except Exception as e:
            Logger.error(f"Failed to init battle: {e}")

    def _spawn_attack_effect(self, is_player: bool):
        element = self.battle_system.state.player_element if is_player else self.battle_system.state.enemy_element
        if is_player:
            start_pos = self.player_sprite.rect.center
            target_pos = self.enemy_sprite.rect.center
        else:
            start_pos = self.enemy_sprite.rect.center
            target_pos = self.player_sprite.rect.center
        effect = AttackEffect(element, start_pos, target_pos)
        self.effect_sprites.add(effect)

    @override
    def update(self, dt: float) -> None:
        state = self.battle_system.get_state()

        self.player_sprite.update(dt)
        self.enemy_sprite.update(dt)
        self.effect_sprites.update(dt)

        # 暗黑戰鬥持續扣血邏輯
        if self.is_dark_battle and state.player_hp > 0 and not self.showing_battle_result:
            self._dark_damage_timer += dt
            if self._dark_damage_timer >= 1.5:
                self._dark_damage_timer = 0.0
                damage = 100
                state.player_hp -= damage
                self._red_flash_alpha = 180 # 觸發紅光
                Logger.info(f"[Dark] Environment damage! Player took {damage} dmg.")
                
                # 如果扣到死
                if state.player_hp <= 0:
                    state.player_hp = 0
                    self.showing_battle_result = True
                    self.battle_result_message = "YOU DIED"
                    self.battle_result = 'lose'
                    self.result_text_timer = 2.0
                    self.action_pending = False

        # 紅光淡出
        if self._red_flash_alpha > 0:
            self._red_flash_alpha -= dt * 500
            if self._red_flash_alpha < 0: self._red_flash_alpha = 0

        # 警告訊息計時
        if self.warning_msg_timer > 0:
            self.warning_msg_timer -= dt

        if self.showing_battle_result:
            self.result_text_timer -= dt
            if self.result_text_timer <= 0:
                self._save_and_return()
                return

        if self.switch_panel: self.switch_panel.update(dt)
        if self.item_panel and self.item_panel.is_open: self.item_panel.update(dt, input_manager)
        self.btn_close.update(dt)

        if state.is_player_turn and not self.action_pending:
            self.btn_fight.update(dt)
            self.btn_item.update(dt)
            self.btn_switch.update(dt)
            self.btn_run.update(dt)

        if self.action_pending and not state.is_player_turn:
            self._enemy_action_timer += dt
            if self._enemy_action_timer >= self._enemy_action_delay:
                self.enemy_sprite.play_attack()
                self._spawn_attack_effect(is_player=False)
                
                result = self.battle_system.enemy_attack()
                Logger.info(result.get("message", ""))

                if result.get("message") == "shield_blocked":
                    state.is_player_turn = True
                    self.action_pending = False
                    self._enemy_action_timer = 0.0
                    return

                if state.player_hp <= 0:
                    self.showing_battle_result = True
                    self.battle_result_message = "YOU LOSE"
                    self.battle_result = 'lose'
                    self.result_text_timer = 2.0
                    self.action_pending = False
                    self._enemy_action_timer = 0.0
                    return

                if result.get("battle_end"):
                    self._end_battle_and_return()
                    return

                self.action_pending = False
                self._enemy_action_timer = 0.0

    def _player_attack(self):
        if self.action_pending: return
        state = self.battle_system.get_state()
        if not state.is_player_turn: return

        self.player_sprite.play_attack()
        self._spawn_attack_effect(is_player=True)
        
        result = self.battle_system.player_attack()
        Logger.info(result.get("message", ""))

        if result.get("battle_end"):
            self._end_battle_and_return()
            return

        self.action_pending = True
        self._enemy_action_timer = 0.0

    def _player_switch_pokemon(self):
        if self.action_pending: return
        if self.switch_panel is None:
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, "game_manager"):
                self.switch_panel = PokemonSwitchPanel(game_scene.game_manager)
        if self.switch_panel:
            self.switch_panel.open(callback=self._on_pokemon_selected)

    def _on_pokemon_selected(self, pokemon_index: int):
        game_scene = scene_manager._scenes.get("game")
        if not game_scene: return
        gm = game_scene.game_manager
        monsters = gm.bag._monsters_data
        
        if pokemon_index < 0 or pokemon_index >= len(monsters): return

        if self.player_mon:
            current_combat_hp = self.battle_system.state.player_hp
            for monster in monsters:
                if monster.get('name') == self.player_mon.get('name'):
                    monster['hp'] = max(0, int(current_combat_hp))
                    break

        self.player_mon = monsters[pokemon_index]
        p_id = self._get_monster_id(self.player_mon["sprite_path"])
        p_elem = self._get_element(p_id)
        p_atk = self.player_mon.get('attack', 10)
        p_lv = self.player_mon.get('level', 1)

        self.player_sprite = BattleSprite(p_id, int(GameSettings.SCREEN_WIDTH * 0.30), int(GameSettings.SCREEN_HEIGHT * 0.54), is_enemy=False)

        self.battle_system.switch_player_pokemon(
            new_player_hp=self.player_mon["hp"],
            new_player_max_hp=self.player_mon["max_hp"],
            new_element=p_elem,
            new_atk=p_atk,
            new_level=p_lv
        )

        Logger.info(f"Switched to {self.player_mon['name']}!")
        if self.switch_panel: self.switch_panel.close()

    def _player_run_away(self):
        if self.action_pending: return
        state = self.battle_system.get_state()
        if not state.is_player_turn: return
        
        # 暗黑模式：禁止逃跑
        if self.is_dark_battle:
            self.warning_msg_text = "YOU CAN NOT RUN AWAY"
            self.warning_msg_timer = 2.0
            return

        self.battle_result = 'run'
        self._save_and_return()

    def _player_use_item_placeholder(self):
        game_scene = scene_manager._scenes.get("game")
        if game_scene:
            gm = game_scene.game_manager
            items = gm.bag._items_data
            if self.item_panel is None:
                self.item_panel = ItemPanel(items, callback=self._on_item_selected)
            else:
                self.item_panel.items = items
                self.item_panel.open(callback=self._on_item_selected)
            self.item_panel.open(callback=self._on_item_selected)

    def _on_item_selected(self, item_index: int):
        state = self.battle_system.get_state()
        game_scene = scene_manager._scenes.get("game")
        if game_scene:
            gm = game_scene.game_manager
            items = gm.bag._items_data
            if 0 <= item_index < len(items):
                item = items[item_index]
                name = item.get('name', '')
                option = item.get('option', None)
                
                # 暗黑模式：禁止使用精靈球
                if (name == "Pokeball" or option == 1):
                    if self.is_dark_battle:
                        self.warning_msg_text = "YOU CAN NOT CATCH IT"
                        self.warning_msg_timer = 2.0
                        if self.item_panel: self.item_panel.close()
                        return
                    else:
                        self._start_pokeball_animation()
                        self._consume_item(items, item_index, close_panel=False) 
                        if self.item_panel: self.item_panel.items = items
                        return

                if name == "Magic Hand" or option == 8:
                    if self.is_dark_battle: # Magic Hand 也不能抓
                        self.warning_msg_text = "YOU CAN NOT CATCH IT"
                        self.warning_msg_timer = 2.0
                        if self.item_panel: self.item_panel.close()
                        return
                    self._add_enemy_to_bag(gm)
                    self._consume_item(items, item_index)
                    self._end_battle_with_victory()
                    return
                elif name == "Shield" or option == 6:
                    self.battle_system.state.shield_active = True
                    Logger.info("Used Shield!")
                    self._consume_item(items, item_index)
                    return
                elif name == "Potion" or option == 2:
                    if self.player_mon:
                        heal = int(self.player_mon['max_hp'] * 0.2)
                        new = min(self.player_mon['hp'] + heal, self.player_mon['max_hp'])
                        self.player_mon['hp'] = new
                        self.battle_system.state.player_hp = new
                        Logger.info(f"Used Potion! Healed {heal} HP.")
                    self._consume_item(items, item_index)
                    return
                elif name == "Strength Potion" or option == 3:
                    self.battle_system.state.strength_up = True
                    Logger.info("Used Strength Potion! Attack boosted.")
                    self._consume_item(items, item_index)
                    return
                elif name == "Defense Potion" or option == 4:
                    self.battle_system.state.defense_up = True
                    Logger.info("Used Defense Potion! Defense boosted.")
                    self._consume_item(items, item_index)
                    return

    def _consume_item(self, items, index, close_panel=True):
        items[index]['count'] -= 1
        if items[index]['count'] <= 0:
            items.pop(index)
        if self.item_panel:
            self.item_panel.items = items
            if close_panel:
                self.item_panel.close()

    def _add_enemy_to_bag(self, gm):
        enemy_info = {
            'name': self.enemy_mon.get('name', 'EnemyMon'),
            'level': self.enemy_mon.get('level', 1),
            'max_hp': self.enemy_mon.get('max_hp', 60),
            'hp': self.enemy_mon.get('max_hp', 60),
            'attack': self.enemy_mon.get('attack', 10),
            'exp': 0,
            'max_exp': (self.enemy_mon.get('level', 1) + 1) * 10,
            'sprite_path': self.enemy_mon.get('sprite_path', get_menu_sprite_path(3))
        }
        gm.bag._monsters_data.append(enemy_info)

    def _end_battle_and_return(self):
        self.showing_battle_result = True
        self.battle_result_message = "YOU WIN"
        self.battle_result = 'win'
        self.result_text_timer = 2.0
    
    def _end_battle_with_victory(self):
        self.showing_battle_result = True
        self.battle_result_message = "YOU WIN"
        self.battle_result = 'win'
        self.result_text_timer = 2.0

    def _save_and_return(self):
        if self.player_mon:
            try:
                final_hp = self.battle_system.state.player_hp
                game_scene = scene_manager._scenes.get("game")
                if game_scene:
                    gm = game_scene.game_manager
                    
                    target_monster = None
                    for monster in gm.bag._monsters_data:
                        if monster.get('name') == self.player_mon.get('name'):
                            monster['hp'] = max(0, int(final_hp))
                            if monster['hp'] <= 0: monster['is_dead'] = True
                            else: monster['is_dead'] = False
                            target_monster = monster
                            break
                    
                    if self.battle_result == 'win':
                        found = False
                        for item in gm.bag._items_data:
                            if item['name'] == 'Coins':
                                item['count'] += 10
                                found = True
                                break
                        
                        if target_monster and not target_monster.get('is_dead', False):
                            level = target_monster.get('level', 1)
                            if 'max_exp' not in target_monster:
                                target_monster['max_exp'] = (level + 1) * 10
                            if 'exp' not in target_monster:
                                target_monster['exp'] = 0
                                
                            exp_gain = int(target_monster['max_exp'] * 0.1)
                            target_monster['exp'] += exp_gain
                            Logger.info(f"{target_monster['name']} gained {exp_gain} EXP!")

                            EVO_STAGE_1 = {1, 7, 12}
                            EVO_STAGE_2 = {2, 8, 13}
                            
                            mid = self._get_monster_id(target_monster['sprite_path'])

                            while target_monster['exp'] >= target_monster['max_exp']:
                                current_lvl = target_monster['level']
                                is_capped = False
                                
                                if current_lvl == 29 and mid in EVO_STAGE_1:
                                    is_capped = True
                                elif current_lvl == 49 and mid in EVO_STAGE_2:
                                    is_capped = True
                                
                                if is_capped:
                                    target_monster['exp'] = target_monster['max_exp']
                                    Logger.info(f"{target_monster['name']} is ready to evolve! (Level capped)")
                                    break
                                
                                target_monster['exp'] -= target_monster['max_exp']
                                target_monster['level'] += 1
                                
                                new_lvl = target_monster['level']
                                target_monster['max_exp'] = (new_lvl + 1) * 10
                                target_monster['max_hp'] = new_lvl * 100
                                target_monster['attack'] = new_lvl * 10
                                target_monster['hp'] += 100 
                                
                                Logger.info(f"{target_monster['name']} grew to Lv.{new_lvl}!")

            except Exception as e:
                Logger.error(f"Save error: {e}")
        scene_manager.change_scene("game")

    def _start_pokeball_animation(self):
        self.pokeball_animating = True
        self.pokeball_anim_frame = 0
        self.pokeball_pos = [int(GameSettings.SCREEN_WIDTH*0.3)+64, int(GameSettings.SCREEN_HEIGHT*0.62)+32]
        self.pokeball_target = [int(GameSettings.SCREEN_WIDTH*0.64)+64, int(GameSettings.SCREEN_HEIGHT*0.28)+32]
        self.baricon_animating = False; self.capture_result = None

    def _start_baricon_animation(self, success):
        self.baricon_animating = True; self.baricon_anim_frame = 0; self.baricon_icons = []
        self.baricon_type = 'baricon2' if success else 'baricon3_4'
        num = random.randint(4,5) if success else 6
        bx, by = int(GameSettings.SCREEN_WIDTH*0.64)+64, int(GameSettings.SCREEN_HEIGHT*0.28)+32
        for _ in range(num):
            self.baricon_icons.append((bx+random.randint(-40,40), by+random.randint(-40,40), random.choice([0,1])))
        self.capture_result = success; self.capture_text_timer = 0

    def _start_capture_text(self, success):
        self.capture_result = success; self.capture_text_timer = 120

    @override
    def draw(self, screen: pg.Surface) -> None:
        state = self.battle_system.get_state()
        
        # 1. 繪製背景 (正常或暗黑)
        if self.is_dark_battle:
            screen.blit(self.bg_dark, (0, 0))
        elif self.background:
            self.background.draw(screen)

        p_adv = self.battle_system.check_elemental_advantage(state.player_element, state.enemy_element)
        e_adv = self.battle_system.check_elemental_advantage(state.enemy_element, state.player_element)
        
        p_outline = None
        e_outline = None
        
        if p_adv > 1.0:
            p_outline = (0, 255, 0)
            e_outline = (255, 0, 0)
        elif e_adv > 1.0:
            e_outline = (0, 255, 0)
            p_outline = (255, 0, 0)

        # 暗黑模式：強制敵人使用黑色描邊，營造詭異感
        if self.is_dark_battle:
            e_outline = (0, 0, 0) 

        self.enemy_sprite.draw(screen, outline_color=e_outline)
        self.player_sprite.draw(screen, outline_color=p_outline)
        self.effect_sprites.draw(screen)
        
        self._draw_status(screen, False, GameSettings.SCREEN_WIDTH - self.banner_size[0] - 24, 20, state)
        self._draw_status(screen, True, 24, GameSettings.SCREEN_HEIGHT - self.banner_size[1] - 140, state)

        # Draw Bottom Panel
        panel_top = GameSettings.SCREEN_HEIGHT - 120
        pg.draw.rect(screen, (20, 20, 20), (0, panel_top, GameSettings.SCREEN_WIDTH, 120)) 
        pg.draw.line(screen, (255, 255, 255), (0, panel_top), (GameSettings.SCREEN_WIDTH, panel_top), 3) 

        pname = self.player_mon['name'] if self.player_mon else 'Player'
        prompt = f"What will {pname} do?" if state.is_player_turn else "Enemy is acting..."
        screen.blit(self.font_text.render(prompt, True, (255, 255, 255)), (24, panel_top + 20))
        
        if state.shield_active:
            screen.blit(self.font_small.render("YOU HAVE ONE SHIELD", True, (0, 200, 255)), (24, panel_top + 50))

        if state.is_player_turn and not self.action_pending:
            self.btn_fight.draw(screen)
            self.btn_item.draw(screen)
            self.btn_switch.draw(screen)
            self.btn_run.draw(screen)

        self.btn_close.draw(screen)
        if self.switch_panel: self.switch_panel.draw(screen)
        if self.item_panel and self.item_panel.is_open: self.item_panel.draw(screen)
        
        # 繪製警告訊息 (Cannot Run/Catch)
        if self.warning_msg_timer > 0:
            self._draw_result_overlay(screen, text=self.warning_msg_text, color=(255, 50, 50))

        # 繪製紅光閃爍 (扣血特效)
        if self._red_flash_alpha > 0:
            self._red_flash_surf.set_alpha(int(self._red_flash_alpha))
            screen.blit(self._red_flash_surf, (0, 0))

        if self.showing_battle_result:
            self._draw_result_overlay(screen)

        if self.pokeball_animating:
            img = pg.image.load("assets/images/ingame_ui/ball.png").convert_alpha()
            t = min(self.pokeball_anim_frame / 30.0, 1.0)
            x = int(self.pokeball_pos[0]*(1-t) + self.pokeball_target[0]*t)
            y = int(self.pokeball_pos[1]*(1-t) + self.pokeball_target[1]*t)
            screen.blit(pg.transform.scale(img, (32,32)), (x, y))
            self.pokeball_anim_frame += 1
            if self.pokeball_anim_frame > 30:
                self.pokeball_animating = False
                self._start_baricon_animation(random.random() < 0.4)
        
        if self.baricon_animating:
            icons = self.baricon_icons
            img1 = pg.image.load("assets/images/ingame_ui/baricon2.png").convert_alpha()
            img2 = pg.image.load("assets/images/ingame_ui/baricon3.png").convert_alpha()
            for idx, (bx, by, t) in enumerate(icons):
                if (self.baricon_anim_frame//10 + idx)%2 == 0:
                    screen.blit(pg.transform.scale(img1 if self.baricon_type=='baricon2' else img2, (24,24)), (bx, by))
            self.baricon_anim_frame += 1
            if self.baricon_anim_frame > 90:
                self.baricon_animating = False
                self._start_capture_text(self.capture_result)
        
        if self.capture_text_timer > 0:
            self._draw_result_overlay(screen, "Captured!" if self.capture_result else "Failed", (0, 255, 0) if self.capture_result else (255, 0, 0))
            self.capture_text_timer -= 1
            if self.capture_text_timer == 0:
                if self.capture_result: self._add_enemy_to_bag(scene_manager._scenes.get("game").game_manager); self._end_battle_and_return()

    def _draw_result_overlay(self, screen, text=None, color=None):
        """Draws a cinematic overlay for results."""
        # 1. Darken Background
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(150)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        # 2. Draw Banner
        banner_h = 100
        banner_y = (GameSettings.SCREEN_HEIGHT - banner_h) // 2
        pg.draw.rect(screen, (0, 0, 0, 200), (0, banner_y, GameSettings.SCREEN_WIDTH, banner_h))
        pg.draw.line(screen, (255, 215, 0), (0, banner_y), (GameSettings.SCREEN_WIDTH, banner_y), 2) # Gold Line Top
        pg.draw.line(screen, (255, 215, 0), (0, banner_y + banner_h), (GameSettings.SCREEN_WIDTH, banner_y + banner_h), 2) # Gold Line Bottom

        # 3. Draw Text
        msg = text if text else self.battle_result_message
        col = color if color else ((0, 255, 0) if self.battle_result == 'win' else (255, 50, 50))
        
        # Shadow
        shadow_txt = self.font_title.render(msg, True, (0, 0, 0))
        txt = self.font_title.render(msg, True, col)
        
        cx = GameSettings.SCREEN_WIDTH // 2 - txt.get_width() // 2
        cy = GameSettings.SCREEN_HEIGHT // 2 - txt.get_height() // 2
        
        screen.blit(shadow_txt, (cx + 3, cy + 3))
        screen.blit(txt, (cx, cy))

    def _draw_status(self, screen, is_player, x, y, state):
        screen.blit(self.banner, (x, y))
        
        if is_player:
            name_txt = self.player_mon['name'] if self.player_mon else 'Player'
            level = state.player_level
            hp = state.player_hp
            max_hp = state.player_max_hp
        else:
            name_txt = self.enemy_mon.get('name', 'Enemy') if self.enemy_mon else 'Enemy'
            level = state.enemy_level
            hp = state.enemy_hp
            max_hp = state.enemy_max_hp

        screen.blit(self.font_text.render(str(name_txt), True, (0, 0, 0)), (x + 14, y + 8))
        screen.blit(self.font_small.render(f"Lv.{level}", True, (0, 0, 0)), (x + self.banner_size[0] - 70, y + 10))
        
        bar_x, bar_y = x + 14, y + 36
        bar_w = self.banner_size[0] - 40
        fill = int((hp / max_hp) * bar_w) if max_hp > 0 else 0
        
        # Rounded HP Bar Background
        pg.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_w, 14), border_radius=4)
        # HP Fill
        color = (0, 200, 0) if (hp/max_hp) > 0.5 else (255, 165, 0) if (hp/max_hp) > 0.2 else (255, 0, 0)
        if fill > 0:
            pg.draw.rect(screen, color, (bar_x, bar_y, fill, 14), border_radius=4)
        # Border
        pg.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, 14), 2, border_radius=4)
        
        screen.blit(self.font_small.render(f"{int(hp)}/{int(max_hp)}", True, (0, 0, 0)), (bar_x, bar_y + 18))

        base, lv_bonus, field_bonus = self.battle_system.get_atk_breakdown(is_player)
        
        atk_label = self.font_small.render("ATK:", True, (0, 0, 0))
        lx = bar_x + 90 
        ly = bar_y + 18
        screen.blit(atk_label, (lx, ly))
        
        base_surf = self.font_small.render(str(base), True, (0, 0, 0))
        screen.blit(base_surf, (lx + 40, ly))
        curr_x = lx + 40 + base_surf.get_width()
        
        if lv_bonus > 0:
            lv_surf = self.font_small.render(f"+{lv_bonus}", True, (0, 0, 255))
            screen.blit(lv_surf, (curr_x, ly))
            curr_x += lv_surf.get_width()
            
        if field_bonus != 0:
            color = (0, 150, 0) if field_bonus > 0 else (200, 0, 0)
            sign = "+" if field_bonus > 0 else ""
            field_surf = self.font_small.render(f"{sign}{field_bonus}", True, color)
            screen.blit(field_surf, (curr_x, ly))