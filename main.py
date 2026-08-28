import os
import http.server
import socketserver
import json
import random
from urllib.parse import parse_qs, urlparse

PORT = int(os.environ.get("PORT", 8080))

# शुरुआती आइडिया बैंक (जहाँ से ऑटोनॉमस सिस्टम नए आइडिया चुनेगा)
IDEAS_BANK = [
    "Oxidized Silver Choker Set - Ethnic Boho Theme",
    "Matte Liquid Lipstick Collection - Long Wear Formula",
    "Anti-Aging Botanical Face Serum with Vitamin C",
    "Minimalist Silver Finger Rings - Daily Wear Stackable",
    "Herbal Hair Growth Oil with Rosemary & Amla"
]

HTML_CONTENT = """<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Empire OS - Autonomous Dashboard</title>
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
            min-height: 140px;
            max-height: 220px;
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
            <span class="badge">🟢 STEP 1: MAKE AN IDEA ACTIVE</span>
            <h1>MASTER EMPIRE OS</h1>
            <p class="subtitle">Autonomous Command Center - Shringaar & Digital Assets</p>
        </div>

        <div class="grid-buttons">
            <button class="action-btn" onclick="runAction('make_idea')">
                <span>💡 Make an Idea</span>
                <span>✨</span>
            </button>
            <button class="action-btn" onclick="alert('Step 2: Publish module will be linked next!')">
                <span>🚀 Publish Content</span>
                <span>📤</span>
            </button>
            <button class="action-btn" onclick="alert('Step 3: Reject filter ready.')">
                <span>❌ Reject / Filter</span>
                <span>🗑️</span>
            </button>
            <button class="action-btn" onclick="alert('Step 4: Overall analytics loading.')">
                <span>📊 Overall Analytics</span>
                <span>📈</span>
            </button>
            <button class="action-btn" onclick="alert('Step 5: Books catalog loading.')">
                <span>📚 All Books & Analytics</span>
                <span>📖</span>
            </button>
        </div>

        <div class="console-title">Live Execution Console & Status</div>
        <div class="console-box" id="consoleLog">
            > System initialized successfully on Render Cloud.<br>
            > Step 1 Active: Click 'Make an Idea' to generate autonomous product/content concepts.<br>
            > Waiting for command...
        </div>
    </div>

    <script>
        function runAction(actionType) {
            const consoleBox = document.getElementById('consoleLog');
            const timestamp = new Date().toLocaleTimeString();
            
            if(actionType === 'make_idea') {
                fetch('/api/make-idea')
                .then(response => response.json())
                .then(data => {
                    consoleBox.innerHTML += `<br>> [${timestamp}] 💡 New Autonomous Idea Generated: <b>${data.idea}</b> (Score: ${data.score}/10)`;
                    consoleBox.scrollTop = consoleBox.scrollHeight;
                })
                .catch(err => {
                    consoleBox.innerHTML += `<br>> [${timestamp}] ❌ Error generating idea.`;
                });
            }
        }
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/api/make-idea':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            selected_idea = random.choice(IDEAS_BANK)
            response_data = {
                "idea": selected_idea,
                "score": round(random.uniform(8.5, 9.9), 1)
            }
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Master Empire OS serving at port {PORT}")
        httpd.serve_forever()