import pygame as pg

from src.utils import GameSettings, Logger
from .services import scene_manager, input_manager

from src.scenes.menu_scene import MenuScene
from src.scenes.game_scene import GameScene
from src.scenes.setting_scene import SettingScene
from src.scenes.battle_scene import BattleScene
from src.scenes.catch_scene import CatchScene

class Engine:

    screen: pg.Surface              # Screen Display of the Game
    clock: pg.time.Clock            # Clock for FPS control
    running: bool                   # Running state of the game

    def __init__(self):
        Logger.info("Initializing Engine")

        pg.init()

        self.screen = pg.display.set_mode((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.clock = pg.time.Clock()
        self.running = True

        pg.display.set_caption(GameSettings.TITLE)

        scene_manager.register_scene("menu", MenuScene())
        scene_manager.register_scene("game", GameScene())
        scene_manager.register_scene("setting", SettingScene())
        scene_manager.register_scene("battle", BattleScene())
        scene_manager.register_scene("catch", CatchScene())
        scene_manager.change_scene("menu")

    def run(self):
        Logger.info("Running the Game Loop ...")

        while self.running:
            dt = self.clock.tick(GameSettings.FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

    def handle_events(self):
        input_manager.reset()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            input_manager.handle_events(event)
            
            # Pass events to current scene if it has handle_event method
            current_scene = scene_manager.current_scene
            if hasattr(current_scene, 'handle_event'):
                current_scene.handle_event(event)

    def update(self, dt: float):
        try:
            scene_manager.update(dt)
        except Exception as e:
            from src.utils import Logger
            Logger.error(f"Error during scene manager update: {e}")

    def render(self):
        try:
            self.screen.fill((0, 0, 0))     # Make sure the display is cleared
            scene_manager.draw(self.screen) # Draw the current scene
            pg.display.flip()               # Render the display
        except Exception as e:
            from src.utils import Logger
            Logger.error(f"Error during render: {e}")
            self.screen.fill((0, 0, 0))
            try:
                pg.display.flip()
            except Exception as display_err:
                Logger.error(f"Failed to flip display: {display_err}")

'''
因為 pygame 使用 double buffering（雙緩衝）
更新畫面：

先畫到內部 buffer（看不到）

呼叫 flip() → 把 buffer 顯示出來
'''