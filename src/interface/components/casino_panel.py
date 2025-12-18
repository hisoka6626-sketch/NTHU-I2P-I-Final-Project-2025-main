import pygame as pg
import random
from src.utils import GameSettings, Logger
from src.interface.components.button import Button
# [修正] 這裡絕對不能有 from src.core.dev_tools import dev_tool

class CasinoPanel:
    def __init__(self, game_manager):
        self.game_manager = game_manager
        self.is_open = False
        
        # --- 畫面設定 ---
        self.width = 600
        self.height = 450
        self.x = (GameSettings.SCREEN_WIDTH - self.width) // 2
        self.y = (GameSettings.SCREEN_HEIGHT - self.height) // 2
        self.rect = pg.Rect(self.x, self.y, self.width, self.height)
        
        # --- 資源載入 ---
        self.coin_img_path = "assets/images/ingame_ui/coin.png"
        self.coin_img = None
        self.coin_particle_img = None 
        try:
            raw_img = pg.image.load(self.coin_img_path).convert_alpha()
            # 滾輪用小圖
            self.coin_img = pg.transform.scale(raw_img, (60, 60))
            # 掉落動畫用稍小一點的圖
            self.coin_particle_img = pg.transform.scale(raw_img, (40, 40))
        except FileNotFoundError:
            Logger.warning(f"CasinoPanel: {self.coin_img_path} not found, using text fallback.")

        # 拉霸機符號設定
        self.symbols = ["MON", "ITEM", "COIN", "7"] 
        
        # 基礎機率
        self.base_weights = [20, 20, 20, 40]     
        
        self.reels = [0, 0, 0] 
        self.spinning = [False, False, False]
        self.spin_timer = [0.0, 0.0, 0.0]
        
        self.cost = 1000
        self.message = f"SPACE TO SPIN ({self.cost}G)"
        self.message_color = (255, 255, 255)
        
        # 字體設定
        self.font_large = pg.font.Font("assets/fonts/Minecraft.ttf", 64)
        self.font_medium = pg.font.Font("assets/fonts/Minecraft.ttf", 32)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        
        self.btn_close = Button(
            "UI/button_x.png", "UI/button_x_hover.png",
            self.x + self.width - 50, self.y + 15, 40, 40,
            self.close
        )

        # --- Jackpot 動畫變數 ---
        self.is_jackpot_animating = False
        self.jackpot_timer = 0.0
        self.jackpot_duration = 5.0 
        self.particles = []

    def open(self):
        self.is_open = True
        self.message = f"COST: {self.cost} COINS"
        self.message_color = (255, 255, 255)
        self.is_jackpot_animating = False
        self.particles.clear()

    def close(self):
        self.is_open = False
        self.is_jackpot_animating = False 

    def spin(self):
        # [關鍵修正] 將 import 移到這裡，只有在執行 spin 時才載入
        from src.core.dev_tools import dev_tool

        if any(self.spinning): return
        if self.is_jackpot_animating: return 
        
        # 1. 檢查並扣除金幣 (如果開啟了 Casino Hack 則不扣錢)
        if not (dev_tool.active and dev_tool.casino_hack_mode):
            player_bag = self.game_manager.bag
            has_coins = False
            coin_item = None
            for item in player_bag._items_data:
                if item['name'] == 'Coins' and item['count'] >= self.cost:
                    has_coins = True
                    coin_item = item
                    break
            
            if not has_coins:
                self.message = "NOT ENOUGH COINS!"
                self.message_color = (255, 50, 50)
                return

            coin_item['count'] -= self.cost
        
        # 2. 啟動滾輪
        self.spinning = [True, True, True]
        self.spin_timer = [0.5, 1.0, 1.5]
        self.message = "SPINNING..."
        self.message_color = (255, 255, 0)

    def _get_random_symbol_index(self, custom_weights=None):
        weights = custom_weights if custom_weights else self.base_weights
        return random.choices(range(len(self.symbols)), weights=weights, k=1)[0]

    def _calculate_reel3_weights(self):
        s1_idx = self.reels[0]
        s2_idx = self.reels[1]
        
        if s1_idx != s2_idx:
            return self.base_weights
        
        symbol_name = self.symbols[s1_idx]
        
        if symbol_name == "7":
            return [33, 33, 33, 1] 
        elif symbol_name == "ITEM":
            return [26, 20, 27, 27]
        elif symbol_name == "MON":
            return [20, 27, 27, 26]
        elif symbol_name == "COIN":
            return [20, 20, 40, 20]
            
        return self.base_weights

    def _check_result(self):
        s1 = self.symbols[self.reels[0]]
        s2 = self.symbols[self.reels[1]]
        s3 = self.symbols[self.reels[2]]
        
        current_symbols = [s1, s2, s3]
        
        if s1 == "7" and s2 == "7" and s3 == "7":
            self._give_coins(10000)
            self._trigger_jackpot_animation()
        elif s1 == "MON" and s2 == "MON" and s3 == "MON":
            self._give_pokemon()
        elif s1 == "ITEM" and s2 == "ITEM" and s3 == "ITEM":
            self._give_item()
        elif s1 == "COIN" and s2 == "COIN" and s3 == "COIN":
            self._give_coins(3000)
        elif current_symbols.count("COIN") == 2:
            self._give_coins(500)
        else:
            self.message = "BAD LUCK..."
            self.message_color = (200, 200, 200)

    def _trigger_jackpot_animation(self):
        self.is_jackpot_animating = True
        self.jackpot_timer = self.jackpot_duration
        self.particles = []
        self.message = "JACKPOT!! 10000G!!"
        self.message_color = (255, 215, 0)

    def _update_jackpot_particles(self, dt):
        if len(self.particles) < 200: 
            spawn_count = random.randint(1, 3)
            for _ in range(spawn_count):
                self.particles.append({
                    'x': random.randint(0, GameSettings.SCREEN_WIDTH),
                    'y': -50,
                    'speed': random.uniform(200, 500),
                    'rot_speed': random.uniform(-90, 90)
                })
        
        for p in self.particles:
            p['y'] += p['speed'] * dt
            
        self.particles = [p for p in self.particles if p['y'] < GameSettings.SCREEN_HEIGHT + 50]

    def _give_coins(self, amount):
        found = False
        for item in self.game_manager.bag._items_data:
            if item['name'] == 'Coins':
                item['count'] += amount
                found = True
                break
        
        if not found:
             self.game_manager.bag._items_data.append({
                "name": "Coins", "count": amount, "sprite_path": "ingame_ui/coin.png", "option": 0
            })

        self.message = f"WINNER! +{amount} COINS"
        self.message_color = (255, 215, 0)

    def _give_item(self):
        item_pool = [
            {"name": "Potion", "path": "ingame_ui/potion.png", "opt": 2},
            {"name": "Pokeball", "path": "ingame_ui/ball.png", "opt": 1},
            {"name": "Shield", "path": "ingame_ui/shield.png", "opt": 6},
            {"name": "Strength Potion", "path": "ingame_ui/potion.png", "opt": 3},
            {"name": "Defense Potion", "path": "ingame_ui/potion.png", "opt": 4}
        ]
        prize = random.choice(item_pool)
        
        bag_items = self.game_manager.bag._items_data
        found = False
        for it in bag_items:
            if it['name'] == prize['name']:
                it['count'] += 1
                found = True
                break
        
        if not found:
            bag_items.append({
                "name": prize['name'],
                "count": 1,
                "sprite_path": prize['path'],
                "option": prize['opt']
            })
            
        self.message = f"GOT {prize['name'].upper()}!"
        self.message_color = (0, 255, 255)

    def _give_pokemon(self):
        player_mons = self.game_manager.bag._monsters_data
        min_lvl = 5
        max_lvl = 5
        
        active_mons = [m for m in player_mons if not m.get('is_dead', False)]
        if not active_mons:
            active_mons = player_mons 
            
        if active_mons:
            levels = [m.get('level', 1) for m in active_mons]
            min_lvl = min(levels)
            max_lvl = max(levels)
        
        target_lvl = random.randint(min_lvl, max_lvl)
        mid = random.randint(1, 16)
        pname = f"PrizeMon-{mid}"
        hp = 100 + target_lvl * 5
        atk = 10 + target_lvl * 2
        
        new_mon = {
            "name": pname,
            "hp": hp, "max_hp": hp,
            "attack": atk, "level": target_lvl,
            "exp": 0, "max_exp": 100,
            "sprite_path": f"menu_sprites/menusprite{mid}.png",
            "is_dead": False
        }
        
        self.game_manager.bag._monsters_data.append(new_mon)
        self.message = f"GOT LV.{target_lvl} POKEMON!"
        self.message_color = (0, 255, 0)

    def update(self, dt, input_manager):
        if not self.is_open: return
        
        # [關鍵修正] 這裡也要加 import，因為下面有用 dev_tool
        from src.core.dev_tools import dev_tool

        self.btn_close.update(dt)
        
        if self.is_jackpot_animating:
            self._update_jackpot_particles(dt)
            self.jackpot_timer -= dt
            if self.jackpot_timer <= 0:
                self.is_jackpot_animating = False
                self.particles.clear()
        
        if not self.is_jackpot_animating:
            if input_manager.key_pressed(pg.K_SPACE):
                self.spin()
            elif input_manager.key_pressed(pg.K_ESCAPE):
                self.close()

        for i in range(3):
            if self.spinning[i]:
                self.spin_timer[i] -= dt
                self.reels[i] = (self.reels[i] + 1) % len(self.symbols)
                
                if self.spin_timer[i] <= 0:
                    self.spinning[i] = False
                    
                    if dev_tool.active and dev_tool.casino_hack_mode:
                        self.reels[i] = 3 
                    else:
                        if i < 2:
                            self.reels[i] = self._get_random_symbol_index(self.base_weights)
                        else:
                            w = self._calculate_reel3_weights()
                            self.reels[i] = self._get_random_symbol_index(w)
                        
                    if i == 2:
                        self._check_result()

    def draw(self, screen):
        if not self.is_open: return
        
        overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        pg.draw.rect(screen, (40, 20, 60), self.rect, border_radius=20)
        pg.draw.rect(screen, (255, 215, 0), self.rect, 6, border_radius=20)
        
        title = self.font_medium.render("CASINO SLOTS", True, (255, 215, 0))
        screen.blit(title, (self.x + (self.width - title.get_width()) // 2, self.y + 20))
        
        reel_w = 120
        reel_h = 120
        spacing = 30
        total_w = (reel_w * 3) + (spacing * 2)
        start_reel_x = self.x + (self.width - total_w) // 2
        reel_y = self.y + 100
        
        for i in range(3):
            rx = start_reel_x + i * (reel_w + spacing)
            ry = reel_y
            
            pg.draw.rect(screen, (255, 255, 255), (rx, ry, reel_w, reel_h), border_radius=10)
            pg.draw.rect(screen, (0, 0, 0), (rx, ry, reel_w, reel_h), 3, border_radius=10)
            
            symbol_str = self.symbols[self.reels[i]]
            
            if symbol_str == "COIN" and self.coin_img:
                cx = rx + (reel_w - self.coin_img.get_width()) // 2
                cy = ry + (reel_h - self.coin_img.get_height()) // 2
                screen.blit(self.coin_img, (cx, cy))
            else:
                color = (0, 0, 0)
                if symbol_str == "MON": color = (255, 0, 0) 
                elif symbol_str == "ITEM": color = (0, 0, 255) 
                elif symbol_str == "COIN": color = (0, 150, 0)
                elif symbol_str == "7": color = (255, 215, 0) 
                
                txt = self.font_large.render(symbol_str, True, color)
                if txt.get_width() > reel_w - 10:
                    scale = (reel_w - 10) / txt.get_width()
                    txt = pg.transform.scale(txt, (int(txt.get_width() * scale), int(txt.get_height() * scale)))
                
                tx = rx + (reel_w - txt.get_width()) // 2
                ty = ry + (reel_h - txt.get_height()) // 2
                screen.blit(txt, (tx, ty))

        msg_surf = self.font_medium.render(self.message, True, self.message_color)
        mx = self.x + (self.width - msg_surf.get_width()) // 2
        my = self.y + 280
        screen.blit(msg_surf, (mx, my))
        
        hint = self.font_small.render(f"[SPACE] SPIN ({self.cost}G)   [ESC] EXIT", True, (180, 180, 180))
        hx = self.x + (self.width - hint.get_width()) // 2
        hy = self.y + 350
        screen.blit(hint, (hx, hy))
        
        self.btn_close.draw(screen)

        if self.is_jackpot_animating and self.coin_particle_img:
            for p in self.particles:
                screen.blit(self.coin_particle_img, (p['x'], p['y']))