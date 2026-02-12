import websocket
import hashlib
import hmac
import json
import time
import threading
from dotenv import load_dotenv
load_dotenv()
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import memory

WEBSOCKET_URL = os.getenv("Delta_websocket_url")
API_KEY = os.getenv("Delta_apikey")
API_SECRET = os.getenv("Delta_apisecret")

ws_global = None   # 👈 store socket here

# ================= EVENTS =================

def on_error(ws, error):
    print(f"Socket Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Socket closed: {close_status_code} {close_msg}")

def on_open(ws):
    print("Delta socket opened")
    send_authentication(ws)

def send_authentication(ws):
    method = 'GET'
    timestamp = str(int(time.time()))
    path = '/live'
    signature_data = method + timestamp + path
    signature = generate_signature(API_SECRET, signature_data)

    ws.send(json.dumps({
        "type": "key-auth",
        "payload": {
            "api-key": API_KEY,
            "signature": signature,
            "timestamp": timestamp
        }
    }))

def generate_signature(secret, message):
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

def subscribe(ws, channel, symbols):
    ws.send(json.dumps({
        "type": "subscribe",
        "payload": {
            "channels": [
                {"name": channel, "symbols": symbols}
            ]
        }
    }))

def on_message(ws, json_message):
    message = json.loads(json_message)

    if message.get('type') == 'key-auth':
        if message.get('success'):
            print("Delta auth ok")
            subscribe(ws, "positions", ["all"])
        return

    # detect position delete
    if message.get("action") == "delete":
        memory.indicator = 1

# ================= START =================

def start_delta_ws():
    global ws_global

    ws = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.on_open = on_open
    ws_global = ws   # store reference

    ws.run_forever()

def run_delta_background():
    t = threading.Thread(target=start_delta_ws, daemon=True)
    t.start()

# ================= STOP =================

def stop_delta_ws():
    global ws_global
    print("Stopping Delta socket...")
    if ws_global:
        ws_global.close()
        ws_global = None
