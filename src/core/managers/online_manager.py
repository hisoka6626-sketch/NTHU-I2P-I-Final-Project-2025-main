import requests
import threading
import time
from src.utils import Logger

class OnlineManager:
    def __init__(self):
        self.server_url = "http://127.0.0.1:8989"
        self.player_id = None
        self.other_players = []
        self.chat_messages = [] 
        self._register()

    def _register(self):
        try:
            res = requests.get(f"{self.server_url}/register")
            if res.status_code == 200:
                self.player_id = res.json()["id"]
                Logger.info(f"Registered online with ID: {self.player_id}")
        except Exception as e:
            Logger.error(f"Failed to connect to server: {e}")

    def enter(self): pass
    def exit(self): pass

    def update(self, x, y, map_name, direction="down", moving=False):
        if self.player_id is None: return

        def _task():
            try:
                # 1. 上傳自己的狀態
                payload = {
                    "id": self.player_id,
                    "x": x, "y": y,
                    "map": map_name,
                    "direction": direction, 
                    "moving": moving        
                }
                requests.post(f"{self.server_url}/players", json=payload)

                # 2. 下載其他玩家
                res = requests.get(f"{self.server_url}/players")
                if res.status_code == 200:
                    all_players = res.json()["players"]
                    
                    # ★★★ 修正重點：強制轉型成字串來比對，避免 1 != "1" 的問題 ★★★
                    my_id_str = str(self.player_id)
                    self.other_players = [
                        p for p in all_players 
                        if str(p.get("id")) != my_id_str
                    ]

                # 3. 下載聊天訊息
                chat_res = requests.get(f"{self.server_url}/chat")
                if chat_res.status_code == 200:
                    self.chat_messages = chat_res.json()["messages"]
            except Exception:
                pass

        threading.Thread(target=_task, daemon=True).start()
        return self.other_players

    def get_list_players(self):
        return self.other_players
    
    def get_chat_history(self):
        return self.chat_messages

    def send_message(self, msg):
        if self.player_id is None: return
        def _send():
            try:
                requests.post(f"{self.server_url}/chat", json={"id": self.player_id, "msg": msg})
            except:
                pass
        threading.Thread(target=_send, daemon=True).start()