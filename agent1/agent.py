import time
from delta_rest_client import DeltaRestClient
from dotenv import load_dotenv
import hmac
import hashlib
import json
import requests
from flask import json
load_dotenv()
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config.mongo import trading_collection

from Close_coin.close_posotion import close_coin_position
from Close_delta.close_position import close_delta_position

KEY = os.getenv("Delta_apikey")
SECRET = os.getenv("Delta_apisecret")
URL = os.getenv("Delta_baseurl")
COIN_KEY = os.getenv("Coindcx_apikey")
COIN_SECRET = os.getenv("Coindcx_apisecret")
COIN_URL = os.getenv("Coindcx_url_position")

delta_client = DeltaRestClient(
  base_url=URL,
  api_key=KEY,
  api_secret=SECRET
)

def get_all_texts():
    data = trading_collection.find({}, {"_id": 0, "text": 1})
    return [item["text"] for item in data]

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

def get_position_delta(symbol: str):
    try:
        response = delta_client.get_ticker(symbol)
        product_id = response["product_id"]
        position = delta_client.get_position(product_id)
        return position
    except Exception as e:
        return {"error": str(e)}

def agent1(stop_event):
    while not stop_event.is_set():
        list1 = get_all_texts()
        list2 = []

        for s in list1:
            s = s.replace("B-", "")
            s = s.replace("_USDT", "USD")   # USDT → USD
            s = s.replace("_", "")          # remove remaining _
            list2.append(s)
        list3 = []

        for symbol in list1:
            data = get_position_coindcx(symbol)

            flag = 0

            if data and len(data) > 0:
                pos = data[0].get("active_pos") or 0
                if pos > 0 or pos < 0:
                    flag = 1

            list3.append(flag)

        list4 = []

        for symbol in list2:
            data = get_position_delta(symbol)

            flag = 0

            if isinstance(data, list) and data:
                if data[0].get("size") and data[0]["size"] > 0:
                    flag = 1
                if data[0].get("size") and data[0]["size"] < 0:
                    flag = 1

            elif isinstance(data, dict):
                if data.get("size") and data["size"] > 0:
                    flag = 1
                if data.get("size") and data["size"] < 0:
                    flag = 1

            list4.append(flag)

        
        
        for i, (a, b) in enumerate(zip(list3, list4)):
            if (a, b) in [(0, 1)]:
                print("detect delta",list2[i])
                close_delta_position(list2[i])
            elif (a, b) in [(1, 0)]:
                print("detect coin",list1[i])  
                close_coin_position(list1[i])  
                
        time.sleep(1)
    print("Agent1 stopped")
