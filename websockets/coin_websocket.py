import socketio
import hmac
import hashlib
import json
import os
import threading
from dotenv import load_dotenv
import time
import os
import sys

import memory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# import memory

load_dotenv()

socketEndpoint = os.getenv("Coindcx_websocket_url")
key = os.getenv("Coindcx_apikey")
secret = os.getenv("Coindcx_apisecret")

sio = socketio.Client(reconnection=True)

# ================= EVENTS =================

@sio.event
def connect():
    print("CoinDCX connected")

    secret_bytes = bytes(secret, encoding='utf-8')

    body = {"channel": "coindcx"}
    json_body = json.dumps(body, separators=(',', ':'))

    signature = hmac.new(
        secret_bytes,
        json_body.encode(),
        hashlib.sha256
    ).hexdigest()

    sio.emit('join', {
        'channelName': 'coindcx',
        'authSignature': signature,
        'apiKey': key
    })


@sio.on('df-position-update')
def on_position(data):
    # print("CoinDCX POSITION:", data['data'])
    data = json.loads(data['data'])
    if data[0]['active_pos'] == 0:
        memory.indicator = 1
    
@sio.event
def disconnect():
    print("CoinDCX disconnected")

# ================= THREAD FUNCTIONS =================

def start_coindcx_socket():
    try:
        sio.connect(socketEndpoint, transports=['websocket'])
        sio.wait()
    except Exception as e:
        print("CoinDCX socket error:", e)

def run_coindcx_background():
    t = threading.Thread(target=start_coindcx_socket, daemon=True)
    t.start()

def stop_coindcx_ws():
    sio.disconnect()
