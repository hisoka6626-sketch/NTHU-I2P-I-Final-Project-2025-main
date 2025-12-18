import pygame as pg
from src.utils import GameSettings
from src.core import GameManager
from src.interface.components.component import UIComponent
from src.interface.components.button import Button
from src.core.services import input_manager
from src.sprites import Sprite


class ShopPanel(UIComponent):
    """商店面板，支援買賣功能，顯示商品清單與玩家物品清單。"""

    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.is_open = False
        self.mode = "SELL"  # 預設模式

        # ------------------------------
        # UI 畫框 (標準大尺寸 960x650)
        # ------------------------------
        raw = pg.image.load("assets/images/UI/raw/UI_Flat_Frame03a.png").convert_alpha()
        frame_w, frame_h = 960, 650
        self.surface = pg.transform.smoothscale(raw, (frame_w, frame_h))

        x = (GameSettings.SCREEN_WIDTH - frame_w) // 2
        y = (GameSettings.SCREEN_HEIGHT - frame_h) // 2
        self.rect = pg.Rect(x, y, frame_w, frame_h)

        # Fonts
        self.font_title = pg.font.Font("assets/fonts/Minecraft.ttf", 42)
        self.font_text = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        self.font_small = pg.font.Font("assets/fonts/Minecraft.ttf", 20)

        # 關閉按鈕
        self.close_button = Sprite("UI/button_x.png", (50, 50))
        self.close_rect = pg.Rect(x + frame_w - 70, y + 25, 50, 50)

        # SELL/BUY 切換按鈕 (加大)
        self.sell_button = Button(
            img_path="UI/raw/UI_Flat_Button02a_4.png",
            img_hovered_path="UI/raw/UI_Flat_Button02a_3.png",
            x=self.rect.left + 50,
            y=self.rect.top + 90, 
            width=160,
            height=55,
            label="SELL",
            font=self.font_text,
            on_click=lambda: self._set_mode("SELL")
        )
        
        self.buy_button = Button(
            img_path="UI/raw/UI_Flat_Button02a_4.png",
            img_hovered_path="UI/raw/UI_Flat_Button02a_3.png",
            x=self.rect.left + 230,
            y=self.rect.top + 90,
            width=160,
            height=55,
            label="BUY",
            font=self.font_text,
            on_click=lambda: self._set_mode("BUY")
        )

        # 滾動偏移
        self.scroll_item = 0
        self.SCROLL_SPEED = 30

        # 內容裁切區域 (加大寬度)
        # x+50, y+170, 寬860, 高420
        self.clip_item = pg.Rect(x + 50, y + 170, 860, 420)

        # 商品定義
        self.shop_items = [
            {"name": "Heal Potion", "sprite_path": "ingame_ui/potion.png", "price": 100, "option": 2},
            {"name": "Strength Potion", "sprite_path": "ingame_ui/potion.png", "price": 100, "option": 3},
            {"name": "Defense Potion", "sprite_path": "ingame_ui/potion.png", "price": 100, "option": 4},
            {"name": "Shield", "sprite_path": "ingame_ui/shield.png", "price": 20, "option": 6},
            {"name": "Magic Hand", "sprite_path": "ingame_ui/magic_hand.png", "price": 20, "option": 8},
            {"name": "Pokeball", "sprite_path": "ingame_ui/ball.png", "price": 20, "option": 1},
        ]

        # 購買/賣出按鈕列表
        self.action_buttons = []
        self._init_action_buttons()

        # coin 圖示
        self.coin_sprite = Sprite("ingame_ui/coin.png", (40, 40))
        
        # 滾動條顏色
        self.COLOR_SCROLL_HANDLE = (50, 50, 50)

    def _init_action_buttons(self):
        """初始化購買/賣出按鈕。"""
        self.action_buttons = []
        items = self._get_current_items()
        row_h = 80 # 項目高度增加
        
        for i, item in enumerate(items):
            # 按鈕靠右對齊
            btn_x = self.clip_item.right - 160
            btn_y = 0 

            if self.mode == "BUY":
                btn = Button(
                    img_path="UI/button_shop.png",
                    img_hovered_path="UI/button_shop_hover.png",
                    x=btn_x,
                    y=btn_y,
                    width=130,
                    height=50,
                    on_click=lambda item_name=item["name"], price=item["price"]: self._buy_item(item_name, price)
                )
            else:  # SELL mode
                sell_price = item.get("price", 10) // 2 
                btn = Button(
                    img_path="UI/button_shop.png",
                    img_hovered_path="UI/button_shop_hover.png",
                    x=btn_x,
                    y=btn_y,
                    width=130,
                    height=50,
                    on_click=lambda item_data=item, sell_price=sell_price: self._sell_item(item_data, sell_price)
                )
            self.action_buttons.append(btn)

    def _set_mode(self, mode: str):
        self.mode = mode
        self.scroll_item = 0
        self._init_action_buttons()

    def _get_current_items(self):
        if self.mode == "BUY":
            return self.shop_items
        else:
            items = []
            if hasattr(self.game_manager.bag, '_items_data'):
                for item in self.game_manager.bag._items_data:
                    if item["name"] != "Coins" and item.get("count", 0) > 0:
                        sell_item = item.copy()
                        ref_price = 20
                        for shop_i in self.shop_items:
                            if shop_i["name"] == item["name"]:
                                ref_price = shop_i["price"]
                                break
                        sell_item["price"] = ref_price
                        items.append(sell_item)
            return items

    def _buy_item(self, item_name: str, price: int) -> None:
        coins = self._get_coin_count()
        if coins < price:
            return 

        self._deduct_coins(price)
        self._add_item_to_bag(item_name)

    def _sell_item(self, item_data: dict, sell_price: int) -> None:
        item_name = item_data["name"]
        self._add_coins(sell_price)
        self._remove_item_from_bag(item_name)
        self._init_action_buttons()

    # --- Helper methods for bag operations ---
    def _get_coin_count(self) -> int:
        return self.game_manager.bag.get_coins()

    def _deduct_coins(self, amount: int) -> None:
        self.game_manager.bag.add_coins(-amount)

    def _add_coins(self, amount: int) -> None:
        self.game_manager.bag.add_coins(amount)

    def _remove_item_from_bag(self, item_name: str) -> None:
        items = self.game_manager.bag._items_data
        for item in items:
            if item["name"] == item_name:
                item["count"] -= 1
                if item["count"] <= 0:
                    items.remove(item)
                return

    def _add_item_to_bag(self, item_name: str) -> None:
        items = self.game_manager.bag._items_data
        
        item_config = {i["name"]: i for i in self.shop_items}
        config = item_config.get(item_name)
        
        if not config: return
        
        for item in items:
            if item["name"] == item_name:
                item["count"] += 1
                return
        
        new_item = {
            "name": item_name,
            "count": 1,
            "sprite_path": config["sprite_path"],
            "option": config["option"]
        }
        items.append(new_item)

    # -----------------------------------------------------
    # UI Loop
    # -----------------------------------------------------
    def open(self):
        self.is_open = True
        self.scroll_item = 0
        self._init_action_buttons()

    def close(self):
        self.is_open = False

    def update(self, dt: float):
        if not self.is_open:
            return

        if self.close_rect.collidepoint(input_manager.mouse_pos) and input_manager.mouse_pressed(1):
            self.close()

        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()

        self.sell_button.update(dt)
        self.buy_button.update(dt)

        # 滾動處理
        mx, my = input_manager.mouse_pos
        wheel = input_manager.mouse_wheel

        if wheel != 0:
            if self.clip_item.collidepoint((mx, my)):
                self.scroll_item += wheel * self.SCROLL_SPEED

        # 限制滾動
        items = self._get_current_items()
        row_h = 80
        content_h = max(self.clip_item.height, len(items) * row_h)
        min_scroll = self.clip_item.height - content_h
        
        self.scroll_item = max(min_scroll, min(0, self.scroll_item))

        # 更新動態按鈕位置
        start_y = self.clip_item.top + 15
        
        for i, btn in enumerate(self.action_buttons):
            item_y_offset = i * row_h
            screen_y = start_y + item_y_offset + self.scroll_item + 10 # +10 居中
            
            btn.hitbox.y = screen_y
            
            # 可見範圍檢查
            if self.clip_item.top <= screen_y <= self.clip_item.bottom - btn.hitbox.height:
                btn.update(dt)
            else:
                btn.hitbox.y = -1000

    def draw(self, screen: pg.Surface):
        if not self.is_open:
            return

        # 1. 背景遮罩
        dark = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        dark.set_alpha(180)
        dark.fill((0, 0, 0))
        screen.blit(dark, (0, 0))

        # 2. 面板
        screen.blit(self.surface, self.rect)

        # 3. 標題
        title = self.font_title.render("ITEM SHOP", True, (0, 0, 0))
        screen.blit(title, (self.rect.left + 30, self.rect.top + 30))

        self.sell_button.draw(screen)
        self.buy_button.draw(screen)

        # 模式指示文字 (深色)
        mode_color = (0, 100, 0) if self.mode == "BUY" else (180, 50, 0)
        mode_text = self.font_text.render(f"Current Mode: {self.mode}", True, mode_color)
        screen.blit(mode_text, (self.rect.left + 450, self.rect.top + 105))

        # 4. 商品列表
        items = self._get_current_items()
        row_h = 80
        content_h = max(self.clip_item.height, len(items) * row_h)
        temp_surface = pg.Surface((self.clip_item.width, content_h), pg.SRCALPHA)
        
        iy = self.scroll_item 
        draw_y = 0
        
        # 繪製列表內容
        for i, item in enumerate(items):
            # 分隔線 (深灰色)
            pg.draw.line(temp_surface, (180, 180, 180), (10, draw_y + row_h - 2), (self.clip_item.width - 20, draw_y + row_h - 2), 2)

            # 圖示
            icon = Sprite(item["sprite_path"], (56, 56))
            icon.rect.topleft = (10, draw_y + 12)
            icon.draw(temp_surface)
            
            # ★★★ 藥水亮色邊框 ★★★
            border_col = None
            if "Heal" in item["name"]: border_col = (0, 255, 0) # Bright Green
            elif "Strength" in item["name"]: border_col = (255, 0, 0) # Bright Red
            elif "Defense" in item["name"]: border_col = (50, 100, 255) # Bright Blue
            
            if border_col:
                pg.draw.rect(temp_surface, border_col, icon.rect, 3)

            # 名稱 (純黑)
            name = self.font_text.render(item["name"], True, (0, 0, 0))
            temp_surface.blit(name, (80, draw_y + 25))

            # 價格與數量
            price = item.get("price", 20)
            if self.mode == "SELL": price //= 2
            
            # 價格 (純黑)
            price_txt = self.font_text.render(f"${price}", True, (0, 0, 0))
            temp_surface.blit(price_txt, (450, draw_y + 25))
            
            # 擁有數量 (SELL 模式)
            if self.mode == "SELL":
                count = item.get("count", 0)
                # 數量也改為深色，不要淺灰
                cnt_txt = self.font_small.render(f"Owned: {count}", True, (50, 50, 50))
                temp_surface.blit(cnt_txt, (300, draw_y + 28))

            draw_y += row_h

        # 繪製列表到螢幕
        screen.set_clip(self.clip_item)
        screen.blit(temp_surface, (self.clip_item.x, self.clip_item.y + self.scroll_item))
        
        # 繪製按鈕
        for btn in self.action_buttons:
            if self.clip_item.top <= btn.hitbox.y <= self.clip_item.bottom - btn.hitbox.height:
                btn.draw(screen)
                
        # 滾動條
        self._draw_scrollbar(screen, self.clip_item, content_h, self.scroll_item)
        
        screen.set_clip(None)

        # 5. 底部金幣
        coins = self._get_coin_count()
        
        # 金幣背景框
        coin_bg_rect = pg.Rect(0, 0, 240, 60)
        coin_bg_rect.centerx = self.rect.centerx
        coin_bg_rect.bottom = self.rect.bottom - 25
        pg.draw.rect(screen, (240, 240, 240), coin_bg_rect, border_radius=12)
        pg.draw.rect(screen, (0, 0, 0), coin_bg_rect, 3, border_radius=12)
        
        self.coin_sprite.rect.midleft = (coin_bg_rect.left + 20, coin_bg_rect.centery)
        self.coin_sprite.draw(screen)
        
        coin_text = self.font_text.render(f"{coins}", True, (0, 0, 0))
        screen.blit(coin_text, (self.coin_sprite.rect.right + 15, coin_bg_rect.centery - coin_text.get_height()//2))

        # 關閉按鈕
        self.close_button.rect.topleft = (self.close_rect.x, self.close_rect.y)
        self.close_button.draw(screen)

    def _draw_scrollbar(self, screen, clip_rect, content_height, scroll_offset):
        if content_height <= clip_rect.height:
            return

        bar_w = 10 # 加寬
        margin = 5
        track_x = clip_rect.right - bar_w - margin
        track_y = clip_rect.top
        track_h = clip_rect.height

        viewable_ratio = clip_rect.height / content_height
        handle_h = max(40, track_h * viewable_ratio)
        
        scroll_ratio = abs(scroll_offset) / (content_height - clip_rect.height)
        track_scrollable_h = track_h - handle_h
        handle_y = track_y + (track_scrollable_h * scroll_ratio)

        # 繪製滑塊 (深色圓角)
        pg.draw.rect(screen, self.COLOR_SCROLL_HANDLE, (track_x, handle_y, bar_w, handle_h), border_radius=5)