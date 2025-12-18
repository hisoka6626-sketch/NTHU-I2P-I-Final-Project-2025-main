from src.scenes.game_scene import GameScene

g = GameScene()
print('chat_overlay type:', type(g.chat_overlay))
print('has update:', hasattr(g.chat_overlay, 'update'))
print('has draw:', hasattr(g.chat_overlay, 'draw'))
print('done')
