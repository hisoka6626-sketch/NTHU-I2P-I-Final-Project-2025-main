import pygame as pg
from src.scenes.scene import Scene
from src.sprites import BackgroundSprite
from src.interface.components import Button
from src.core.services import scene_manager, resource_manager, input_manager
from src.utils import GameSettings, Logger
from src.utils.definition import get_menu_sprite_path
from typing import override

class CatchScene(Scene):
    background: BackgroundSprite
    catch_button: Button
    cancel_button: Button
    window_rect: pg.Rect
    border_color: tuple
    monster: dict

    def __init__(self):
        super().__init__()
        try:
            self.background = BackgroundSprite("backgrounds/background1.png")
        except Exception as e:
            Logger.error(f"Failed to load background sprite: {e}")
            self.background = None
        
        self.border_color = (0, 0, 0)
        
        window_width = 500
        window_height = 300
        window_x = (GameSettings.SCREEN_WIDTH - window_width) // 2
        window_y = (GameSettings.SCREEN_HEIGHT - window_height) // 2
        self.window_rect = pg.Rect(window_x, window_y, window_width, window_height)

        self.monster = {
            "name": "WildMon",
            "hp": 30,
            "max_hp": 30,
            "level": 1,
            "sprite_path": get_menu_sprite_path(2)
        }

        try:
            self.catch_button = Button(
                "UI/button_play.png", "UI/button_play_hover.png",
                window_x + 120, GameSettings.SCREEN_HEIGHT - 100, 160, 64,
                self._on_catch_button
            )
        except Exception as e:
            Logger.error(f"Failed to create catch button: {e}")
            self.catch_button = None

        try:
            self.cancel_button = Button(
                "UI/button_x.png", "UI/button_x_hover.png",
                window_x + window_width - 120, GameSettings.SCREEN_HEIGHT - 100, 80, 64,
                lambda: scene_manager.change_scene("game")
            )
        except Exception as e:
            Logger.error(f"Failed to create cancel button: {e}")
            self.cancel_button = None

        try:
            self.dialog_font = resource_manager.get_font("Minecraft.ttf", 20)
        except Exception as e:
            self.dialog_font = pg.font.Font(None, 20)
        
        self.showing_battle_result = False
        self.battle_result_message = ""
        self.battle_result = None 
        self.result_text_timer = 0.0
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 36)
        
        self.item_panel = None

    def _on_catch_button(self):
        try:
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, "game_manager"):
                gm = game_scene.game_manager
                items = gm.bag._items_data if hasattr(gm.bag, '_items_data') else []
                
                if items:
                    from src.interface.components.item_panel import ItemPanel
                    self.item_panel = ItemPanel(items, callback=self._on_item_selected)
                    self.item_panel.open(callback=self._on_item_selected)
                else:
                    self._catch_monster()
        except Exception as e:
            Logger.error(f"Failed to show item panel: {e}")
            self._catch_monster()
    
    def _on_item_selected(self, item_index: int):
        try:
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, "game_manager"):
                gm = game_scene.game_manager
                items = gm.bag._items_data if hasattr(gm.bag, '_items_data') else []
                
                if 0 <= item_index < len(items):
                    item = items[item_index]
                    option = item.get('option', None)
                    name = item.get('name', '')
                    
                    if name == "Magic Hand" or option == 8:
                        self._add_monster_to_bag(self.monster)
                        item['count'] -= 1
                        if item['count'] <= 0: items.pop(item_index)
                        scene_manager.change_scene("game")
                        return
                    
                    elif name == "Shield" or option == 6:
                        item['count'] -= 1
                        if item['count'] <= 0: items.pop(item_index)
                        scene_manager.change_scene("game")
                        return
                    
                    elif name == "Pokeball" or option == 1:
                        item['count'] -= 1
                        if item['count'] <= 0: items.pop(item_index)
                        self._catch_monster()
                        return
                    
                    elif name == "Heal Potion" or option == 2:
                        item['count'] -= 1
                        if item['count'] <= 0: items.pop(item_index)
                        scene_manager.change_scene("game")
                        return
        except Exception as e:
            Logger.error(f"Failed to handle item selection: {e}")

    def _catch_monster(self):
        try:
            self._add_monster_to_bag(self.monster)
            Logger.info(f"Caught monster: {self.monster['name']}")
        except Exception as e:
            Logger.error(f"Failed to add monster to bag: {e}")
        finally:
            scene_manager.change_scene("game")
    
    def _add_monster_to_bag(self, monster: dict):
        try:
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, "game_manager"):
                gm = game_scene.game_manager
                if hasattr(gm.bag, '_monsters_data'):
                    level = monster.get('level', 1)
                    captured = {
                        'name': monster.get('name', 'WildMon'),
                        'level': level,
                        'max_hp': monster.get('max_hp', 30),
                        'hp': monster.get('max_hp', 30),
                        'attack': level * 10,
                        'exp': 0,
                        'max_exp': (level + 1) * 10,
                        'sprite_path': monster.get('sprite_path', get_menu_sprite_path(2))
                    }
                    gm.bag._monsters_data.append(captured)
        except Exception as e:
            Logger.error(f"Failed to add monster to bag: {e}")

    @override
    def enter(self) -> None:
        try:
            game_scene = scene_manager._scenes.get("game")
            if game_scene and hasattr(game_scene, "game_manager"):
                gm = game_scene.game_manager
                import random
                candidates = getattr(gm.bag, '_monsters_data', []) or []
                
                e_lv = 1
                if candidates:
                    levels = [m.get('level', 1) for m in candidates]
                    if levels:
                        e_lv = random.randint(min(levels), max(levels) + 5)
                
                e_max = e_lv * 100
                
                fallback = [{'name': 'WildMon', 'sprite_path': get_menu_sprite_path(2)}]
                pool = candidates if candidates else fallback
                choice_template = random.choice(pool)
                
                self.monster = {
                    "name": choice_template.get('name', 'WildMon'),
                    "hp": e_max,
                    "max_hp": e_max,
                    "level": e_lv,
                    "sprite_path": choice_template.get('sprite_path', get_menu_sprite_path(2))
                }
                
                has_alive_pokemon = any(mon.get('hp', 0) > 0 for mon in candidates)
                if not has_alive_pokemon:
                    Logger.warning("Player has no alive pokemon! Cannot enter catch scene.")
                    scene_manager.change_scene("game")
                    return
        except Exception as e:
            Logger.error(f"CatchScene.enter failed to pick monster: {e}")

    @override
    def exit(self) -> None:
        pass

    @override
    def update(self, dt: float) -> None:
        try:
            if self.showing_battle_result:
                self.result_text_timer -= dt
                if self.result_text_timer <= 0:
                    scene_manager.change_scene("game")
                    return
            
            if self.item_panel and self.item_panel.is_open:
                self.item_panel.update(dt, input_manager)
            
            if self.catch_button is not None:
                self.catch_button.update(dt)
            if self.cancel_button is not None:
                self.cancel_button.update(dt)

            if input_manager.key_pressed(pg.K_ESCAPE):
                if self.item_panel and self.item_panel.is_open:
                    self.item_panel.close()
                else:
                    scene_manager.change_scene("game")

            if input_manager.key_pressed(pg.K_SPACE):
                try:
                    self._on_catch_button()
                except Exception as e:
                    Logger.error(f"Exception while handling SPACE catch: {e}")
        except Exception as e:
            Logger.error(f"Exception in CatchScene.update: {e}")

    @override
    def draw(self, screen: pg.Surface) -> None:
        try:
            if self.background is not None:
                self.background.draw(screen)
            else:
                screen.fill((50, 50, 50))

            player_mon = None
            try:
                game_scene = scene_manager._scenes.get("game")
                if game_scene and hasattr(game_scene, "game_manager"):
                    bag = game_scene.game_manager.bag
                    if bag._monsters_data:
                        player_mon = bag._monsters_data[0]
            except Exception:
                player_mon = None

            if player_mon is None:
                player_mon = {"name": "YourMon", "sprite_path": get_menu_sprite_path(1), "hp": 40, "max_hp": 40, "level": 5}

            wild_mon = self.monster

            try:
                player_img = resource_manager.get_image(player_mon.get("sprite_path"))
            except Exception:
                player_img = pg.Surface((GameSettings.TILE_SIZE, GameSettings.TILE_SIZE), pg.SRCALPHA)
                player_img.fill((255, 0, 255))
            
            try:
                wild_img = resource_manager.get_image(wild_mon.get("sprite_path"))
            except Exception:
                wild_img = pg.Surface((GameSettings.TILE_SIZE, GameSettings.TILE_SIZE), pg.SRCALPHA)
                wild_img.fill((255, 0, 255))

            def scale_keep(surface, factor=3):
                w, h = surface.get_size()
                return pg.transform.scale(surface, (w * factor, h * factor))

            p_img = scale_keep(player_img, 3)
            w_img = scale_keep(wild_img, 3)

            p_x = 80
            p_y = GameSettings.SCREEN_HEIGHT // 2 + 20
            w_x = GameSettings.SCREEN_WIDTH // 2 + 60
            w_y = GameSettings.SCREEN_HEIGHT // 2 - w_img.get_height() // 2 - 40

            screen.blit(p_img, (p_x, p_y))
            screen.blit(w_img, (w_x, w_y))

            # Bottom Dialog Panel
            dialog_h = 120
            dialog_rect = pg.Rect(0, GameSettings.SCREEN_HEIGHT - dialog_h, GameSettings.SCREEN_WIDTH, dialog_h)
            pg.draw.rect(screen, (20, 20, 20), dialog_rect) # Dark Grey Fill
            pg.draw.line(screen, (255, 255, 255), (0, dialog_rect.top), (GameSettings.SCREEN_WIDTH, dialog_rect.top), 3) # White Border

            dialog_text = f"A wild {wild_mon['name']} appears!"
            text_surf = self.dialog_font.render(dialog_text, True, (255, 255, 255))
            screen.blit(text_surf, (30, GameSettings.SCREEN_HEIGHT - dialog_h + 20))

            status_font = resource_manager.get_font("Minecraft.ttf", 18)
            
            # Helper to draw improved status box
            def draw_status_box(rect, name, img, hp, max_hp, is_wild=False):
                # Box with rounded corners
                pg.draw.rect(screen, (240, 240, 240), rect, border_radius=8)
                pg.draw.rect(screen, self.border_color, rect, 2, border_radius=8)
                
                # Icon
                icon_s = pg.transform.scale(img, (48, 48))
                screen.blit(icon_s, (rect.left + 8, rect.top + 16))
                
                # Name
                name_s = status_font.render(name, True, (0, 0, 0))
                screen.blit(name_s, (rect.left + 64, rect.top + 10))
                
                # HP Bar
                bar_w = 160 if not is_wild else 120
                bar_h = 10
                bar_x = rect.left + 64
                bar_y = rect.top + 45
                
                pg.draw.rect(screen, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
                filled = int((hp / max(1, max_hp)) * bar_w)
                color = (0, 200, 0) if (hp/max_hp) > 0.5 else (255, 165, 0) if (hp/max_hp) > 0.2 else (255, 0, 0)
                if filled > 0:
                    pg.draw.rect(screen, color, (bar_x, bar_y, filled, bar_h), border_radius=3)
                
            # Player Status
            p_rect = pg.Rect(20, GameSettings.SCREEN_HEIGHT - dialog_h - 90, 260, 80)
            draw_status_box(p_rect, player_mon.get("name", "You"), player_img, player_mon.get("hp", 1), player_mon.get("max_hp", 1))

            # Enemy Status
            e_rect = pg.Rect(GameSettings.SCREEN_WIDTH - 280, 20, 240, 80)
            draw_status_box(e_rect, wild_mon.get("name", "Wild"), wild_img, wild_mon.get("hp", 1), wild_mon.get("max_hp", 1), True)

            # Buttons
            if self.catch_button is not None:
                self.catch_button.draw(screen)
            if self.cancel_button is not None:
                self.cancel_button.draw(screen)
            
            # Item Panel
            if self.item_panel and self.item_panel.is_open:
                self.item_panel.draw(screen)
            
            # Result Overlay
            if self.showing_battle_result:
                self._draw_result_overlay(screen)
        
        except Exception as e:
            Logger.error(f"CRITICAL: Unhandled exception in CatchScene.draw: {e}")
            screen.fill((0, 0, 0))

    def _draw_result_overlay(self, screen):
        """Draws a cinematic overlay for results."""
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(150)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        banner_h = 100
        banner_y = (GameSettings.SCREEN_HEIGHT - banner_h) // 2
        pg.draw.rect(screen, (0, 0, 0, 200), (0, banner_y, GameSettings.SCREEN_WIDTH, banner_h))
        pg.draw.line(screen, (255, 215, 0), (0, banner_y), (GameSettings.SCREEN_WIDTH, banner_y), 2)
        pg.draw.line(screen, (255, 215, 0), (0, banner_y + banner_h), (GameSettings.SCREEN_WIDTH, banner_y + banner_h), 2)

        msg = self.battle_result_message
        col = (0, 255, 0) if self.battle_result == 'win' else (255, 50, 50)
        
        shadow_txt = self.font_title.render(msg, True, (0, 0, 0))
        txt = self.font_title.render(msg, True, col)
        
        cx = GameSettings.SCREEN_WIDTH // 2 - txt.get_width() // 2
        cy = GameSettings.SCREEN_HEIGHT // 2 - txt.get_height() // 2
        
        screen.blit(shadow_txt, (cx + 3, cy + 3))
        screen.blit(txt, (cx, cy))