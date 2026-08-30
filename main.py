import os
from flask import Flask, jsonify, request
from waitress import serve
from supabase import create_client

app = Flask(__name__)

# Supabase Initialization
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SECRET_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Live & Operational",
        "system": "Sovereign Autonomous Book Empire OS",
        "target_markets": "195+ Countries",
        "modules": ["Make an Idea Engine", "Global Book Publish Room", "Autonomous SEO"]
    })

@app.route("/api/make-idea", methods=["POST"])
def make_idea():
    data = request.json or {}
    topic = data.get("topic", "Dhol Mein Sona and Ancient History")
    return jsonify({
        "status": "Success",
        "generated_idea": f"Master Blueprint for: {topic}",
        "chapters": 12,
        "target_word_count": 150000
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    serve(app, host="0.0.0.0", port=port)