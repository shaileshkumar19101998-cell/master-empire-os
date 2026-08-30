import os
from flask import Flask, jsonify, request
from waitress import serve
from supabase import create_client, Client

app = Flask(__name__)

# Supabase Initialization from Render Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SECRET_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Supabase Connection Error: {e}")

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "system": "Sovereign Book Publishing OS",
        "target_markets": "195+ Countries",
        "modules": ["Make an Idea", "Global Book Publish Room", "Autonomous SEO"]
    })

@app.route("/api/health", methods=["GET"])
def health_check():
    db_status = "Connected" if supabase else "Not Connected"
    return jsonify({
        "status": "Running smoothly",
        "database_layer": db_status,
        "active_engines": 10
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Sovereign OS Server on port {port} using Waitress...")
    serve(app, host="0.0.0.0", port=port)