import pygame as pg
import threading
import time
import random
import math

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core import services
from src.core.services import sound_manager, input_manager, scene_manager
from src.utils.particle_system import ParticleManager

from src.sprites import Sprite, Animation
from src.interface.components.overlay import Overlay
from src.interface.components.button import Button
from src.interface.components.backpack_panel import BackpackPanel
from src.interface.components.shop_panel import ShopPanel
from src.interface.components.hospital_panel import HospitalPanel
from src.interface.components.chat_overlay import ChatOverlay
from src.interface.components.minimap import Minimap
from src.interface.components.navigation_panel import NavigationPanel
from src.interface.components.altar_panel import AltarPanel
from src.entities.shopkeeper import Shopkeeper
from src.interface.components.casino_panel import CasinoPanel 
# [修正] 這裡絕對不能有 from src.core.dev_tools import dev_tool

from src.utils import Direction
from typing import override


class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    sprite_online: Sprite
    particle_manager: ParticleManager
    casino_panel: CasinoPanel 

    def __init__(self):
        super().__init__()

        if services.should_load_game:
            manager = GameManager.load("saves/game0.json")
            services.should_load_game = False
        else:
            manager = GameManager.new_game()

        if manager is None: exit(1)
        self.game_manager = manager

        if GameSettings.IS_ONLINE:
            self.online_manager = OnlineManager()
        else:
            self.online_manager = None

        self.sprite_online = Animation(
            "character/ow5.png", ["down", "left", "right", "up"], 4,
            (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        )

        self.particle_manager = ParticleManager()
        self.current_music_path = "" 

        self._transitioning = False
        self._transition_phase = "none"
        self._transition_timer = 0.0
        self._transition_duration = 0.25 
        
        self._flicker_duration = 1.5     
        self._flicker_timer = 0.0
        self._flicker_state = False      

        self._fade_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)).convert_alpha()

        self._darkness_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self._base_light_radius = 250
        self._light_mask_original = self._create_gradient_circle(self._base_light_radius) 
        self._light_pulse_timer = 0.0 
        
        self._flashlight_battery = 100.0
        self._battery_drain_speed = 2.0 

        self._last_damage_time = 0.0
        self._damage_cooldown = 1.0 
        self._red_flash_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)).convert_alpha()
        self._red_flash_surf.fill((255, 0, 0))
        self._red_flash_alpha = 0
        
        self._shake_timer = 0.0  
        self._shake_amount = 5   

        self._footstep_timer = 0.0
        self._footstep_interval = 0.35 
        
        self._speed_boost_timer = 0.0
        self._base_speed_multiplier = 1.0

        self._heartbeat_playing = False
        self._heartbeat_sound = None
        try:
            if services.sound_manager: 
                pass
        except:
            pass

        self._ambience_timer = random.uniform(5.0, 15.0) 

        self._map_name_timer = 0.0
        self._current_map_display_name = ""
        self.font_map_name = pg.font.Font("assets/fonts/Minecraft.ttf", 48)

        self.coord_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
        self.font_warning = pg.font.Font("assets/fonts/Minecraft.ttf", 32)
        self.show_no_pokemon_warning = False
        self.warning_timer = 0.0

        self.overlay = Overlay(self.game_manager)
        self.backpack_panel = BackpackPanel(self.game_manager)
        self.navigation_panel = NavigationPanel(self.game_manager)
        self.shop_panel = ShopPanel(self.game_manager)
        self.hospital_panel = HospitalPanel(self.game_manager)
        self.altar_panel = AltarPanel(self.game_manager)
        self.casino_panel = CasinoPanel(self.game_manager)
        
        self.minimap = None 
        
        self.chat_overlay = ChatOverlay(self.game_manager)
        self.chat_overlay.set_state_change_callback(self._on_chat_state_change)

        self.overlay_button = Button("UI/button_setting.png", "UI/button_setting_hover.png", 10, 10, 50, 50, 
                                     lambda: self.overlay.close() if self.overlay.is_open else self.overlay.open())
        self.backpack_button = Button("UI/button_backpack.png", "UI/button_backpack_hover.png", 70, 10, 50, 50, 
                                      lambda: self.backpack_panel.close() if self.backpack_panel.is_open else self.backpack_panel.open())
        self.navigation_button = Button("UI/button_play.png", "UI/button_play_hover.png", 130, 10, 50, 50, 
                                        lambda: self.navigation_panel.close() if self.navigation_panel.is_open else self.navigation_panel.open())

        self.shopkeeper = Shopkeeper(17 * GameSettings.TILE_SIZE, 28 * GameSettings.TILE_SIZE, self.game_manager, 
                                     facing=Direction.DOWN, 
                                     on_interact=lambda: self.shop_panel.close() if self.shop_panel.is_open else self.shop_panel.open())

    def _create_gradient_circle(self, radius: int) -> pg.Surface:
        surf = pg.Surface((radius * 2, radius * 2))
        surf.fill((0, 0, 0))
        center = (radius, radius)
        for r in range(radius, 0, -2):
            intensity = 255 * (1 - (r / radius) ** 2) 
            color = (intensity, intensity, intensity)
            pg.draw.circle(surf, color, center, r)
        return surf

    def _on_chat_state_change(self, active: bool):
        self.game_manager.chat_active = active

    def _start_pending_navigation(self):
        if self.game_manager.pending_navigation_destination == (0, 0): return
        final_dest = self.game_manager.pending_navigation_destination
        self.game_manager.pending_navigation_destination = (0, 0)
        start_pos = (
            int(self.game_manager.player.position.x // GameSettings.TILE_SIZE),
            int(self.game_manager.player.position.y // GameSettings.TILE_SIZE)
        )
        path = self.navigation_panel._find_path(start_pos, final_dest, self.game_manager.current_map, self.game_manager)
        if path and len(path) > 1:
            self.navigation_panel.navigation_path = path
            self.navigation_panel.current_path_index = 0
            self.navigation_panel.is_navigating = True
            self.game_manager.navigation_active = True

    def handle_event(self, event):
        # [關鍵修正] 將 import 移到這裡
        from src.core.dev_tools import dev_tool
        
        dev_tool.handle_event(event, self.game_manager)
        
        if self.chat_overlay.active:
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.chat_overlay.toggle()
                    self.game_manager.chat_active = False
                    return 
                elif event.key == pg.K_RETURN:
                    msg = getattr(self.chat_overlay, 'input_text', "")
                    if msg and self.online_manager:
                        self.online_manager.send_message(msg)
                        self.chat_overlay.input_text = ""
            return self.chat_overlay.handle_input(event)
        
        elif event.type == pg.KEYDOWN and event.key == pg.K_t:
             self.chat_overlay.toggle()
             self.game_manager.chat_active = True

    @override
    def enter(self) -> None:
        self.current_music_path = ""
        self._current_map_display_name = ""
        
        if "dark map" in self.game_manager.current_map_key:
            self._current_map_display_name = "Dark World"
        elif self.game_manager.current_map_key == "new map.tmx":
            self._current_map_display_name = "Route 1"
            self._flashlight_battery = 100.0 
        else:
            self._current_map_display_name = "Pallet Town"
            self._flashlight_battery = 100.0 
            
        self._map_name_timer = 3.0
            
        if self.online_manager:
            self.online_manager.enter()

    @override
    def exit(self) -> None:
        if self.online_manager:
            self.online_manager.exit()
            
        if self._heartbeat_sound and self._heartbeat_playing:
            self._heartbeat_sound.stop()
            self._heartbeat_playing = False

    @override
    def update(self, dt: float):
        if self.minimap is None and self.game_manager.player:
            self.minimap = Minimap(self.game_manager.current_map, self.game_manager.player)

        desired_bgm = ""
        if self.casino_panel.is_open:
            desired_bgm = "RBY 135 To Bill_s Origin From Cerulean (Route 24).ogg"
        else:
            if "dark map" in self.game_manager.current_map_key:
                desired_bgm = "horror-thriller-action-247745.mp3"
            elif self.game_manager.current_map_key == "new map.tmx":
                desired_bgm = "RBY 109 Road to Viridian City (Route 1).ogg"
            else:
                desired_bgm = "RBY 103 Pallet Town.ogg"
        
        if desired_bgm and self.current_music_path != desired_bgm:
            self.current_music_path = desired_bgm
            sound_manager.play_bgm(desired_bgm)

        if self.casino_panel.is_open:
            self.casino_panel.update(dt, input_manager)

        self.particle_manager.update(dt)
        if "dark map" in self.game_manager.current_map_key and self.game_manager.player:
            self.particle_manager.create_dark_fog(
                self.game_manager.player.camera, 
                GameSettings.SCREEN_WIDTH, 
                GameSettings.SCREEN_HEIGHT
            )
            
            if self._flashlight_battery > 0:
                self._flashlight_battery -= self._battery_drain_speed * dt
            else:
                self._flashlight_battery = 0.0
                
            self._ambience_timer -= dt
            if self._ambience_timer <= 0:
                self._ambience_timer = random.uniform(8.0, 20.0) 

        if self._speed_boost_timer > 0:
            self._speed_boost_timer -= dt
            self._base_speed_multiplier = 1.5
        else:
            self._base_speed_multiplier = 1.0

        first_mon = None
        for m in self.game_manager.bag._monsters_data:
            if not m.get('is_dead', False):
                first_mon = m
                break
        
        if first_mon:
            hp_ratio = first_mon['hp'] / first_mon['max_hp']
            if hp_ratio < 0.3 and not self._heartbeat_playing and self._heartbeat_sound:
                self._heartbeat_sound.play(-1) 
                self._heartbeat_playing = True
            elif hp_ratio >= 0.3 and self._heartbeat_playing and self._heartbeat_sound:
                self._heartbeat_sound.stop()
                self._heartbeat_playing = False
        else:
            if self._heartbeat_playing and self._heartbeat_sound:
                self._heartbeat_sound.stop()
                self._heartbeat_playing = False

        if self._shake_timer > 0:
            self._shake_timer -= dt

        if self._map_name_timer > 0:
            self._map_name_timer -= dt

        self._light_pulse_timer += dt

        if self.game_manager.should_change_scene:
            if not self._transitioning:
                self._transitioning = True
                self._transition_phase = "out"
                self._transition_timer = 0.0
                self._flicker_timer = 0.0
                
            if self.game_manager.is_triggering_dark_event:
                self._flicker_timer += dt
                if int(self._flicker_timer * 10) % 2 == 0:
                    self._flicker_state = True 
                else:
                    self._flicker_state = False 
                
                if self._flicker_timer >= self._flicker_duration:
                    self._perform_map_switch()
                    self._transition_phase = "in"
                    self._transition_timer = 0.0
            else:
                self._transition_timer += dt
                if self._transition_timer >= self._transition_duration:
                    self._perform_map_switch()
                    self._transition_phase = "in"
                    self._transition_timer = 0.0
                    
        elif self._transitioning:
            if self._transition_phase == "in":
                self._transition_timer += dt
                if self._transition_timer >= self._transition_duration:
                    self._transitioning = False
                    self._transition_phase = "none"
                    self._transition_timer = 0.0

        if self.show_no_pokemon_warning:
            self.warning_timer -= dt
            if self.warning_timer <= 0: self.show_no_pokemon_warning = False

        if self._red_flash_alpha > 0:
            self._red_flash_alpha -= dt * 500
            if self._red_flash_alpha < 0: self._red_flash_alpha = 0

        if self.game_manager.player and not self.casino_panel.is_open: 
            keys = [pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN, pg.K_w, pg.K_a, pg.K_s, pg.K_d]
            is_moving = any(input_manager.key_down(k) for k in keys) and not self._transitioning

            if is_moving:
                self._footstep_timer -= dt
                if self._footstep_timer <= 0:
                    freq = self._footstep_interval * (0.7 if self._speed_boost_timer > 0 else 1.0)
                    sound_manager.play_sound("assets/sounds/step.wav", volume=0.3)
                    self._footstep_timer = freq

            final_speed_mult = self._base_speed_multiplier
            if self.game_manager.current_map_key == "dark map.tmx":
                final_speed_mult *= 0.6 
            
            self.game_manager.player.update(dt * final_speed_mult)

        for enemy in self.game_manager.current_enemy_trainers: enemy.update(dt)
        self.shopkeeper.update(dt)
        self.game_manager.bag.update(dt)

        if self.game_manager.player and self.online_manager:
            p_pos = self.game_manager.player.position
            p_dir = self.game_manager.player.direction.name.lower()
            is_moving_online = any(input_manager.key_down(k) for k in [pg.K_LEFT, pg.K_RIGHT, pg.K_UP, pg.K_DOWN, pg.K_w, pg.K_a, pg.K_s, pg.K_d])
            self.online_manager.update(p_pos.x, p_pos.y, self.game_manager.current_map.path_name, p_dir, is_moving_online)
            server_msgs = self.online_manager.get_chat_history()
            self.chat_overlay.messages = server_msgs

        self.overlay_button.update(dt)
        self.overlay.update(dt)
        self.backpack_button.update(dt)
        self.backpack_panel.update(dt)
        self.navigation_button.update(dt)
        self.navigation_panel.update(dt)
        self.shop_panel.update(dt)
        self.hospital_panel.update(dt)
        self.altar_panel.update(dt)
        if self.minimap:
            self.minimap.update(dt)
            if input_manager.key_pressed(pg.K_m): self.minimap.toggle()
        self.chat_overlay.update(dt)
        if input_manager.key_pressed(pg.K_t) and not self.chat_overlay.active:
            self.chat_overlay.toggle()
            self.game_manager.chat_active = self.chat_overlay.active

        if not self.casino_panel.is_open:
            self._handle_interactions()

    def _perform_map_switch(self):
        is_nav_event = self.game_manager.pending_navigation_destination != (0, 0)
        self.game_manager.try_switch_map()
        self.enter() 

        if is_nav_event and self.game_manager.current_map.path_name == "map.tmx":
            cx, cy = 16 * GameSettings.TILE_SIZE, 29 * GameSettings.TILE_SIZE
            self.game_manager.player.position.x = float(cx)
            self.game_manager.player.position.y = float(cy)
            self.game_manager.player.camera.x = float(cx)
            self.game_manager.player.camera.y = float(cy)
        if self.minimap: self.minimap.set_map(self.game_manager.current_map)
        if self.game_manager.pending_navigation_destination != (0, 0):
            self._start_pending_navigation()
            
        self.particle_manager.particles.clear()

    def _handle_interactions(self):
        try:
            if self.game_manager.player:
                if hasattr(self.game_manager.current_map, "tmx_data"):
                    tmx_map = self.game_manager.current_map.tmx_data
                    
                    p_rect = pg.Rect(
                        self.game_manager.player.position.x + 8, 
                        self.game_manager.player.position.y + 20, 
                        16, 
                        12
                    )
                    
                    start_tx = int(p_rect.left // GameSettings.TILE_SIZE)
                    end_tx = int(p_rect.right // GameSettings.TILE_SIZE)
                    start_ty = int(p_rect.top // GameSettings.TILE_SIZE)
                    end_ty = int(p_rect.bottom // GameSettings.TILE_SIZE)
                    
                    target_layers = ["aqua position", "aerial position"]
                    
                    for py in range(start_ty, end_ty + 1):
                        for px in range(start_tx, end_tx + 1):
                            
                            for layer_name in target_layers:
                                try:
                                    layer = tmx_map.get_layer_by_name(layer_name)
                                    gid = 0
                                    if hasattr(layer, 'data'):
                                        if 0 <= py < len(layer.data) and 0 <= px < len(layer.data[0]):
                                            gid = layer.data[py][px]
                                    
                                    if gid != 0 and input_manager.key_pressed(pg.K_SPACE):
                                        if layer_name == "aqua position":
                                            for m in self.game_manager.bag._monsters_data:
                                                m['hp'] = m['max_hp']
                                                m['is_dead'] = False
                                            Logger.info(f"Interaction at ({px},{py}): Aqua Zone Healed!")
                                            return
                                            
                                        elif layer_name == "aerial position":
                                            self.particle_manager.particles.clear()
                                            self._speed_boost_timer = 20.0
                                            Logger.info(f"Interaction at ({px},{py}): Aerial Zone Boost!")
                                            return
                                            
                                except ValueError:
                                    pass 

                casino_spot = self.game_manager.current_map.get_casino_at_pos(self.game_manager.player.position)
                if casino_spot and input_manager.key_pressed(pg.K_SPACE):
                    Logger.info("Interaction: Casino Opened")
                    self.casino_panel.open()

                bush = self.game_manager.current_map.get_bush_at_pos(self.game_manager.player.position)
                now = pg.time.get_ticks() / 1000.0

                if bush:
                    if self.game_manager.current_map_key == "dark map.tmx":
                        if now - self._last_damage_time >= 3.0: 
                            self._last_damage_time = now
                            has_live = any(m.get('hp',0)>0 and not m.get('is_dead',False) for m in getattr(self.game_manager.bag, '_monsters_data', []))
                            if has_live:
                                Logger.info("[Dark World] Ambushed by corrupted pokemon!")
                                self.game_manager.is_dark_battle = True 
                                scene_manager.change_scene("battle")
                            else:
                                if not self.show_no_pokemon_warning:
                                    self.show_no_pokemon_warning = True
                                    self.warning_timer = 2.0

                    elif input_manager.key_pressed(pg.K_SPACE):
                        if now - getattr(self, "_last_bush_trigger", 0) >= 1.0:
                            self._last_bush_trigger = now
                            has_live = any(m.get('hp',0)>0 and not m.get('is_dead',False) for m in getattr(self.game_manager.bag, '_monsters_data', []))
                            if has_live:
                                self.game_manager.is_dark_battle = False 
                                scene_manager.change_scene("battle")
                            else: 
                                self.show_no_pokemon_warning, self.warning_timer = True, 2.0
                
                altar = self.game_manager.current_map.get_altar_at_pos(self.game_manager.player.position)
                if altar and input_manager.key_pressed(pg.K_SPACE):
                    self.altar_panel.close() if self.altar_panel.is_open else self.altar_panel.open()

                shop_keeper = self.game_manager.current_map.get_shop_keeper_at_pos(self.game_manager.player.position)
                if shop_keeper and input_manager.key_pressed(pg.K_SPACE):
                    self.shop_panel.close() if self.shop_panel.is_open else self.shop_panel.open()

                hospital = self.game_manager.current_map.get_hospital_at_pos(self.game_manager.player.position)
                if hospital and input_manager.key_pressed(pg.K_SPACE):
                    self.hospital_panel.close() if self.hospital_panel.is_open else self.hospital_panel.open()
        except Exception as e:
            Logger.warning(f"Interaction error: {e}")

    @override
    def draw(self, screen: pg.Surface):
        # [關鍵修正] 將 import 移到這裡
        from src.core.dev_tools import dev_tool

        camera = self.game_manager.player.camera if self.game_manager.player else PositionCamera(0, 0)
        
        if self._shake_timer > 0:
            offset_x = random.randint(-self._shake_amount, self._shake_amount)
            offset_y = random.randint(-self._shake_amount, self._shake_amount)
            camera.x += offset_x
            camera.y += offset_y

        map_to_draw = self.game_manager.current_map
        if self._transitioning and self.game_manager.is_triggering_dark_event:
            if self._flicker_state:
                dark_key = "dark map.tmx"
                if dark_key in self.game_manager.maps:
                    map_to_draw = self.game_manager.maps[dark_key]
            else:
                target_key = self.game_manager.flicker_map_key
                if target_key in self.game_manager.maps:
                    map_to_draw = self.game_manager.maps[target_key]

        map_to_draw.draw(screen, camera)

        if self.game_manager.player: self.game_manager.player.draw(screen, camera)
        for enemy in self.game_manager.current_enemy_trainers: enemy.draw(screen, camera)
        self.shopkeeper.draw(screen, camera)
        self.game_manager.bag.draw(screen)

        if self.online_manager and self.game_manager.player:
            for p in self.online_manager.get_list_players():
                if str(p.get("map")) == str(self.game_manager.current_map.path_name):
                    world_pos = Position(p["x"], p["y"])
                    self.sprite_online.update_pos(world_pos)
                    direction = p.get("direction", "down")
                    self.sprite_online.switch(direction)
                    if p.get("moving", False):
                        self.sprite_online.update(0.016)
                    else:
                        if hasattr(self.sprite_online, 'index'): self.sprite_online.index = 0
                        elif hasattr(self.sprite_online, 'frame_index'): self.sprite_online.frame_index = 0
                    self.sprite_online.draw(screen, camera)

        self.particle_manager.draw(screen, camera)

        if self.game_manager.current_map_key == "dark map.tmx":
            self._darkness_surf.fill((20, 20, 30)) 
            if self.game_manager.player:
                p_rect = self.game_manager.player.animation.rect
                screen_rect = camera.transform_rect(p_rect)
                
                battery_factor = max(0.2, self._flashlight_battery / 100.0) 
                pulse_scale = 1.0 + math.sin(self._light_pulse_timer * 2.0) * 0.05
                current_radius = int(self._base_light_radius * battery_factor * pulse_scale)
                
                light_mask = pg.transform.scale(self._light_mask_original, (current_radius*2, current_radius*2))
                light_rect = light_mask.get_rect(center=screen_rect.center)
                self._darkness_surf.blit(light_mask, light_rect, special_flags=pg.BLEND_RGBA_ADD)
            screen.blit(self._darkness_surf, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

        if self._red_flash_alpha > 0:
            self._red_flash_surf.set_alpha(int(self._red_flash_alpha))
            screen.blit(self._red_flash_surf, (0, 0))

        self.overlay_button.draw(screen)
        self.overlay.draw(screen)
        self.backpack_button.draw(screen)
        self.backpack_panel.draw(screen)
        self.navigation_button.draw(screen)
        self.navigation_panel.draw(screen)
        self.shop_panel.draw(screen)
        self.hospital_panel.draw(screen)
        self.altar_panel.draw(screen)
        
        # 繪製 Casino Panel
        if self.casino_panel.is_open:
            self.casino_panel.draw(screen)
            
        if self.minimap: self.minimap.draw(screen)
        self.chat_overlay.draw(screen)

        if self._map_name_timer > 0:
            alpha = min(255, int(self._map_name_timer * 255))
            txt_surf = self.font_map_name.render(self._current_map_display_name, True, (255, 255, 255))
            text_container = pg.Surface(txt_surf.get_size(), pg.SRCALPHA)
            text_container.fill((0, 0, 0, 0)) 
            text_container.blit(txt_surf, (0, 0))
            text_container.set_alpha(alpha)
            x = GameSettings.SCREEN_WIDTH // 2 - txt_surf.get_width() // 2
            y = 100 
            screen.blit(text_container, (x, y))

        if self.show_no_pokemon_warning:
            txt = self.font_warning.render("YOU DON'T HAVE A LIVE POKEMON!", True, (255, 0, 0))
            screen.blit(txt, (GameSettings.SCREEN_WIDTH//2 - txt.get_width()//2, GameSettings.SCREEN_HEIGHT//2))

        if self.game_manager.player:
            tx, ty = int(self.game_manager.player.position.x // GameSettings.TILE_SIZE), int(self.game_manager.player.position.y // GameSettings.TILE_SIZE)
            coord = self.coord_font.render(f"X: {tx}, Y: {ty}", True, (255, 255, 255))
            screen.blit(coord, (10, GameSettings.SCREEN_HEIGHT - 30))

        if self._transitioning:
            if not self.game_manager.is_triggering_dark_event:
                progress = min(self._transition_timer/self._transition_duration, 1.0)
                alpha = int(
                    progress * 255 if self._transition_phase == "out"
                    else (1.0 - progress) * 255
                )
                self._fade_surf.fill((0, 0, 0, alpha))
                screen.blit(self._fade_surf, (0, 0))
        
        dev_tool.draw(screen)