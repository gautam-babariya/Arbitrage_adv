import os
import time
import json
import hmac
import hashlib
import requests
from dotenv import load_dotenv
load_dotenv()

COIN_KEY = os.getenv("Coindcx_apikey")
COIN_SECRET = os.getenv("Coindcx_apisecret")
COIN_URL = os.getenv("Coindcx_url_position")

def get_position_coindcx(symbol: str):
    """
    Normal blocking version
    """

    secret_bytes = COIN_SECRET.encode("utf-8")
    timestamp = int(time.time() * 1000)

    body = {
        "timestamp": timestamp,
        "page": "1",
        "size": "10",
        "pairs": symbol,
        "margin_currency_short_name": ["INR"]
    }

    json_body = json.dumps(body, separators=(",", ":"))

    signature = hmac.new(
        secret_bytes,
        json_body.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": COIN_KEY,
        "X-AUTH-SIGNATURE": signature
    }

    try:
        resp = requests.post(COIN_URL, data=json_body, headers=headers)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def exit_position(id):
    api_key = os.getenv("Coindcx_apikey")
    api_secret = os.getenv("Coindcx_apisecret")
    
    secret_bytes = bytes(api_secret, encoding='utf-8')

    # Generating a timestamp
    timeStamp = int(round(time.time() * 1000))

    # Request body
    body = {
        "timestamp": timeStamp,
        "id": id
    }

    json_body = json.dumps(body, separators=(',', ':'))

    # Generate signature
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()

    url = os.getenv("Coindcx_url_exit")

    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': api_key,
        'X-AUTH-SIGNATURE': signature
    }

    # Send request
    response = requests.post(url, data=json_body, headers=headers)

    try:
        return response.json()
    except:
        return {"error": "Invalid Response", "raw": response.text}
    
def close_coin_position(sym):
    position_data = get_position_coindcx(sym)
    if "error" in position_data:
        return {"error": position_data["error"]}
    elif not position_data or not isinstance(position_data, list) or len(position_data) == 0:
        return {"error": "No position data found"}
    else:   
        ids = position_data[0]["id"]
        result = exit_position(ids)
        return result

# print(close_position("B-SWARMS_USDT"))
