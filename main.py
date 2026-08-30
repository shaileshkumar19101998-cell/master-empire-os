import os
from flask import Flask, jsonify
from waitress import serve
from supabase import create_client, Client

app = Flask(__name__)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SECRET_KEY")
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error: {e}")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "online", "system": "Sovereign Book Publishing OS", "markets": "195+ Countries"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    serve(app, host="0.0.0.0", port=port)
