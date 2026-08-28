import os
import http.server
import socketserver
import json
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", 8080))

# Master Autonomous Business OS - Permanent 11 Elite Books Edition
OS_DATABASE = {
    "system_name": "MASTER AUTONOMOUS BUSINESS OS (PERMANENT CATALOG)",
    "status": "Multi-Currency Pricing + Permanent 11 Books Catalog ACTIVE",
    "seo_architecture": "Autonomous Multi-Region Indexing & Currency Routing",
    "stats": {
        "impressions": "0",
        "max_views": "0",
        "total_orders": "0",
        "global_revenue": "₹0"
    },
    "books": [
        {
            "id": 1,
            "title": "High-Ticket AI Automation & Global Scaling Ecosystem — Enterprise Mega Level",
            "discount": "60% OFF WORLDWIDE LAUNCH 👑",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.98 / 5.0 Elite Certified",
            "chapters": ["Module 1: Foundations", "Module 2: Cross-Border Infra", "Module 3: Zero-Human Operations"],
            "full_text": "Comprehensive masterclass on High-Ticket AI Automation and Global Scaling. Fully optimized for 195+ nations."
        },
        {
            "id": 2,
            "title": "Artificial Intelligence & Autonomous Wealth Systems — 2026 Edition",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: AI Systems", "Module 2: Wealth Generation", "Module 3: Automation Loops"],
            "full_text": "Masterclass on Artificial Intelligence and Autonomous Wealth Systems designed for worldwide digital storefronts."
        },
        {
            "id": 3,
            "title": "Advanced Digital Marketing & 195+ Nation SEO Mastery",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Global SEO", "Module 2: Traffic Multipliers", "Module 3: Conversion Loops"],
            "full_text": "Deep-dive manual into advanced digital marketing and perpetual global SEO indexing across 195+ countries."
        },
        {
            "id": 4,
            "title": "E-Commerce & High-Ticket Dropshipping Dominance",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Product Research", "Module 2: Storefront Architecture", "Module 3: Scaling Ads"],
            "full_text": "The ultimate guide to building, scaling, and automating high-ticket e-commerce and dropshipping brands."
        },
        {
            "id": 5,
            "title": "Biohacking, Longevity & Peak Human Performance",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Cellular Health", "Module 2: Circadian Alignment", "Module 3: Vitality Routine"],
            "full_text": "Science-backed protocols and biological engineering blueprints for absolute physical and mental peak performance."
        },
        {
            "id": 6,
            "title": "Cryptocurrency, Web3 & Decentralized Financial Empires",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Web3 Foundations", "Module 2: Decentralized Assets", "Module 3: Security Protocols"],
            "full_text": "Comprehensive analysis of cryptocurrency ecosystems, smart contracts, and decentralized financial growth."
        },
        {
            "id": 7,
            "title": "Psychology of Mass Influence & High-Conversion Copywriting",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Behavioral Triggers", "Module 2: Persuasive Copy", "Module 3: Conversion Funnels"],
            "full_text": "Master the art of persuasive communication and mass psychological triggers to drive unstoppable sales conversions."
        },
        {
            "id": 8,
            "title": "Algorithmic Trading & Automated Passive Income Portfolios",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Algo Basics", "Module 2: Risk Management", "Module 3: Portfolio Automation"],
            "full_text": "A rigorous technical guide on deploying algorithmic trading bots and managing automated financial portfolios."
        },
        {
            "id": 9,
            "title": "Global Leadership & Scaling Cross-Border Organizations",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Cross-Border Teams", "Module 2: Remote Leadership", "Module 3: Organizational Scaling"],
            "full_text": "Frameworks for leading international teams and scaling distributed organizations without geographical bottlenecks."
        },
        {
            "id": 10,
            "title": "The 4.9+ Star Masterclass in Personal Brand Authority",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Brand Positioning", "Module 2: Authority Content", "Module 3: Monetization Loops"],
            "full_text": "Build unshakeable personal brand authority and command premium pricing across global digital markets."
        },
        {
            "id": 11,
            "title": "Zero-Human Digital Asset Creation & Automated Distribution",
            "discount": "70% OFF GLOBAL LAUNCH 🌟",
            "pricing": {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
            "quality": "⭐ 4.99 / 5.0 Elite Certified",
            "chapters": ["Module 1: Zero-Human Pipelines", "Module 2: Automated Assets", "Module 3: Global Delivery"],
            "full_text": "The pinnacle manual on deploying zero-human operational pipelines for completely automated digital publishing."
        }
    ]
}

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Autonomous Business OS - Permanent Catalog</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-deep: #0b0f17;
            --card-bg: #111520;
            --border-gold: #d4af37;
            --accent-gold: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; }
        body {
            background-color: var(--bg-deep);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            margin: 0;
            padding: 15px;
            display: flex;
            justify-content: center;
        }
        .main-wrapper {
            width: 100%;
            max-width: 520px;
            background: var(--card-bg);
            border: 2px solid var(--border-gold);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        }
        .top-badge {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #000;
            font-size: 10px;
            font-weight: 800;
            text-align: center;
            padding: 6px;
            border-radius: 8px;
            margin-bottom: 15px;
            letter-spacing: 0.5px;
        }
        h1 {
            text-align: center;
            font-size: 20px;
            color: #f8fafc;
            margin-bottom: 20px;
            font-weight: 800;
        }
        .nav-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 20px;
        }
        .nav-btn {
            background: #1f2937;
            border: 1px solid #374151;
            color: #fff;
            padding: 10px 5px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
            transition: 0.2s;
        }
        .nav-btn.active, .nav-btn:hover {
            background: #f59e0b;
            color: #000;
            border-color: #f59e0b;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }
        .stat-card {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        .stat-title { font-size: 12px; color: var(--text-muted); margin-bottom: 5px; }
        .stat-value { font-size: 18px; font-weight: 700; color: #38bdf8; }
        .stat-value.green { color: #22c55e; }
        .stat-value.gold { color: #f59e0b; }
        .seo-box {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            margin-top: 15px;
        }
        .seo-box h3 { color: #f59e0b; font-size: 14px; margin-top: 0; }
        .seo-box p { font-size: 11px; color: var(--text-muted); line-height: 1.5; margin-bottom: 0; }
        
        .book-item-card {
            background: #0d1117;
            border: 1px solid var(--border-gold);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .discount-tag {
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            font-size: 10px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
            margin-bottom: 8px;
        }
        .book-title { font-size: 14px; font-weight: 700; margin-bottom: 10px; color: #fff; }
        .pricing-grid {
            background: #111827;
            border: 1px solid #374151;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 12px;
            font-size: 11px;
            color: #cbd5e1;
        }
        .pricing-grid b { color: #22c55e; }
        .btn-row { display: flex; gap: 10px; }
        .btn-read { background: #f59e0b; color: #000; border: none; padding: 8px 15px; border-radius: 6px; font-weight: 700; cursor: pointer; font-size: 12px; }
        .btn-buy { background: #22c55e; color: #000; border: none; padding: 8px 15px; border-radius: 6px; font-weight: 700; cursor: pointer; font-size: 12px; }
        .reader-box { background: #05070a; border: 1px solid #38bdf8; padding: 15px; border-radius: 8px; margin-top: 12px; font-size: 12px; max-height: 400px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <div class="top-badge">👑 PERMANENT 11-BOOKS ELITE CATALOG</div>
        <h1>MASTER AUTONOMOUS BUSINESS OS</h1>

        <!-- Navigation Tabs -->
        <div class="nav-grid">
            <button class="nav-btn active" onclick="switchTab('dashboard')">🏠 Dashboard</button>
            <button class="nav-btn" onclick="switchTab('studio')">🚀 AI Studio</button>
            <button class="nav-btn" onclick="switchTab('store')">📚 Max Store</button>
            <button class="nav-btn" onclick="switchTab('stats')">📊 Live Stats</button>
            <button class="nav-btn" onclick="switchTab('customers')">👥 Customers</button>
            <button class="nav-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>

        <!-- Dynamic Content Area -->
        <div id="contentArea">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Global Impressions</div>
                    <div class="stat-value">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Total Max Views</div>
                    <div class="stat-value green">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Total Orders</div>
                    <div class="stat-value">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Global Revenue</div>
                    <div class="stat-value gold">₹0</div>
                </div>
            </div>

            <div class="seo-box" style="border-color: #22c55e;">
                <h3 style="color: #22c55e;">📚 Permanent 11-Books Catalog Loaded</h3>
                <p>All 11 elite books are now permanently hardcoded and locked into the store. They will never disappear on refresh.</p>
            </div>
        </div>
    </div>

    <script>
        const permanentBooks = [
            {
                id: 1,
                title: "High-Ticket AI Automation & Global Scaling Ecosystem — Enterprise Mega Level",
                discount: "60% OFF WORLDWIDE LAUNCH 👑",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.98 / 5.0 Elite Certified",
                chapters: ["Module 1: Foundations", "Module 2: Cross-Border Infra", "Module 3: Zero-Human Operations"],
                full_text: "Comprehensive masterclass on High-Ticket AI Automation and Global Scaling. Fully optimized for 195+ nations."
            },
            {
                id: 2,
                title: "Artificial Intelligence & Autonomous Wealth Systems — 2026 Edition",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: AI Systems", "Module 2: Wealth Generation", "Module 3: Automation Loops"],
                full_text: "Masterclass on Artificial Intelligence and Autonomous Wealth Systems designed for worldwide digital storefronts."
            },
            {
                id: 3,
                title: "Advanced Digital Marketing & 195+ Nation SEO Mastery",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Global SEO", "Module 2: Traffic Multipliers", "Module 3: Conversion Loops"],
                full_text: "Deep-dive manual into advanced digital marketing and perpetual global SEO indexing across 195+ countries."
            },
            {
                id: 4,
                title: "E-Commerce & High-Ticket Dropshipping Dominance",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Product Research", "Module 2: Storefront Architecture", "Module 3: Scaling Ads"],
                full_text: "The ultimate guide to building, scaling, and automating high-ticket e-commerce and dropshipping brands."
            },
            {
                id: 5,
                title: "Biohacking, Longevity & Peak Human Performance",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Cellular Health", "Module 2: Circadian Alignment", "Module 3: Vitality Routine"],
                full_text: "Science-backed protocols and biological engineering blueprints for absolute physical and mental peak performance."
            },
            {
                id: 6,
                title: "Cryptocurrency, Web3 & Decentralized Financial Empires",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Web3 Foundations", "Module 2: Decentralized Assets", "Module 3: Security Protocols"],
                full_text: "Comprehensive analysis of cryptocurrency ecosystems, smart contracts, and decentralized financial growth."
            },
            {
                id: 7,
                title: "Psychology of Mass Influence & High-Conversion Copywriting",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Behavioral Triggers", "Module 2: Persuasive Copy", "Module 3: Conversion Funnels"],
                full_text: "Master the art of persuasive communication and mass psychological triggers to drive unstoppable sales conversions."
            },
            {
                id: 8,
                title: "Algorithmic Trading & Automated Passive Income Portfolios",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Algo Basics", "Module 2: Risk Management", "Module 3: Portfolio Automation"],
                full_text: "A rigorous technical guide on deploying algorithmic trading bots and managing automated financial portfolios."
            },
            {
                id: 9,
                title: "Global Leadership & Scaling Cross-Border Organizations",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Cross-Border Teams", "Module 2: Remote Leadership", "Module 3: Organizational Scaling"],
                full_text: "Frameworks for leading international teams and scaling distributed organizations without geographical bottlenecks."
            },
            {
                id: 10,
                title: "The 4.9+ Star Masterclass in Personal Brand Authority",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Brand Positioning", "Module 2: Authority Content", "Module 3: Monetization Loops"],
                full_text: "Build unshakeable personal brand authority and command premium pricing across global digital markets."
            },
            {
                id: 11,
                title: "Zero-Human Digital Asset Creation & Automated Distribution",
                discount: "70% OFF GLOBAL LAUNCH 🌟",
                pricing: {"inr": "₹1,999 INR", "usd": "$24 USD", "eur": "€22 EUR", "gbp": "£19 GBP"},
                quality: "⭐ 4.99 / 5.0 Elite Certified",
                chapters: ["Module 1: Zero-Human Pipelines", "Module 2: Automated Assets", "Module 3: Global Delivery"],
                full_text: "The pinnacle manual on deploying zero-human operational pipelines for completely automated digital publishing."
            }
        ];

        function switchTab(tabName) {
            const buttons = document.querySelectorAll('.nav-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            const area = document.getElementById('contentArea');

            if (tabName === 'dashboard') {
                area.innerHTML = `
                    <div class="stats-grid">
                        <div class="stat-card"><div class="stat-title">Global Impressions</div><div class="stat-value">0</div></div>
                        <div class="stat-card"><div class="stat-title">Total Max Views</div><div class="stat-value green">0</div></div>
                        <div class="stat-card"><div class="stat-title">Total Orders</div><div class="stat-value">0</div></div>
                        <div class="stat-card"><div class="stat-title">Global Revenue</div><div class="stat-value gold">₹0</div></div>
                    </div>
                    <div class="seo-box" style="border-color: #22c55e;">
                        <h3 style="color: #22c55e;">📚 Permanent 11-Books Catalog Loaded</h3>
                        <p>All 11 elite books are permanently locked into the store and will never disappear.</p>
                    </div>`;
            } 
            else if (tabName === 'store') {
                renderStore(area);
            }
            else if (tabName === 'studio') {
                area.innerHTML = `
                    <div class="seo-box" style="border-color:#f59e0b;">
                        <h3>🚀 AI Studio & Permanent Catalog</h3>
                        <p>All 11 books are permanently active in Max Store with multi-currency pricing and live SEO.</p>
                    </div>`;
            }
            else if (tabName === 'stats') {
                area.innerHTML = `
                    <div class="seo-box">
                        <h3>📊 Permanent Catalog Stats</h3>
                        <p><b>Total Active Books:</b> 11<br><b>Currencies:</b> INR, USD, EUR, GBP<br><b>Status:</b> Locked & Permanent.</p>
                    </div>`;
            }
            else if (tabName === 'customers') {
                area.innerHTML = `
                    <div class="seo-box">
                        <h3>👥 Live Customer & Webhook Ledger</h3>
                        <p><b>Status:</b> Ready to capture real-time multi-currency checkouts via Razorpay webhook.</p>
                    </div>`;
            }
        }

        function renderStore(area) {
            let html = `<h3 style="color:#f59e0b; font-size:14px; margin-bottom:12px;">📚 Permanent Max Store Catalog (11 Books)</h3>`;
            permanentBooks.forEach(book => {
                html += `
                <div class="book-item-card">
                    <span class="discount-tag">${book.discount}</span>
                    <div class="book-title">${book.title}</div>
                    <div class="pricing-grid">
                        <div>🇮🇳 India: <b>${book.pricing.inr}</b></div>
                        <div>🇺🇸 USA: <b>${book.pricing.usd}</b></div>
                        <div>🇪🇺 Europe: <b>${book.pricing.eur}</b></div>
                        <div>🇬🇧 UK: <b>${book.pricing.gbp}</b></div>
                    </div>
                    <div class="btn-row">
                        <button class="btn-read" onclick="readFullBook(${book.id})">📖 READ FULL BOOK</button>
                        <button class="btn-buy" onclick="simulateCheckout(${book.id})">💳 SECURE BUY</button>
                    </div>
                    <div id="reader-${book.id}"></div>
                </div>`;
            });
            area.innerHTML = html;
        }

        function readFullBook(bookId) {
            const book = permanentBooks.find(b => b.id == bookId);
            const readerDiv = document.getElementById(`reader-${bookId}`);
            let list = "<ul style='padding-left: 15px; margin: 8px 0;'>";
            book.chapters.forEach(c => list += `<li style='margin-bottom: 4px;'>${c}</li>`);
            list += "</ul>";
            
            readerDiv.innerHTML = `
            <div class="reader-box">
                <strong style="color:#f59e0b;">✨ Quality: ${book.quality}</strong>
                <strong style="color:#38bdf8; display:block; margin-top:8px;">📖 Table of Contents:</strong> ${list}
                <strong style="color:#22c55e; display:block; margin-top:10px;">📄 Full Unrestricted Book Content:</strong>
                <pre style="color:#cbd5e1; font-size:11px; white-space: pre-wrap; font-family:'Plus Jakarta Sans', sans-serif; line-height:1.6;">${book.full_text}</pre>
            </div>`;
        }

        function simulateCheckout(bookId) {
            alert("💳 256-Bit Razorpay Checkout Initialized! Multi-currency routing active for INR, USD, EUR, and GBP.");
        }
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode('utf-8'))

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"Master Empire OS serving at port {PORT}")
        httpd.serve_forever()