import pygame as pg
from src.utils import Logger
from src.core import services

class StoryManager:
    def __init__(self, game_manager, dialogue_box, confirmation_panel, game_scene):
        self.game_manager = game_manager
        self.dialogue_box = dialogue_box
        self.confirmation_panel = confirmation_panel
        self.game_scene = game_scene 
        
        self.current_event = None

        self.confirmation_panel.on_confirm = self._on_confirm_story
        self.confirmation_panel.on_cancel = self._on_cancel_story

    def update(self, dt):
        if self.dialogue_box.finished:
            self.dialogue_box.finished = False
            self._on_dialogue_finished()

    def handle_input(self, event):
        if self.confirmation_panel.is_open or self.dialogue_box.is_open:
            return True
        return False

    # --- 互動入口 ---
    def interact_aerial(self):
        if self.game_manager.story_flags.get("in_fog_world", False):
            return False
        
        self.confirmation_panel.open()
        return True

    def interact_shopkeeper(self):
        if not self.game_manager.story_flags.get("met_shopkeeper", False):
            self.dialogue_box.start_dialogue([
                "Welcome, stranger!",
                "The coins here are imbued with strange energy.",
                "Be careful how you spend them."
            ], "Shopkeeper")
            self.game_manager.story_flags["met_shopkeeper"] = True
            return True
        return False

    # --- Fog World Stories ---
    def start_fog_monologue(self):
        script = [
            "Wait... where is this?",
            "Why is there so much fog everywhere?",
            "And why does this scenery feel so... familiar?",
            "(An unsettling silence surrounds you.)"
        ]
        self.dialogue_box.start_dialogue(script, "James")

    # [修改] Gym Story - 依照您的要求更新文本
    def start_gym_story(self):
        script = [
            "(Headache splitting...) I... I've been here before?!",
            "Wait, what is that?!!!!",
            "What is that monster?"
        ]
        self.dialogue_box.start_dialogue(script, "James")
        self.current_event = "gym_scare_event"

    # --- 內部回調 ---
    def _on_confirm_story(self):
        Logger.info("Player confirmed story mode.")
        

        script = [
            "Welcome to Silent Hill."
        ]
        self.dialogue_box.start_dialogue(script, "James")
        self.current_event = "silent_hill_transition"

    def _on_cancel_story(self):
        pass

    def _on_dialogue_finished(self):
        if self.current_event == "silent_hill_transition":
            Logger.info("Story finished: Teleporting to Fog World.")
            
            self.game_scene.activate_fog()
            self.game_manager.switch_map("fog world.tmx", force_pos=(16, 29))
            
            self.game_manager.story_flags["silent_hill_completed"] = True
            self.game_manager.story_flags["in_fog_world"] = True
            self.current_event = None
            
        elif self.current_event == "gym_scare_event":
            # Gym 劇情結束，觸發恐怖畫面
            Logger.info("Gym story finished: Triggering Jumpscare!")
            self.game_scene.trigger_gym_horror_event()
            self.current_event = None