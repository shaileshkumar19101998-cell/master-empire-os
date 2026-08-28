import os
import http.server
import socketserver
import json
import random
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", 8080))

# ग्लोबल मार्केट ट्रेंड्स और बुक्स का डायनामिक बैंक जो दुनिया भर की डिमांड को ट्रैक करेगा
GLOBAL_BOOK_TRENDS = [
    {
        "book": "The AI Revolution in Small Business: 2026 Blueprint",
        "category": "Technology & AI",
        "demand": "Very High",
        "top_country": "United States & Canada",
        "score": 9.8
    },
    {
        "book": "Ancient Philosophy for Modern Anxiety: Stoicism Today",
        "category": "Self-Help & Psychology",
        "demand": "High",
        "top_country": "United Kingdom & Europe",
        "score": 9.5
    },
    {
        "book": "Passive Income Ecosystems: Global E-Commerce Strategies",
        "category": "Business & Wealth",
        "demand": "Explosive",
        "top_country": "Australia & United States",
        "score": 9.9
    },
    {
        "book": "The Longevity Diet: Biohacking Cellular Health",
        "category": "Health & Wellness",
        "demand": "Steady High",
        "top_country": "Germany & Japan",
        "score": 9.2
    },
    {
        "book": "Mastering Digital Marketing & Algorithmic SEO 2026",
        "category": "Digital Skills",
        "demand": "Very High",
        "top_country": "India & Southeast Asia",
        "score": 9.6
    }
]

HTML_CONTENT = """<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Empire OS - Global Book Intelligence</title>
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: #111827;
            --border-color: #1f2937;
            --accent-green: #22c55e;
            --accent-glow: rgba(34, 197, 94, 0.2);
            --text-main: #f8fafc;
            --text-muted: #9ca3af;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
        }
        .container {
            width: 100%;
            max-width: 900px;
            background-color: var(--card-bg);
            border: 2px solid var(--accent-green);
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.8);
        }
        .header {
            text-align: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 25px;
        }
        .badge {
            background-color: var(--accent-green);
            color: #000;
            font-weight: 800;
            font-size: 12px;
            padding: 5px 12px;
            border-radius: 20px;
            letter-spacing: 1px;
        }
        h1 {
            font-size: 24px;
            margin: 15px 0 5px 0;
            color: #4ade80;
        }
        p.subtitle {
            color: var(--text-muted);
            font-size: 14px;
            margin: 0;
        }
        .grid-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .action-btn {
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            border: 1px solid #374151;
            color: #fff;
            padding: 18px 20px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: left;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            width: 100%;
        }
        .action-btn:hover {
            border-color: var(--accent-green);
            background: #1f2937;
            box-shadow: 0 0 15px var(--accent-glow);
            transform: translateY(-2px);
        }
        .console-box {
            background-color: #030712;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            font-family: monospace;
            font-size: 13px;
            color: #38bdf8;
            min-height: 160px;
            max-height: 240px;
            overflow-y: auto;
        }
        .console-title {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">🌍 GLOBAL TREND & BOOK INTELLIGENCE ACTIVE</span>
            <h1>MASTER EMPIRE OS</h1>
            <p class="subtitle">Autonomous Global Book Research & Publishing Engine</p>
        </div>

        <div class="grid-buttons">
            <button class="action-btn" onclick="runGlobalResearch()">
                <span>💡 Make an Idea (Global Trend)</span>
                <span>✨</span>
            </button>
            <button class="action-btn" onclick="alert('Publish module queuing next...')">
                <span>🚀 Publish Content</span>
                <span>📤</span>
            </button>
            <button class="action-btn" onclick="alert('Filter module ready.')">
                <span>❌ Reject / Filter</span>
                <span>🗑️</span>
            </button>
            <button class="action-btn" onclick="alert('Analytics loading.')">
                <span>📊 Overall Analytics</span>
                <span>📈</span>
            </button>
            <button class="action-btn" onclick="alert('Catalog loading.')">
                <span>📚 All Books & Analytics</span>
                <span>📖</span>
            </button>
        </div>

        <div class="console-title">Live Global Research Console</div>
        <div class="console-box" id="consoleLog">
            > System online on Render Cloud.<br>
            > Global Market Intelligence Engine: Active.<br>
            > Click 'Make an Idea' to fetch current world-wide best-selling book opportunities & target countries...
        </div>
    </div>

    <script>
        function runGlobalResearch() {
            const consoleBox = document.getElementById('consoleLog');
            const timestamp = new Date().toLocaleTimeString();
            
            fetch('/api/global-book-idea')
            .then(response => response.json())
            .then(data => {
                consoleBox.innerHTML += `<br><br>> [${timestamp}] 🌐 <b>GLOBAL BOOK RESEARCH REPORT:</b><br>` +
                                         `&nbsp;&nbsp;📖 <b>Title:</b> ${data.book}<br>` +
                                         `&nbsp;&nbsp;🏷️ <b>Category:</b> ${data.category}<br>` +
                                         `&nbsp;&nbsp;🔥 <b>Market Demand:</b> ${data.demand} (Score: ${data.score}/10)<br>` +
                                         `&nbsp;&nbsp;🌍 <b>Top Target Country:</b> ${data.top_country}`;
                consoleBox.scrollTop = consoleBox.scrollHeight;
            })
            .catch(err => {
                consoleBox.innerHTML += `<br>> [${timestamp}] ❌ Error fetching global trend.`;
            });
        }
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/global-book-idea':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            selected_trend = random.choice(GLOBAL_BOOK_TRENDS)
            self.wfile.write(json.dumps(selected_trend).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Master Empire OS serving at port {PORT}")
        httpd.serve_forever()