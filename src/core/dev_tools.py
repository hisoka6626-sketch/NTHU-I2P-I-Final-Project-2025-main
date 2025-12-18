import pygame as pg
import time
from src.utils import Logger, GameSettings

class DevTool:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DevTool, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.active = False
        
        # 功能狀態開關
        self.noclip_mode = False       # 穿牆 (F1)
        self.casino_hack_mode = False  # 賭場必勝 (F2)
        # 移除了 show_hitboxes
        
        # 觸發邏輯變數
        self.tab_press_count = 0
        self.last_tab_time = 0.0
        self.trigger_window = 0.5

        # [關鍵修正] 這裡必須設為 None，避免在程式剛啟動時就載入字體導致當機
        self.font = None 

    def handle_event(self, event, game_manager):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_TAB:
                now = time.time()
                if now - self.last_tab_time < self.trigger_window:
                    self.tab_press_count += 1
                else:
                    self.tab_press_count = 1 
                
                self.last_tab_time = now

                if self.tab_press_count >= 5:
                    self.active = not self.active
                    self.tab_press_count = 0
                    state = "ON" if self.active else "OFF"
                    Logger.info(f"*** DEVELOPER MODE {state} ***")
                    # 開啟時預設關閉所有 hack
                    if not self.active:
                        self.noclip_mode = False
                        self.casino_hack_mode = False

            # 2. 開發者快捷鍵 (只有 Active 時有效)
            if self.active:
                if event.key == pg.K_F1:
                    self.noclip_mode = not self.noclip_mode
                    Logger.info(f"Dev: Noclip {'ON' if self.noclip_mode else 'OFF'}")
                
                elif event.key == pg.K_F2:
                    self.casino_hack_mode = not self.casino_hack_mode
                    Logger.info(f"Dev: Casino Hack {'ON' if self.casino_hack_mode else 'OFF'}")

                elif event.key == pg.K_F3:
                    self._add_money(game_manager, 10000)
                    Logger.info("Dev: Added 10000 Coins")

                elif event.key == pg.K_F4:
                    self._heal_all(game_manager)
                    Logger.info("Dev: Healed All Pokemon")
                    
                # 移除了 F5 功能

    def _add_money(self, gm, amount):
        try:
            found = False
            for item in gm.bag._items_data:
                if item['name'] == 'Coins':
                    item['count'] += amount
                    found = True
                    break
            if not found:
                gm.bag._items_data.append({"name": "Coins", "count": amount, "sprite_path": "ingame_ui/coin.png", "option": 0})
        except Exception as e:
            Logger.warning(f"DevTool Error Adding Money: {e}")

    def _heal_all(self, gm):
        try:
            for m in gm.bag._monsters_data:
                m['hp'] = m['max_hp']
                m['is_dead'] = False
        except Exception as e:
            Logger.warning(f"DevTool Error Healing: {e}")

    def draw(self, screen):
        if not self.active: return
        
        # [關鍵修正] 在這裡才載入字體，確保 Pygame 已經初始化完成
        if self.font is None:
            try:
                self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
            except:
                if not pg.font.get_init(): pg.font.init()
                self.font = pg.font.SysFont("Arial", 20)
        
        texts = [
            f"== DEV MODE ON ==",
            f"[F1] NoClip: {self.noclip_mode}",
            f"[F2] Casino 777: {self.casino_hack_mode}",
            f"[F3] +10k Coin",
            f"[F4] Heal All"
        ]
        
        y = 10
        for t in texts:
            try:
                surf = self.font.render(t, True, (0, 255, 0), (0, 0, 0)) 
                surf.set_alpha(200)
                screen.blit(surf, (10, y))
                y += 25
            except:
                pass

# 方便全域呼叫的實例
dev_tool = DevTool()