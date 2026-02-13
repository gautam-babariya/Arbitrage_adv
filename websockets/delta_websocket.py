import websocket
import hashlib
import hmac
import json
import time
import threading
from dotenv import load_dotenv
import os
import sys

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import memory   # your shared memory module

WEBSOCKET_URL = os.getenv("Delta_websocket_url")
API_KEY = os.getenv("Delta_apikey")
API_SECRET = os.getenv("Delta_apisecret")

ws_global = None
reconnect_flag = True
delta_thread = None
last_msg_time = time.time()

# ================= EVENTS =================

def on_error(ws, error):
    print("Delta WS error:", error)

def on_close(ws, close_status_code, close_msg):
    print(f"Delta WS closed: {close_status_code} {close_msg}")

def on_open(ws):
    print("Delta WS connected")
    send_authentication(ws)

def generate_signature(secret, message):
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

def send_authentication(ws):
    method = "GET"
    timestamp = str(int(time.time()))
    path = "/live"

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

def subscribe(ws, channel, symbols):
    ws.send(json.dumps({
        "type": "subscribe",
        "payload": {
            "channels": [
                {"name": channel, "symbols": symbols}
            ]
        }
    }))

def on_message(ws, message):
    global last_msg_time
    last_msg_time = time.time()

    data = json.loads(message)

    # auth success
    if data.get("type") == "key-auth":
        if data.get("success"):
            print("Delta auth success")
            subscribe(ws, "positions", ["all"])
        else:
            print("Delta auth failed")
        return

    # position delete detect
    if data.get("action") == "delete":
        print("Position closed on Delta")
        memory.indicator = 1


# ================= MAIN SOCKET LOOP =================

def start_delta_ws():
    global ws_global, reconnect_flag, last_msg_time

    while reconnect_flag:
        try:
            print("Connecting Delta WS...")

            ws = websocket.WebSocketApp(
                WEBSOCKET_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws_global = ws
            last_msg_time = time.time()

            ws.run_forever(
                ping_interval=20,
                ping_timeout=10
            )

        except Exception as e:
            print("WS crash:", e)

        # reconnect delay
        if reconnect_flag:
            print("Reconnecting in 5 sec...")
            time.sleep(5)


# ================= WATCHDOG =================
# if no message for long → reconnect

def watchdog():
    global ws_global
    while reconnect_flag:
        time.sleep(10)

        if time.time() - last_msg_time > 60:
            print("No data from Delta → force reconnect")
            try:
                if ws_global:
                    ws_global.close()
            except:
                pass


# ================= START =================

def run_delta_background():
    global delta_thread, reconnect_flag

    if delta_thread and delta_thread.is_alive():
        print("Delta WS already running")
        return

    reconnect_flag = True

    delta_thread = threading.Thread(target=start_delta_ws, daemon=True)
    delta_thread.start()

    # watchdog thread
    threading.Thread(target=watchdog, daemon=True).start()


# ================= STOP =================

def stop_delta_ws():
    global ws_global, reconnect_flag

    print("Stopping Delta WS...")
    reconnect_flag = False

    try:
        if ws_global:
            ws_global.close()
    except:
        pass

    ws_global = None
