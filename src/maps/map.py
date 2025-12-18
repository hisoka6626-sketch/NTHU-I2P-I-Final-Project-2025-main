import pygame as pg
import pytmx

from src.utils import load_tmx, Position, GameSettings, PositionCamera, Teleport

class Map:
    # 地圖屬性
    path_name: str
    tmxdata: pytmx.TiledMap
    # Position Argument
    spawn: Position
    teleporters: list[Teleport]
    # Rendering Properties
    _surface: pg.Surface
    
    # Collision & Interaction Rects
    _collision_map: list[pg.Rect]
    _bush_rects: list[pg.Rect]
    _altar_rects: list[pg.Rect]
    _shop_keeper_rects: list[pg.Rect]
    _hospital_rects: list[pg.Rect]
    _casino_rects: list[pg.Rect] # 新增 Casino (Thermal) 互動區域列表

    def __init__(self, path: str, tp: list[Teleport], spawn: Position):
        self.path_name = path
        self.tmxdata = load_tmx(path)
        self.spawn = spawn
        self.teleporters = tp

        pixel_w = self.tmxdata.width * GameSettings.TILE_SIZE
        pixel_h = self.tmxdata.height * GameSettings.TILE_SIZE
        
        # Ensure spawn is within the map pixel bounds
        max_x = max(0, pixel_w - GameSettings.TILE_SIZE)
        max_y = max(0, pixel_h - GameSettings.TILE_SIZE)
        if self.spawn.x < 0: self.spawn.x = 0
        elif self.spawn.x > max_x: self.spawn.x = max_x
        if self.spawn.y < 0: self.spawn.y = 0
        elif self.spawn.y > max_y: self.spawn.y = max_y

        # Render Map Surface
        self._surface = pg.Surface((pixel_w, pixel_h), pg.SRCALPHA)
        self._render_all_layers(self._surface)
        
        # Build Collision and Interaction Maps based on Layer Names
        self._build_map_logic()

    def update(self, dt: float):
        return

    def draw(self, screen: pg.Surface, camera: PositionCamera):
        screen.blit(self._surface, camera.transform_position(Position(0, 0)))
        if GameSettings.DRAW_HITBOXES:
            for rect in self._collision_map:
                pg.draw.rect(screen, (255, 0, 0), camera.transform_rect(rect), 1)
            for rect in self._hospital_rects:
                pg.draw.rect(screen, (0, 255, 0), camera.transform_rect(rect), 1)
            for rect in self._shop_keeper_rects:
                pg.draw.rect(screen, (0, 0, 255), camera.transform_rect(rect), 1)
            for rect in self._casino_rects: # 繪製 Casino 判定框 (Debug用)
                pg.draw.rect(screen, (255, 215, 0), camera.transform_rect(rect), 1)

    def check_collision(self, obj) -> bool:
        # [修改] 在這裡引入 dev_tool 以避免 Circular Import
        from src.core.dev_tools import dev_tool
        
        # [DEV MODE] 如果穿牆模式開啟，直接無視碰撞
        if dev_tool.active and dev_tool.noclip_mode:
            return False

        if isinstance(obj, pg.Rect):
            rect = obj
        else:
            rect = pg.Rect(
                obj.x, obj.y,
                GameSettings.TILE_SIZE, GameSettings.TILE_SIZE
            )

        for collision_rect in self._collision_map:
            if rect.colliderect(collision_rect):
                return True
        return False

    def check_teleport(self, pos: Position) -> Teleport | None:
        player_rect = pg.Rect(pos.x, pos.y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        for tp in self.teleporters:
            teleport_rect = pg.Rect(tp.pos.x, tp.pos.y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
            if player_rect.colliderect(teleport_rect):
                # Additional check: center distance
                pc_x = pos.x + GameSettings.TILE_SIZE // 2
                pc_y = pos.y + GameSettings.TILE_SIZE // 2
                tc_x = tp.pos.x + GameSettings.TILE_SIZE // 2
                tc_y = tp.pos.y + GameSettings.TILE_SIZE // 2
                if ((pc_x - tc_x)**2 + (pc_y - tc_y)**2)**0.5 <= GameSettings.TILE_SIZE:
                    return tp
        return None

    # --- Interaction Checkers ---
    def _check_interaction(self, pos: Position, rect_list: list[pg.Rect]) -> pg.Rect | None:
        # 使用中心點進行判定，手感較好
        pc_x = pos.x + GameSettings.TILE_SIZE // 2
        pc_y = pos.y + GameSettings.TILE_SIZE // 2
        for rect in rect_list:
            if rect.collidepoint(pc_x, pc_y):
                return rect
        return None

    def get_bush_at_pos(self, pos: Position) -> pg.Rect | None:
        return self._check_interaction(pos, self._bush_rects)

    def get_altar_at_pos(self, pos: Position) -> pg.Rect | None:
        return self._check_interaction(pos, self._altar_rects)

    def get_shop_keeper_at_pos(self, pos: Position) -> pg.Rect | None:
        return self._check_interaction(pos, self._shop_keeper_rects)

    def get_hospital_at_pos(self, pos: Position) -> pg.Rect | None:
        return self._check_interaction(pos, self._hospital_rects)

    def get_casino_at_pos(self, pos: Position) -> pg.Rect | None:
        # 新增：取得 Casino (Thermal) 互動位置
        return self._check_interaction(pos, self._casino_rects)

    # --- Internal Logic Building ---
    def _render_all_layers(self, target: pg.Surface) -> None:
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                
                layer_opacity = getattr(layer, 'opacity', 1.0)
                alpha_value = int(layer_opacity * 255)

                for x, y, gid in layer:
                    if gid == 0: continue
                    image = self.tmxdata.get_tile_image_by_gid(gid)
                    if image:
                        image = pg.transform.scale(image, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
                        
                        if alpha_value < 255:
                            image.set_alpha(alpha_value)
                            
                        target.blit(image, (x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE))

    def _build_map_logic(self):
        """
        Reads TMX layers and assigns tiles to collision or interaction lists based on layer name keywords.
        """
        self._collision_map = []
        self._bush_rects = []
        self._altar_rects = []
        self._shop_keeper_rects = []
        self._hospital_rects = []
        self._casino_rects = [] # 初始化

        # Keywords for obstacles (Block movement)
        collision_keywords = [
            'collision', 'obstacle', 'wall', 'building', 'house', 'tree', 
            'rock', 'cliff', 'mountain', 'water', 'ocean', 'river', 'pond', 
            'lake', 'table', 'chair', 'counter', 'fall'
        ]
        
        # Iterate all visible tile layers
        for layer in self.tmxdata.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            
            name = layer.name.lower()
            
            # Identify layer type
            is_collision = any(k in name for k in collision_keywords)
            
            # Specific Interaction Layers
            is_bush = 'bush' in name
            is_altar = 'altar' in name
            is_shop = ('shop' in name or 'keeper' in name) and 'hospital' not in name
            is_hospital = 'hospital' in name or 'clinic' in name or 'medical' in name
            
            # 新增：偵測 "thermal" 關鍵字作為 Casino
            is_casino = 'thermal' in name
            
            # Optimization: Skip decorative layers (unless it's collision)
            if not (is_collision or is_bush or is_altar or is_shop or is_hospital or is_casino):
                continue

            for x, y, gid in layer:
                if gid == 0: continue
                
                # Exclude specific interaction (Hardcoded fix for new map)
                if "new map" in self.path_name and x == 23 and y == 21:
                    if is_hospital: 
                        continue
                
                rect = pg.Rect(
                    x * GameSettings.TILE_SIZE,
                    y * GameSettings.TILE_SIZE,
                    GameSettings.TILE_SIZE,
                    GameSettings.TILE_SIZE
                )
                
                if is_hospital:
                    self._hospital_rects.append(rect)
                elif is_shop: 
                    self._shop_keeper_rects.append(rect)
                elif is_casino: # 加入 Casino 列表
                    self._casino_rects.append(rect)
                
                if is_bush:
                    self._bush_rects.append(rect)
                
                if is_altar:
                    self._altar_rects.append(rect)

                if is_collision:
                    self._collision_map.append(rect)

        # Final Step: Remove collisions at Teleporter positions
        if self.teleporters:
            tp_coords = set()
            for tp in self.teleporters:
                tx = tp.pos.x // GameSettings.TILE_SIZE
                ty = tp.pos.y // GameSettings.TILE_SIZE
                tp_coords.add((tx, ty))
            
            self._collision_map = [
                r for r in self._collision_map 
                if (r.x // GameSettings.TILE_SIZE, r.y // GameSettings.TILE_SIZE) not in tp_coords
            ]

    @classmethod
    def from_dict(cls, data: dict) -> "Map":
        tp = [Teleport.from_dict(t) for t in data["teleport"]]
        pos = Position(data["player"]["x"] * GameSettings.TILE_SIZE, data["player"]["y"] * GameSettings.TILE_SIZE)
        return cls(data["path"], tp, pos)

    def to_dict(self):
        return {
            "path": self.path_name,
            "teleport": [t.to_dict() for t in self.teleporters],
            "player": {
                "x": self.spawn.x // GameSettings.TILE_SIZE,
                "y": self.spawn.y // GameSettings.TILE_SIZE,
            }
        }