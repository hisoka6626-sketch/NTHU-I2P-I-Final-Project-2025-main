import time

class PlayerHandler:
    def __init__(self):
        self._players = {} 
        self._next_id = 0
        self._messages = [] 

    def register(self):
        pid = self._next_id
        self._next_id += 1
        self._players[pid] = {
            "id": pid, 
            "x": 0, 
            "y": 0, 
            "map": "world",
            "direction": "down",
            "moving": False,
            "last_seen": time.time()
        }
        return pid

    def update(self, pid, x, y, map_name, direction="down", moving=False):
        if pid not in self._players:
            return False
        self._players[pid]["x"] = x
        self._players[pid]["y"] = y
        self._players[pid]["map"] = map_name
        self._players[pid]["direction"] = direction
        self._players[pid]["moving"] = moving
        self._players[pid]["last_seen"] = time.time()
        return True

    def list_players(self):
        # ★★★ 修改點：將 5 改為 600 (10分鐘)，避免戰鬥中被踢除 ★★★
        now = time.time()
        to_remove = [pid for pid, p in self._players.items() if now - p["last_seen"] > 600]
        for pid in to_remove:
            del self._players[pid]
        return list(self._players.values())

    def add_message(self, pid, msg):
        self._messages.append({
            "id": pid,
            "msg": msg,
            "time": time.time()
        })
        if len(self._messages) > 50:
            self._messages.pop(0)

    def get_messages(self):
        return self._messages