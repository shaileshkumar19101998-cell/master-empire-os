import os
import http.server
import socketserver

PORT = int(os.environ.get("PORT", 8080))

HTML_CONTENT = """<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="utf-8">
    <title>Master Empire OS - Live Production</title>
    <style>
        body { background: #0b0f19; color: #f8fafc; font-family: sans-serif; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .container { width: 100%; max-width: 800px; background: #111827; border: 2px solid #22c55e; border-radius: 16px; padding: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.8); }
        .header { text-align: center; border-bottom: 1px solid #1f2937; padding-bottom: 15px; margin-bottom: 20px; }
        .badge { background: #22c55e; color: #000; font-weight: bold; font-size: 11px; padding: 4px 10px; border-radius: 20px; }
        h1 { font-size: 22px; margin: 10px 0 5px 0; color: #4ade80; }
        .status-box { background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">🟢 ONLINE & SECURE</span>
            <h1>MASTER EMPIRE OS LIVE</h1>
        </div>
        <div class="status-box">
            <p style="font-size: 16px; color: #fff; margin: 0;">System is fully operational, error-free, and running live on Render cloud!</p>
        </div>
    </div>
</body>
</html>
"""

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode('utf-8'))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
        print(f"Server serving at port {PORT}")
        httpd.serve_forever()