import pygame as pg
from pytmx import load_pygame, TiledMap
from pathlib import Path
from .logger import Logger
from .settings import GameSettings

ASSETS_DIR = Path("assets")

def load_img(path: str) -> pg.Surface:
    Logger.info(f"Loading image: {path}")
    img_path = ASSETS_DIR / "images" / path
    try:
        img = pg.image.load(str(img_path))
        return img.convert_alpha()
    except Exception as e:
        Logger.error(f"Failed to load image: {path} ({e}) - using placeholder")
        # create a visible placeholder surface sized to TILE_SIZE
        placeholder = pg.Surface((GameSettings.TILE_SIZE, GameSettings.TILE_SIZE), pg.SRCALPHA)
        placeholder.fill((255, 0, 255))
        return placeholder.convert_alpha()

def load_sound(path: str) -> pg.mixer.Sound:
    Logger.info(f"Loading sound: {path}")
    sound = pg.mixer.Sound(str(ASSETS_DIR / "sounds" / path))
    if not sound:
        Logger.error(f"Failed to load sound: {path}")
    return sound

def load_font(path: str, size: int) -> pg.font.Font:
    Logger.info(f"Loading font: {path}")
    font = pg.font.Font(str(ASSETS_DIR / "fonts" / path), size)
    if not font:
        Logger.error(f"Failed to load font: {path}")
    return font

def load_tmx(path: str) -> TiledMap:
    tmxdata = load_pygame(str(ASSETS_DIR / "maps" / path))
    if tmxdata is None:
        Logger.error(f"Failed to load map: {path}")
    return tmxdata
