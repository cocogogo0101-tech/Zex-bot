from flask import Flask
from threading import Thread
import os

app = Flask("keep_alive_app")

@app.route("/")
def home():
    return "OK", 200

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    thread = Thread(target=run)
    thread.daemon = True
    thread.start()