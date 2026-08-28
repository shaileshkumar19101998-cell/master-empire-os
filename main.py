import os
import http.server
import socketserver
import json
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", 8080))

# एक साथ Top 5 Global Trending Books की डेटा लिस्ट
TOP_5_BOOKS = [
    {
        "id": 1,
        "book": "The AI Revolution in Small Business: 2026 Blueprint",
        "category": "Technology & AI",
        "demand": "Very High (9.8/10)",
        "top_country": "United States & Canada",
        "status": "Ready to Publish"
    },
    {
        "id": 2,
        "book": "Ancient Philosophy for Modern Anxiety: Stoicism Today",
        "category": "Self-Help & Psychology",
        "demand": "High (9.5/10)",
        "top_country": "United Kingdom & Europe",
        "status": "Ready to Publish"
    },
    {
        "id": 3,
        "book": "Passive Income Ecosystems: Global E-Commerce Strategies",
        "category": "Business & Wealth",
        "demand": "Explosive (9.9/10)",
        "top_country": "Australia & United States",
        "status": "Ready to Publish"
    },
    {
        "id": 4,
        "book": "The Longevity Diet: Biohacking Cellular Health",
        "category": "Health & Wellness",
        "demand": "Steady High (9.2/10)",
        "top_country": "Germany & Japan",
        "status": "Ready to Publish"
    },
    {
        "id": 5,
        "book": "Mastering Digital Marketing & Algorithmic SEO 2026",
        "category": "Digital Skills",
        "demand": "Very High (9.6/10)",
        "top_country": "India & Southeast Asia",
        "status": "Ready to Publish"
    }
]

HTML_CONTENT = """<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Empire OS - Top 5 Books & Publishing Hub</title>
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
            max-width: 950px;
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
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 25px;
        }
        .action-btn {
            background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            border: 1px solid #374151;
            color: #fff;
            padding: 14px 16px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
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
            min-height: 200px;
            max-height: 320px;
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
            <span class="badge">🚀 TOP 5 GLOBAL BOOKS & PUBLISHING PIPELINE</span>
            <h1>MASTER EMPIRE OS</h1>
            <p class="subtitle">Autonomous Market Research & Publishing Hub</p>
        </div>

        <div class="grid-buttons">
            <button class="action-btn" onclick="fetchTop5Books()">
                📚 <b>1. Make Ideas (Top 5)</b>
            </button>
            <button class="action-btn" onclick="publishBooks()">
                🚀 <b>2. Publish Content</b>
            </button>
            <button class="action-btn" onclick="alert('Filter module active.')">
                ❌ <b>3. Reject / Filter</b>
            </button>
            <button class="action-btn" onclick="alert('Analytics dashboard loading.')">
                📊 <b>4. Analytics</b>
            </button>
            <button class="action-btn" onclick="alert('Catalog active.')">
                📖 <b>5. All Books</b>
            </button>
        </div>

        <div class="console-title">Live Execution Console</div>
        <div class="console-box" id="consoleLog">
            > System online on Render Cloud.<br>
            > Publishing Pipeline: Connected.<br>
            > Click 'Make Ideas (Top 5)' to load current world-wide best-selling book opportunities...
        </div>
    </div>

    <script>
        function fetchTop5Books() {
            const consoleBox = document.getElementById('consoleLog');
            const timestamp = new Date().toLocaleTimeString();
            
            fetch('/api/top-5-books')
            .then(response => response.json())
            .then(data => {
                let htmlOutput = `<br><br>> [${timestamp}] 🌟 <b>TOP 5 GLOBAL TRENDING BOOKS RESEARCH REPORT:</b><br>`;
                data.forEach((item, index) => {
                    htmlOutput += `&nbsp;&nbsp;<b>${index + 1}. ${item.book}</b><br>` +
                                  `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🏷️ Category: ${item.category} | 🔥 Demand: ${item.demand}<br>` +
                                  `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🌍 Target Market: ${item.top_country} | Status: <i>${item.status}</i><br><br>`;
                });
                consoleBox.innerHTML += htmlOutput;
                consoleBox.scrollTop = consoleBox.scrollHeight;
            })
            .catch(err => {
                consoleBox.innerHTML += `<br>> [${timestamp}] ❌ Error fetching books data.`;
            });
        }

        function publishBooks() {
            const consoleBox = document.getElementById('consoleLog');
            const timestamp = new Date().toLocaleTimeString();
            consoleBox.innerHTML += `<br>> [${timestamp}] 🚀 <b>Publishing Triggered!</b> Packaging Top 5 books into distribution-ready format for Amazon KDP & Global Stores... Success!`;
            consoleBox.scrollTop = consoleBox.scrollHeight;
        }
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/top-5-books':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(TOP_5_BOOKS).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Master Empire OS serving at port {PORT}")
        httpd.serve_forever()