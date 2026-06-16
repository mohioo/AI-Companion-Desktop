import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Admin Dashboard Active"

def start_flask():
    # Force threaded execution so it doesn't block the system
    app.run(port=5000, debug=False, use_reloader=False)

def run_server():
    # This keeps the server running in the background safely
    threading.Thread(target=start_flask, daemon=True).start()