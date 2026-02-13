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
import memory

WEBSOCKET_URL = os.getenv("Delta_websocket_url")
API_KEY = os.getenv("Delta_apikey")
API_SECRET = os.getenv("Delta_apisecret")

ws_global = None
reconnect_flag = True
delta_thread = None

# heartbeat
last_heartbeat_time = time.time()
HEARTBEAT_TIMEOUT = 120   # 2 minutes (safe)
lock = threading.Lock()


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


def enable_heartbeat(ws):
    ws.send(json.dumps({
        "type": "enable_heartbeat"
    }))
    print("Heartbeat enabled")


# ================= MESSAGE =================

def on_message(ws, message):
    global last_heartbeat_time

    data = json.loads(message)

    # heartbeat
    if data.get("type") == "heartbeat":
        with lock:
            last_heartbeat_time = time.time()
        return

    # auth
    if data.get("type") == "key-auth":
        if data.get("success"):
            print("Delta auth success")

            enable_heartbeat(ws)
            subscribe(ws, "positions", ["all"])
        else:
            print("Auth failed")
        return

    # position closed
    if data.get("action") == "delete":
        print("Position closed on Delta")
        memory.indicator = 1


# ================= MAIN LOOP =================

def start_delta_ws():
    global ws_global, reconnect_flag, last_heartbeat_time

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

            with lock:
                last_heartbeat_time = time.time()

            ws.run_forever()

        except Exception as e:
            print("WS crash:", e)

        if reconnect_flag:
            print("Reconnect after 3 sec...")
            time.sleep(3)


# ================= WATCHDOG =================
# only reconnect if REALLY dead

def heartbeat_watchdog():
    global ws_global

    while reconnect_flag:
        time.sleep(10)

        with lock:
            diff = time.time() - last_heartbeat_time

        if diff > HEARTBEAT_TIMEOUT:
            print("⚠️ Heartbeat lost for long → reconnect")

            try:
                if ws_global:
                    ws_global.close()
            except:
                pass


# ================= START =================

def run_delta_background():
    global delta_thread, reconnect_flag

    if delta_thread and delta_thread.is_alive():
        print("Delta already running")
        return

    reconnect_flag = True

    delta_thread = threading.Thread(target=start_delta_ws, daemon=True)
    delta_thread.start()

    threading.Thread(target=heartbeat_watchdog, daemon=True).start()


# ================= STOP =================

def stop_delta_ws():
    global ws_global, reconnect_flag

    reconnect_flag = False

    try:
        if ws_global:
            ws_global.close()
    except:
        pass

    ws_global = None
