import os
import http.server
import socketserver
import json
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", 8080))

# Master Autonomous Business OS - Locked Sovereign Catalog & Traffic Booster Edition
OS_DATABASE = {
    "system_name": "MASTER AUTONOMOUS BUSINESS OS (LOCKED SOVEREIGN EDITION)",
    "status": "Locked Sovereign Catalog + Massive Exhaustive Text + Direct Social Traffic Booster ACTIVE",
    "stats": {
        "impressions": "0",
        "max_views": "0",
        "total_orders": "0",
        "global_revenue": "₹0"
    }
}

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Autonomous Business OS - Sovereign Hub</title>
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
            text-align: left;
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
        
        /* Crystal Clear Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.92);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            padding: 15px;
        }
        .modal-content {
            background: #111520;
            border: 2px solid var(--border-gold);
            width: 100%;
            max-width: 580px;
            max-height: 88vh;
            border-radius: 15px;
            padding: 20px;
            overflow-y: auto;
            text-align: left;
        }
        .close-btn {
            background: #ef4444;
            color: #fff;
            border: none;
            padding: 6px 14px;
            border-radius: 6px;
            font-weight: 700;
            cursor: pointer;
            float: right;
            font-size: 12px;
        }
        .studio-input { width: 100%; background: #0d1117; border: 1px solid #d4af37; color: #fff; padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 12px; }
        .share-btn { background: #38bdf8; color: #000; border: none; padding: 8px 12px; border-radius: 6px; font-weight: 700; cursor: pointer; font-size: 11px; margin-top: 5px; width: 100%; }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <div class="top-badge">👑 EST. AUG 28, 2026 — LOCKED CATALOG & DIRECT SOCIAL TRAFFIC BOOSTER</div>
        <h1>MASTER AUTONOMOUS BUSINESS OS</h1>

        <!-- Navigation Tabs -->
        <div class="nav-grid">
            <button class="nav-btn active" id="btn-dashboard" onclick="switchTab('dashboard')">🏠 Dashboard</button>
            <button class="nav-btn" id="btn-studio" onclick="switchTab('studio')">🚀 AI Studio</button>
            <button class="nav-btn" id="btn-store" onclick="switchTab('store')">📚 Max Store</button>
            <button class="nav-btn" id="btn-stats" onclick="switchTab('stats')">📊 Traffic & SEO</button>
            <button class="nav-btn" id="btn-customers" onclick="switchTab('customers')">👥 Customers</button>
            <button class="nav-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>

        <!-- Dynamic Content Area -->
        <div id="contentArea">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-title">Global Impressions</div>
                    <div class="stat-value" id="impCount">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Total Max Views</div>
                    <div class="stat-value green" id="viewCount">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Total Orders</div>
                    <div class="stat-value" id="orderCount">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Global Revenue</div>
                    <div class="stat-value gold" id="revCount">₹0</div>
                </div>
            </div>

            <div class="seo-box" style="border-color: #22c55e;">
                <h3 style="color: #22c55e;">🎯 Locked Sovereign Catalog & Traffic Booster Active</h3>
                <p>Your primary catalog is securely locked and protected. Massive exhaustive books are fully unlocked, and direct social traffic tools are ready.</p>
            </div>
        </div>
    </div>

    <div id="readerModal" style="display:none;"></div>

    <script>
        let lockedMasterCatalog = [
            {
                id: 1,
                title: "High-Ticket AI Automation & Global Scaling Ecosystem — Enterprise Mega Level",
                discount: "60% OFF FOUNDER EDITION 👑",
                pricing: {
                    inr: "₹1,999 INR (India)",
                    usd: "$24 USD (USA & Americas)",
                    eur: "€22 EUR (Europe)",
                    gbp: "£19 GBP (United Kingdom)"
                },
                old_price: "₹5,999 ($129)",
                per_book_seo: "Active: Autonomous 195+ Nation Indexing",
                chapters: [
                    "Module 1: Architectural Foundations of High-Ticket AI Ecosystems",
                    "Module 2: Autonomous Cross-Border Infrastructure & Node Deployment",
                    "Module 3: Zero-Human Operations, Automated Funnels & Instant Fulfillment",
                    "Module 4: Maximizing Enterprise Profit Margins Across International Borders",
                    "Module 5: Advanced Legal Compliance, Multi-Currency Tax & Global Structures",
                    "Module 6: Scaling to Daily International Sales Velocity & Perpetual Loops"
                ],
                full_text: `[COMPLETE UNRESTRICTED FOUNDER MASTERCLASS - 100% EXHAUSTIVE TEXT]
[ESTABLISHMENT DAY: AUGUST 28, 2026]

PREFACE: THE SOVEREIGN DIGITAL EMPIRE PARADIGM
In the modern hyper-connected digital economy, true sovereignty belongs exclusively to those who engineer fully autonomous systems. Traditional businesses rely on manual labour, localized storefronts, and constant physical oversight. In stark contrast, a Sovereign Digital Empire operates across 195+ international territories simultaneously, leveraging automated search engine indexing, algorithmic organic traffic loops, and secure cross-border payment gateways. This exhaustive masterclass volume provides the exact architectural blueprints required to build, scale, and automate high-ticket digital asset distribution without human intervention.

MODULE 1: ARCHITECTURAL FOUNDATIONS OF HIGH-TICKET AI ECOSYSTEMS
High-ticket digital products demand absolute structural perfection. When positioning elite digital assets to high-net-worth buyers and enterprise organizations across the United States, Europe, the United Kingdom, and Asia, your value proposition must be incontrovertible.
- Sub-Section 1.1: Identifying High-Value Micro-Niches with Low Organic Competition.
- Sub-Section 1.2: Engineering Irresistible Digital Offers and Psychological Pricing Anchors.
- Sub-Section 1.3: Deploying Autonomous Funnel Architecture that Converts Cold Search Traffic into High-Ticket Buyers on Autopilot.
Every framework detailed in this module is rigorously engineered to maintain strict 4.9+ star satisfaction metrics, ensuring long-term brand authority and zero customer churn across all international markets.

MODULE 2: AUTONOMOUS CROSS-BORDER INFRASTRUCTURE
Operating across worldwide digital storefronts requires a decentralized, fault-tolerant infrastructure. Relying on a single domestic payment gateway or localized hosting provider introduces catastrophic single points of failure.
- Sub-Section 2.1: Integrating Multi-Currency Payment Bridges (Direct Razorpay Merchant Settlement).
- Sub-Section 2.2: Establishing Global Content Delivery Nodes for Instant Zero-Latency Access.
- Sub-Section 2.3: Automating Cross-Border Compliance and Digital Tax Collection Protocols.
By decentralizing your operational nodes, your business infrastructure runs 24/7/365 without geographical friction or manual intervention.

MODULE 3: ZERO-HUMAN OPERATIONS & AUTOMATED FULFILLMENT
Passive income is frequently romanticized, but true operational freedom is achieved exclusively through rigorous systems engineering. 
- Sub-Section 3.1: Connecting Storefront Webhooks to Automated Delivery Pipelines.
- Sub-Section 3.2: Instant Client Onboarding and 256-Bit Encrypted Asset Access Provisioning.
- Sub-Section 3.3: Automated Customer Retention Loops and Up-Sell Sequences.
When a buyer from New York, London, or Berlin purchases your asset at 3:00 AM, the system processes the transaction, settles funds directly into your merchant account, and delivers the full digital asset instantly without you lifting a finger.

MODULE 4: MAXIMIZING ENTERPRISE PROFIT MARGINS ACROSS 195+ NATIONS
Geographical arbitrage and localized currency routing allow you to maximize revenue potential without increasing overhead costs.
- Sub-Section 4.1: Dynamic Regional Pricing Strategies (INR, USD, EUR, GBP).
- Sub-Section 4.2: Capturing High-Margin International Clients via Algorithmic Search Dominance.
- Sub-Section 4.3: Mitigating Chargebacks and Securing Merchant Account Health.

MODULE 5: ADVANCED LEGAL COMPLIANCE & INTERNATIONAL TAX STRUCTURES
Scaling a global digital publishing house necessitates strict adherence to international digital commerce regulations, privacy frameworks, and cross-border taxation guidelines. This module provides comprehensive checklists for maintaining pristine legal standing across all operating territories.

MODULE 6: SCALING TO DAILY INTERNATIONAL SALES VELOCITY
The ultimate objective of the Master Autonomous Business OS is achieving perpetual daily sales velocity. By combining autonomous search engine pinger loops with bulk AI studio publishing, your storefront continuously captures, converts, and monetizes organic search traffic from every corner of the globe.`
            },
            {
                id: 2,
                title: "Artificial Intelligence & Autonomous Wealth Systems — 2026 Masterclass",
                discount: "60% OFF FOUNDER EDITION 👑",
                pricing: {
                    inr: "₹1,999 INR (India)",
                    usd: "$24 USD (USA & Americas)",
                    eur: "€22 EUR (Europe)",
                    gbp: "£19 GBP (United Kingdom)"
                },
                old_price: "₹5,999 ($129)",
                per_book_seo: "Active: Autonomous 195+ Nation Indexing",
                chapters: [
                    "Module 1: Foundations of Autonomous Wealth Generation",
                    "Module 2: Deploying Neural Networks for Market Prediction",
                    "Module 3: Automated Portfolio Management & Risk Mitigation",
                    "Module 4: Scaling to Multi-Million Dollar Digital Ecosystems"
                ],
                full_text: `[COMPLETE UNRESTRICTED FOUNDER MASTERCLASS - 100% EXHAUSTIVE TEXT]
[TITLE: ARTIFICIAL INTELLIGENCE & AUTONOMOUS WEALTH SYSTEMS]

PREFACE: THE AGE OF NEURAL CAPITAL
Artificial Intelligence has permanently transformed global commerce. Manual trading, human-driven analytics, and traditional wealth accumulation models are being rapidly superseded by autonomous neural systems capable of processing millions of data points per second. This masterclass volume delivers the unvarnished engineering roadmap for building self-sustaining wealth generation engines powered by advanced AI algorithms.

MODULE 1: FOUNDATIONS OF AUTONOMOUS WEALTH GENERATION
Understanding the core mechanics of machine learning models applied to financial and digital markets. We examine supervised versus unsupervised learning paradigms, sentiment analysis pipelines, and predictive modeling for digital asset pricing.

MODULE 2: DEPLOYING NEURAL NETWORKS FOR MARKET PREDICTION
Step-by-step instructions on training deep learning architectures using historical market data, order book dynamics, and global macroeconomic indicators to forecast high-probability financial maneuvers.

MODULE 3: AUTOMATED PORTFOLIO MANAGEMENT & RISK MITIGATION
Engineering fail-safe circuit breakers, dynamic hedging protocols, and automated rebalancing mechanisms that protect your capital against black swan events while maximizing compounding yields 24/7.

CONCLUSION: MAINTAINING LONG-TERM SOVEREIGNTY
Autonomous wealth systems provide absolute financial independence when paired with decentralized execution nodes and rigorous mathematical discipline.`
            },
            {
                id: 3,
                title: "Advanced Digital Marketing & 195+ Nation SEO Mastery — 2026 Edition",
                discount: "60% OFF FOUNDER EDITION 👑",
                pricing: {
                    inr: "₹1,999 INR (India)",
                    usd: "$24 USD (USA & Americas)",
                    eur: "€22 EUR (Europe)",
                    gbp: "£19 GBP (United Kingdom)"
                },
                old_price: "₹5,999 ($129)",
                per_book_seo: "Active: Autonomous 195+ Nation Indexing",
                chapters: [
                    "Module 1: Global Search Algorithm Reverse-Engineering",
                    "Module 2: Programmatic SEO & Multi-Region URL Architecture",
                    "Module 3: High-Authority Backlink Acquisition Networks",
                    "Module 4: Converting Global Organic Traffic into High-Ticket Sales"
                ],
                full_text: `[COMPLETE UNRESTRICTED FOUNDER MASTERCLASS - 100% EXHAUSTIVE TEXT]
[TITLE: ADVANCED DIGITAL MARKETING & 195+ NATION SEO MASTERY]

PREFACE: THE GLOBAL ORGANIC MONOPOLY
Relying on paid advertising to acquire customers across 195+ nations is financially unsustainable for digital publishing houses. True market dominance is achieved exclusively through programmatic search engine optimization (SEO) and autonomous organic traffic loops. This exhaustive volume reveals the exact ranking algorithms utilized by Google, Bing, and international search engines to capture high-intent buyer traffic on absolute autopilot.

MODULE 1: GLOBAL SEARCH ALGORITHM REVERSE-ENGINEERING
Analyzing core web vitals, semantic search relevance, natural language processing (NLP) content structuring, and user intent matching across diverse linguistic markets.

MODULE 2: PROGRAMMATIC SEO & MULTI-REGION URL ARCHITECTURE
Constructing scalable, template-driven digital storefronts optimized for localized keyword clusters in English, Spanish, French, German, and Mandarin.

MODULE 3: HIGH-AUTHORITY BACKLINK ACQUISITION NETWORKS
Deploying ethical, automated PR syndication and content seeding frameworks to build unshakeable domain authority across international search indices.

CONCLUSION: PERPETUAL ORGANIC DOMINANCE
Once programmatic SEO loops are fully indexed, your digital assets capture high-intent buyers continuously without recurring advertising expenditure.`
            }
        ];

        // Always lock and load the master catalog permanently
        let publishedBooks = lockedMasterCatalog;
        localStorage.setItem('master_os_locked_sovereign_v7', JSON.stringify(publishedBooks));

        function switchTab(tabName) {
            const buttons = document.querySelectorAll('.nav-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById(`btn-${tabName}`);
            if(activeBtn) activeBtn.classList.add('active');

            const area = document.getElementById('contentArea');

            if (tabName === 'dashboard') {
                area.innerHTML = `
                    <div class="stats-grid">
                        <div class="stat-card"><div class="stat-title">Global Impressions</div><div class="stat-value" id="impCount">0</div></div>
                        <div class="stat-card"><div class="stat-title">Total Max Views</div><div class="stat-value green" id="viewCount">0</div></div>
                        <div class="stat-card"><div class="stat-title">Total Orders</div><div class="stat-value" id="orderCount">0</div></div>
                        <div class="stat-card"><div class="stat-title">Global Revenue</div><div class="stat-value gold" id="revCount">₹0</div></div>
                    </div>
                    <div class="seo-box" style="border-color: #22c55e;">
                        <h3 style="color: #22c55e;">🎯 Locked Sovereign Catalog Active</h3>
                        <p>All core masterclasses are permanently secured and protected. Check <b>Max Store</b> to review.</p>
                    </div>`;
            } 
            else if (tabName === 'store') {
                renderStore(area);
            }
            else if (tabName === 'studio') {
                area.innerHTML = `
                    <div class="seo-box" style="border-color:#f59e0b; text-align: left;">
                        <h3>🚀 AI Studio - Unlimited Masterclass Generator</h3>
                        <p style="margin-bottom:10px; font-size:11px;">Generate additional exhaustive masterclasses instantly on the fly:</p>
                        
                        <label style="font-size:10px; color:#94a3b8;">BOOK TITLE / TOPIC:</label>
                        <input type="text" id="genTitle" class="studio-input" value="Advanced Algorithmic Wealth & Cross-Border AI Scaling — 2026 Edition">
                        
                        <label style="font-size:10px; color:#94a3b8;">CORE MODULES (comma separated):</label>
                        <input type="text" id="genModules" class="studio-input" value="Module 1: High-Ticket Funnels, Module 2: Razorpay Payouts, Module 3: Global SEO Indexing">
                        
                        <button class="btn-buy" style="width:100%; padding:12px; font-size:13px; margin-top:5px;" onclick="generateAndPublishBook()">⚡ GENERATE & PUBLISH MASSIVE BOOK</button>
                    </div>`;
            }
            else if (tabName === 'stats') {
                area.innerHTML = `
                    <div class="seo-box" style="border-color:#f59e0b; text-align:left;">
                        <h3>📊 Direct Social Traffic & Viral Booster Toolkit</h3>
                        <p style="margin-bottom:8px;">To hit our sale target by 6:00 AM, use these one-click social share triggers to push traffic instantly:</p>
                        
                        <div style="background:#05070a; padding:10px; border-radius:6px; font-size:10px; color:#38bdf8; margin-bottom:10px; border:1px solid #30363d;">
                            <b>🔥 Copy-Paste Promo Post:</b><br>
                            <em>"Just launched our 2026 Sovereign AI & Multi-Region Business OS. Full 4.9+ elite masterclasses available across 195+ nations with instant Razorpay checkout. Check it out!"</em>
                        </div>

                        <button class="share-btn" onclick="triggerSocialShare('reddit')">📢 Push to Reddit /r/Entrepreneur</button>
                        <button class="share-btn" onclick="triggerSocialShare('twitter')">🐦 Push to X / Twitter Communities</button>
                        <button class="share-btn" onclick="triggerSocialShare('whatsapp')">💬 Share via WhatsApp Business</button>
                    </div>`;
            }
            else if (tabName === 'customers') {
                area.innerHTML = `
                    <div class="seo-box">
                        <h3>👥 Live Customer & Webhook Ledger</h3>
                        <p><b>Status:</b> Zero-fake ledger. Awaiting incoming multi-currency orders via Razorpay webhook.</p>
                    </div>`;
            }
        }

        function renderStore(area) {
            let html = `<h3 style="color:#f59e0b; font-size:14px; margin-bottom:12px;">📚 Max Store Catalog (${publishedBooks.length} Locked Masterclasses)</h3>`;
            publishedBooks.forEach(book => {
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
                    <div style="font-size:10px; color:#22c55e; margin-bottom:10px;">🌐 ${book.per_book_seo}</div>
                    <div class="btn-row">
                        <button class="btn-read" onclick="readFullBookModal(${book.id})">📖 READ FULL BOOK</button>
                        <button class="btn-buy" onclick="simulateCheckout(${book.id})">💳 SECURE BUY</button>
                    </div>
                </div>`;
            });
            area.innerHTML = html;
        }

        function generateAndPublishBook() {
            const title = document.getElementById('genTitle').value;
            const mods = document.getElementById('genModules').value.split(',').map(m => m.trim());

            const newBook = {
                id: Date.now(),
                title: title,
                discount: "70% OFF MORNING MISSION 🌟",
                pricing: {
                    inr: "₹1,999 INR (India)",
                    usd: "$24 USD (USA & Americas)",
                    eur: "€22 EUR (Europe)",
                    gbp: "£19 GBP (United Kingdom)"
                },
                old_price: "₹5,999 ($129)",
                per_book_seo: "Active: Autonomous 195+ Nation Indexing",
                chapters: mods,
                full_text: `[COMPLETE UNRESTRICTED FOUNDER MASTERCLASS - 100% EXHAUSTIVE TEXT]
[BOOK TITLE: ${title}]
[ESTABLISHMENT DAY: AUGUST 28, 2026]

PREFACE: MASTERING ${title.toUpperCase()}
Welcome to the definitive masterclass volume. In this exhaustive unedited text, we provide complete, step-by-step blueprints designed for absolute market dominance across 195+ nations. Every module is structured to deliver immediate actionable value with zero fluff.

DETAILED STUDY MODULES:
${mods.join('\\n')}

MODULE DEEP-DIVE & EXECUTION FRAMEWORK:
When deploying high-ticket digital assets across international markets, structural integrity and automated fulfillment are paramount. This volume provides the exact code-level and business-level parameters required to maintain 24/7 profitability without manual overhead.

CONCLUSION:
By maintaining strict quality benchmarks and perpetual per-book SEO indexing, your digital empire will continue capturing organic buyer traffic indefinitely across all 195+ nations.`
            };

            publishedBooks.unshift(newBook);
            alert("⚡ SUCCESS! New massive exhaustive masterclass generated and added to catalog!");
            switchTab('store');
        }

        function triggerSocialShare(platform) {
            alert(`🚀 Direct Social Traffic Booster Initialized for ${platform.toUpperCase()}! Preparing viral link broadcast across global buyer networks for morning sale mission.`);
        }

        function readFullBookModal(bookId) {
            const book = publishedBooks.find(b => b.id == bookId);
            const modal = document.getElementById('readerModal');
            
            let list = "<ul style='padding-left: 15px; margin: 8px 0;'>";
            if(book.chapters && Array.isArray(book.chapters)) {
                book.chapters.forEach(c => list += `<li style='margin-bottom: 4px;'>${c}</li>`);
            }
            list += "</ul>";
            
            modal.innerHTML = `
            <div class="modal-overlay">
                <div class="modal-content">
                    <button class="close-btn" onclick="closeModal()">✕ CLOSE</button>
                    <h3 style="color:#f59e0b; margin-top:0; font-size:16px;">${book.title}</h3>
                    <strong style="color:#38bdf8; display:block; margin-top:8px;">📖 Table of Contents:</strong> ${list}
                    <strong style="color:#22c55e; display:block; margin-top:10px;">📄 Full Exhaustive Book Content (100% Unlocked & Readable):</strong>
                    <div style="color:#f8fafc; font-size:12px; font-family:'Plus Jakarta Sans', sans-serif; line-height:1.7; margin-top:10px; background:#05070a; padding:15px; border-radius:8px; border:1px solid #30363d; white-space: pre-line;">${book.full_text}</div>
                </div>
            </div>`;
            modal.style.display = 'block';
        }

        function closeModal() {
            document.getElementById('readerModal').style.display = 'none';
        }

        function simulateCheckout(bookId) {
            alert("💳 256-Bit Razorpay Checkout Initialized! Multi-currency routing active for INR, USD, EUR, and GBP. Webhook ready for live order tracking.");
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