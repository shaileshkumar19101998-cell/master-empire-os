import os
from flask import Flask, jsonify

app = Flask(__name__)

# Render Environment Variables (Master 10-Tool Engine Config)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "")
NOWPUBLISH_API_KEY = os.environ.get("NOWPUBLISH_API_KEY", "")

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "system": "Master Autonomous Business OS",
        "version": "2.7",
        "message": "Global Digital Empire Engine Running Smoothly"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)S