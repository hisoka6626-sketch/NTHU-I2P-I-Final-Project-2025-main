import pygame as pg
pg.init()
pg.display.init()
pg.display.set_mode((1,1))
from src.scenes.game_scene import GameScene

g = GameScene()
print('chat_overlay type:', type(g.chat_overlay))
print('has update:', hasattr(g.chat_overlay, 'update'))
print('has draw:', hasattr(g.chat_overlay, 'draw'))
print('done')
