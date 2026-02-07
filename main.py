from flask import Flask, request, jsonify, render_template
import threading
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from agent1.agent import agent1  # import from other file
from config.mongo import trading_collection
app = Flask(__name__)

# stop events
agent1_stop_event = threading.Event()
executor_stop_event = threading.Event()

# thread refs
agent1_thread = None
executor_thread = None

@app.route("/all_texts", methods=["GET"])
def all_texts():
    data = trading_collection.find({}, {"_id": 0, "text": 1})
    texts = [item["text"] for item in data]
    return {"data": texts}

@app.route("/save_text", methods=["POST"])
def save_text():
    text = request.form.get("text")

    if not text:
        return "No text", 400

    # check duplicate
    exists = trading_collection.find_one({"text": text})

    if exists:
        return "Already exists"

    trading_collection.insert_one({"text": text})
    return "Saved"

# ============ DELETE ONLY THAT TEXT ============
@app.route("/remove_text", methods=["POST"])
def remove_text():
    text = request.form.get("text")

    if not text:
        return "No text", 400

    trading_collection.delete_one({"text": text})
    return "Deleted"

@app.route("/add_symbol")
def form_page():
    return render_template("index.html")

def start_agent1():
    global agent1_thread

    if agent1_thread and agent1_thread.is_alive():
        print("Agent1 already running")
        return

    agent1_thread = threading.Thread(
        target=agent1,
        args=(agent1_stop_event,)
    )
    agent1_thread.daemon = True
    agent1_thread.start()

def stop_agent1():
    agent1_stop_event.set()

@app.route("/")
def index():
    return "Hello, World!"

@app.route("/start_agent1")
def start():
    start_agent1()
    return "Agent1 thread started"

@app.route("/stop_agent1")
def stop():
    stop_agent1()
    return "Agent1 thread stopped"

if __name__ == "__main__":
    app.run(debug=True)

