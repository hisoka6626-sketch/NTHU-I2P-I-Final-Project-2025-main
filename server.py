from server.playerHandler import PlayerHandler
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

PORT = 8989
PLAYER_HANDLER = PlayerHandler()
PLAYER_HANDLER.register() # Server dummy player (optional)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._json(200, {"status": "ok"})
            return
            
        if self.path == "/register":
            pid = PLAYER_HANDLER.register()
            self._json(200, {"message": "registration successful", "id": pid})
            return

        if self.path == "/players":
            self._json(200, {"players": PLAYER_HANDLER.list_players()})
            return
        
        # ★★★ 新增：獲取聊天訊息 ★★★
        if self.path == "/chat":
            self._json(200, {"messages": PLAYER_HANDLER.get_messages()})
            return

        self._json(404, {"error": "not_found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "invalid_json"})
            return

        # --- 處理玩家更新 ---
        if self.path == "/players":
            if "id" not in data:
                self._json(400, {"error": "missing_id"})
                return

            try:
                pid = int(data["id"])
                x = float(data.get("x", 0))
                y = float(data.get("y", 0))
                map_name = str(data.get("map", ""))
                # ★★★ 新增：解析方向與移動狀態 ★★★
                direction = str(data.get("direction", "down"))
                moving = bool(data.get("moving", False))
                
                ok = PLAYER_HANDLER.update(pid, x, y, map_name, direction, moving)
                if not ok:
                    self._json(404, {"error": "player_not_found"})
                    return
                self._json(200, {"success": True})
            except Exception as e:
                print(e)
                self._json(400, {"error": "bad_fields"})
            return

        # --- ★★★ 新增：處理發送聊天訊息 ★★★ ---
        if self.path == "/chat":
            if "id" not in data or "msg" not in data:
                self._json(400, {"error": "missing_fields"})
                return
            PLAYER_HANDLER.add_message(data["id"], data["msg"])
            self._json(200, {"success": True})
            return

        self._json(404, {"error": "not_found"})

    def _json(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == "__main__":
    print(f"[Server] Running on localhost with port {PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()