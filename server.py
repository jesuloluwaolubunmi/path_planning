from collections import defaultdict
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse

BASE_DIR = Path(__file__).resolve().parent
APP_FILE = BASE_DIR / "Floor Plan Path Planner.html"
app = FastAPI(title="Floor Plan Path Planner phone bridge")
rooms: dict[str, set[WebSocket]] = defaultdict(set)

@app.get("/", response_class=HTMLResponse)
async def home():
    return FileResponse(APP_FILE)

@app.websocket("/ws/{room_id}")
async def room_socket(websocket: WebSocket, room_id: str):
    # The QR code contains a random room token. Keep it private while connecting.
    if not (8 <= len(room_id) <= 80) or not all(c.isalnum() or c in "-_" for c in room_id):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    peers = rooms[room_id]
    peers.add(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if len(message) > 2_000_000:
                await websocket.close(code=1009)
                break
            # Relay only to the other browser in this private room.
            stale = []
            for peer in tuple(peers):
                if peer is websocket:
                    continue
                try:
                    await peer.send_text(message)
                except Exception:
                    stale.append(peer)
            for peer in stale:
                peers.discard(peer)
    except WebSocketDisconnect:
        pass
    finally:
        peers.discard(websocket)
        if not peers:
            rooms.pop(room_id, None)
