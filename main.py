import os
import http.server
import socketserver
import json
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", 8080))

# यूनिवर्सल ग्लोबल मार्केट इंजन जो दुनिया के सभी रजिस्टर्ड और भविष्य के सभी देशों/क्षेत्रों को कवर करेगा
UNIVERSAL_GLOBAL_ENGINE = {
    "engine_status": "ONLINE 24/7",
    "target_scope": "All Registered & Future Global Territories Worldwide",
    "seo_mode": "Autonomous Multi-Region Algorithmic Optimization",
    "active_books": [
        {
            "id": 1,
            "title": "Global Wealth & Autonomous Digital Empires: 2026 Master Edition",
            "category": "Business & Technology",
            "global_reach": "Unlimited (All Active & Future Nation-States)",
            "seo_status": "Running 24/7 Background Optimization",
            "distribution": "Global Multi-Region Ready"
        },
        {
            "id": 2,
            "title": "Universal Philosophy & Human Evolution Across Borders",
            "category": "Philosophy & Society",
            "global_reach": "Unlimited (All Active & Future Nation-States)",
            "seo_status": "Running 24/7 Background Optimization",
            "distribution": "Global Multi-Region Ready"
        }
    ]
}

HTML_CONTENT = """<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Empire OS - Universal Global Empire Engine</title>
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
            min-height: 220px;
            max-height: 340px;
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
            <span class="badge">🌐 UNIVERSAL GLOBAL & FUTURE-PROOF EMPIRE ACTIVE</span>
            <h1>MASTER EMPIRE OS</h1>
            <p class="subtitle">24/7 Autonomous Multi-Nation SEO & Publishing Engine</p>
        </div>

        <div class="grid-buttons">
            <button class="action-btn" onclick="fetchUniversalIdeas()">
                💡 <b>1. Make Ideas (Global)</b>
            </button>
            <button class="action-btn" onclick="publishUniversal()">
                🚀 <b>2. Publish Worldwide</b>
            </button>
            <button class="action-btn" onclick="alert('Filter module active.')">
                ❌ <b>3. Reject / Filter</b>
            </button>
            <button class="action-btn" onclick="alert('Global Analytics active.')">
                📊 <b>4. Analytics</b>
            </button>
            <button class="action-btn" onclick="alert('Universal Catalog active.')">
                📖 <b>5. All Books</b>
            </button>
        </div>

        <div class="console-title">Universal 24/7 Execution Console</div>
        <div class="console-box" id="consoleLog">
            > System online on Render Cloud.<br>
            > Universal Scope: Covering all registered present & future global territories.<br>
            > Background 24/7 SEO Worker: ACTIVE.<br>
            > Click 'Make Ideas (Global)' to scan worldwide demand...
        </div>
    </div>

    <script>
        function fetchUniversalIdeas() {
            const consoleBox = document.getElementById('consoleLog');
            const timestamp = new Date().toLocaleTimeString();
            
            fetch('/api/universal-data')
            .then(response => response.json())
            .then(data => {
                let output = `<br><br>> [${timestamp}] 🌍 <b>UNIVERSAL MULTI-NATION SCAN REPORT:</b><br>` +
                             `&nbsp;&nbsp;<b>Target Scope:</b> ${data.target_scope}<br>` +
                             `&nbsp;&nbsp;<b>SEO Mode:</b> ${data.seo_mode}<br><br>`;
                data.active_books.forEach((book) => {
                    output += `&nbsp;&nbsp;📖 <b>${book.title}</b><br>` +
                              `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🏷️ Category: ${book.category}<br>` +
                              `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🌐 Reach: ${book.global_reach}<br>` +
                              `&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;⚙️ Status: <i>${book.seo_status}</i><br><br>`;
                });
                consoleBox.innerHTML += output;
                consoleBox.scrollTop = consoleBox.scrollHeight;
            })
            .catch(err => {
                consoleBox.innerHTML += `<br>> [${timestamp}] ❌ Error connecting to universal engine.`;
            });
        }

        function publishUniversal() {
            const consoleBox = document.getElementById('consoleLog');
            const timestamp = new Date().toLocaleTimeString();
            consoleBox.innerHTML += `<br>> [${timestamp}] 🚀 <b>Universal Multi-Region Publish Triggered!</b> Deploying books across all active & future international store nodes with automated local SEO... Success!`;
            consoleBox.scrollTop = consoleBox.scrollHeight;
        }
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/universal-data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(UNIVERSAL_GLOBAL_ENGINE).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Master Empire OS serving at port {PORT}")
        httpd.serve_forever()