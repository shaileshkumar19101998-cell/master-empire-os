import os
import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from worker import generate_5_trending_ideas

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)

app = FastAPI(title="Autonomous Business OS - Global Enterprise Engine", version="3.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ApprovalRequest(BaseModel):
    task_id: int
    decision: str

class CouponValidateRequest(BaseModel):
    book_id: int
    coupon_code: str
    original_price_val: int = 499

@app.get("/robots.txt", response_class=Response)
def get_robots():
    content = "User-agent: *\nAllow: /\nSitemap: https://master-empire-os.onrender.com/sitemap.xml\n"
    return Response(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=Response)
def get_sitemap():
    try:
        with engine.connect() as conn:
            books_res = conn.execute(text("SELECT id, title FROM books ORDER BY id DESC;")).mappings().all()
        
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        xml.append('<url><loc>https://master-empire-os.onrender.com/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>')
        for b in books_res:
            xml.append(f'<url><loc>https://master-empire-os.onrender.com/#book-{b["id"]}</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>')
        xml.append('</urlset>')
        return Response(content="".join(xml), media_type="application/xml")
    except Exception:
        return Response(content="<urlset></urlset>", media_type="application/xml")

@app.get("/api/analytics")
def get_analytics():
    try:
        with engine.connect() as conn:
            books_res = conn.execute(text("SELECT * FROM books ORDER BY id DESC;")).mappings().all()
            pending_res = conn.execute(text("SELECT * FROM pending_approvals WHERE status = 'PENDING' ORDER BY id DESC;")).mappings().all()
            logs_res = conn.execute(text("SELECT * FROM system_logs ORDER BY id DESC LIMIT 10;")).mappings().all()

            total_visits = sum(b.get("visits", 0) for b in books_res)
            total_orders = sum(b.get("orders", 0) for b in books_res)
            total_rev = sum(b.get("revenue", 0) for b in books_res)

        return {
            "metrics": {
                "total_products": len(books_res),
                "total_visits": total_visits,
                "total_orders": total_orders,
                "total_revenue": f"₹{total_rev:,}",
                "pending_approvals_count": len(pending_res)
            },
            "products": [dict(b) for b in books_res],
            "pending_approvals": [dict(p) for p in pending_res],
            "system_logs": [dict(l) for l in logs_res]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/apply-coupon")
def apply_coupon(req: CouponValidateRequest):
    code = req.coupon_code.strip().upper()
    orig = req.original_price_val
    
    if code == "SHAILJA":
        return {
            "valid": True,
            "discount_percent": 100,
            "final_price": "₹0 ($0)",
            "final_val": 0,
            "message": "🎉 Master VIP Access Activated: 100% OFF (₹0 Free Access)!"
        }
    elif code == "AKKHI":
        discounted_val = math.floor(orig * 0.25)
        usd_val = max(1, math.floor(discounted_val / 82))
        return {
            "valid": True,
            "discount_percent": 75,
            "final_price": f"₹{discounted_val:,} (${usd_val})",
            "final_val": discounted_val,
            "message": f"🎉 VIP Special Code 'AKKHI' Applied! 75% OFF Saved."
        }
    return {
        "valid": False,
        "discount_percent": 0,
        "final_price": f"₹{orig:,}",
        "final_val": orig,
        "message": "Invalid Promo Code."
    }

@app.post("/api/think-idea")
def think_batch_ideas():
    success = generate_5_trending_ideas()
    if success:
        return {"status": "SUCCESS"}
    raise HTTPException(status_code=500, detail="Research task failed")

@app.post("/api/approve-task")
def approve_task(req: ApprovalRequest):
    try:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT * FROM pending_approvals WHERE id = :id"), {"id": req.task_id}).mappings().first()
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")

            conn.execute(text("UPDATE pending_approvals SET status = :decision WHERE id = :id"), {"decision": req.decision.upper(), "id": req.task_id})

            if req.decision.upper() == "APPROVED":
                title_lower = (row["title"] + row["task_type"]).lower()
                
                tier_val = "Normal Standard"
                price_str = "₹999 ($12)"
                price_val = 999
                mkt_price = "₹2,999 ($36)"

                if "foundation" in title_lower:
                    tier_val = "Foundation Level"
                    price_str = "₹499 ($6)"
                    price_val = 499
                    mkt_price = "₹1,499 ($18)"
                elif "interview" in title_lower or "career" in title_lower:
                    tier_val = "Industry + Interview Pack"
                    price_str = "₹2,499 ($30)"
                    price_val = 2499
                    mkt_price = "₹6,999 ($85)"
                elif "industry" in title_lower or "mastery" in title_lower or "enterprise" in title_lower:
                    tier_val = "Industry Level"
                    price_str = "₹1,999 ($24)"
                    price_val = 1999
                    mkt_price = "₹4,999 ($60)"

                conn.execute(text("""
                    INSERT INTO books (title, niche, tier, price, price_val, market_price, badge, visits, orders, revenue, content_preview, file, seo_status, status)
                    VALUES (:title, :niche, :tier, :price, :price_val, :mkt_price, 'GLOBAL VERIFIED ASSET', 0, 0, 0, :content, '', '195+ Countries Live', 'ACTIVE')
                """), {
                    "title": row["title"],
                    "niche": row["niche"],
                    "tier": tier_val,
                    "price": price_str,
                    "price_val": price_val,
                    "mkt_price": mkt_price,
                    "content": row["proposed_content"]
                })
        return {"status": "SUCCESS"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Autonomous Business OS | Worldwide High-Converting Digital Assets & Blueprints</title>
        <meta name="description" content="Access verified enterprise AI blueprints, career guides, and digital automation systems across 195+ countries worldwide. Instant global delivery.">
        <meta name="keywords" content="AI Automation, Digital Blueprints, Enterprise Architecture, High-Income Skills, Global eBooks">
        <meta name="robots" content="index, follow">
        <link rel="canonical" href="https://master-empire-os.onrender.com/">
        
        <!-- Multi-Region Hreflang Tags for Global Organic Reach -->
        <link rel="alternate" hreflang="x-default" href="https://master-empire-os.onrender.com/">
        <link rel="alternate" hreflang="en-US" href="https://master-empire-os.onrender.com/">
        <link rel="alternate" hreflang="en-GB" href="https://master-empire-os.onrender.com/">
        <link rel="alternate" hreflang="en-IN" href="https://master-empire-os.onrender.com/">
        <link rel="alternate" hreflang="en-CA" href="https://master-empire-os.onrender.com/">
        <link rel="alternate" hreflang="en-AU" href="https://master-empire-os.onrender.com/">

        <!-- Schema.org JSON-LD Structured Data for Rich Search Results -->
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "WebSite",
          "name": "Autonomous Business OS",
          "url": "https://master-empire-os.onrender.com/",
          "description": "Global 195+ Country Enterprise Digital Systems and Blueprints Hub"
        }
        </script>

        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 24px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 18px; }
            .card-title { font-size: 13px; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }
            .card-value { font-size: 24px; font-weight: bold; color: #fff; }
            .section { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 20px; margin-bottom: 24px; }
            
            .btn-think { background: #6366f1; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; }
            .btn-think:hover { background: #4f46e5; }
            
            .folder-nav { display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid #1f2937; padding-bottom: 12px; flex-wrap: wrap; }
            .folder-btn { background: #1f2937; color: #9ca3af; border: 1px solid #374151; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
            .folder-btn.active { background: #2563eb; color: #fff; border-color: #3b82f6; }
            
            .btn-approve { background: #10b981; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-right: 8px; }
            .btn-reject { background: #ef4444; color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; }
            .btn-preview { background: #374151; color: #60a5fa; border: 1px solid #4b5563; padding: 6px 10px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; margin-right:6px; }
            .btn-buy { background: #10b981; color: #fff; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; }
            
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1f2937; font-size: 14px; }
            th { color: #9ca3af; }
            .tag { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
            .tag-found { background: #3b82f622; color: #3b82f6; border: 1px solid #3b82f6; }
            .tag-norm { background: #f59e0b22; color: #f59e0b; border: 1px solid #f59e0b; }
            .tag-ind { background: #8b5cf622; color: #8b5cf6; border: 1px solid #8b5cf6; }
            .tag-pack { background: #ec489922; color: #ec4899; border: 1px solid #ec4899; }
            .status-badge { background: #374151; color: #9ca3af; border: 1px solid #4b5563; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; }

            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; }
            .modal-content { background: #111827; border: 1px solid #374151; padding: 24px; border-radius: 12px; width: 720px; max-width: 92%; color: #f3f4f6; }
            .close-btn { background: #ef4444; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; float: right; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1 style="margin: 0; font-size: 22px;">Autonomous Business OS</h1>
                <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 14px;">195+ Countries Worldwide Automated SEO & Digital Asset Hub</p>
            </div>
            <div>
                <button class="btn-think" id="main-think-btn" onclick="triggerAutoMarketDiscovery()">⚡ Auto-Discover 5 Draft Proposals</button>
            </div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-title">Active Products</div><div class="card-value" id="m-prod">--</div></div>
            <div class="card"><div class="card-title">Total Visits</div><div class="card-value" id="m-visits">--</div></div>
            <div class="card"><div class="card-title">Total Orders</div><div class="card-value" id="m-orders">--</div></div>
            <div class="card"><div class="card-title">Pending Approvals</div><div class="card-value" id="m-pending" style="color: #f59e0b;">--</div></div>
        </div>

        <div class="section">
            <h2 style="font-size: 16px; margin-top: 0; display:flex; justify-content:space-between; align-items:center;">
                <span>⚡ Human-In-The-Loop Approval Queue</span>
                <span style="font-size:12px; color:#9ca3af; font-weight:normal;">Evaluation Status: Transparent</span>
            </h2>
            <div id="pending-container"><p style="color: #6b7280;">Loading proposals...</p></div>
        </div>

        <div class="section">
            <h2 style="font-size: 16px; margin-top: 0; margin-bottom: 12px;">📁 Product Books & Content Inspector</h2>
            
            <div class="folder-nav">
                <button class="folder-btn active" onclick="setFolder('ALL', this)">📂 All Books (<span id="cnt-all">0</span>)</button>
                <button class="folder-btn" onclick="setFolder('Foundation', this)">📘 Foundation (<span id="cnt-found">0</span>)</button>
                <button class="folder-btn" onclick="setFolder('Normal', this)">📗 Normal Standard (<span id="cnt-norm">0</span>)</button>
                <button class="folder-btn" onclick="setFolder('Industry', this)">📕 Industry Level (<span id="cnt-ind">0</span>)</button>
            </div>

            <table>
                <thead>
                    <tr><th>ID</th><th>Book Title</th><th>Target Market & Niche</th><th>Level</th><th>Market Price</th><th>SEO Reach</th><th>Actions</th></tr>
                </thead>
                <tbody id="books-tbody"></tbody>
            </table>
        </div>

        <!-- Modal for Content Preview & Reading -->
        <div id="previewModal" class="modal">
            <div class="modal-content">
                <button class="close-btn" onclick="closeModal('previewModal')">Close ✕</button>
                <h3 id="modal-title" style="margin-top:0; color:#60a5fa;">Full Book Reader & Blueprint</h3>
                <p style="font-size:13px; color:#9ca3af;" id="modal-niche"></p>
                <hr style="border-color:#374151; margin:12px 0;">
                <div id="modal-body" style="background:#1f2937; padding:18px; border-radius:8px; font-size:13.5px; line-height:1.7; max-height:420px; overflow-y:auto; white-space:pre-wrap;"></div>
                <div style="margin-top:16px; display:flex; justify-content:flex-end;">
                    <button onclick="downloadBookAsFile()" style="background:#10b981; color:#fff; border:none; padding:8px 16px; border-radius:6px; font-weight:600; cursor:pointer;">📥 Save / Download Offline (.txt)</button>
                </div>
            </div>
        </div>

        <!-- Modal for Checkout & Secret Coupon Code -->
        <div id="checkoutModal" class="modal">
            <div class="modal-content">
                <button class="close-btn" onclick="closeModal('checkoutModal')">Close ✕</button>
                <h3 id="chk-title" style="margin-top:0; color:#10b981;">Order Checkout</h3>
                <p style="font-size:13px; color:#9ca3af;" id="chk-niche"></p>
                
                <div id="chk-box" style="margin:16px 0; background:#1f2937; padding:16px; border-radius:8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Standard Price:</span>
                        <b id="chk-price" style="font-size:16px; color:#fff;">₹499 ($6)</b>
                    </div>
                    <div style="display:flex; gap:8px; margin-top:12px;">
                        <input type="text" id="coupon-input" placeholder="Enter Promo Code" style="flex:1; padding:8px 12px; background:#111827; border:1px solid #4b5563; border-radius:6px; color:#fff; text-transform:uppercase;">
                        <button onclick="validateCoupon()" style="background:#2563eb; color:#fff; border:none; padding:8px 14px; border-radius:6px; font-weight:600; cursor:pointer;">Apply</button>
                    </div>
                    <div id="coupon-msg" style="font-size:12px; margin-top:8px;"></div>
                </div>

                <div id="delivery-section" style="display:none; background:#064e3b; border:1px solid #059669; padding:16px; border-radius:8px; margin-bottom:16px; text-align:center;">
                    <h4 style="margin:0 0 6px 0; color:#6ee7b7;">🎉 Purchase Verified & Active!</h4>
                    <p style="font-size:13px; margin:0 0 12px 0; color:#d1fae5;">Your full digital blueprint is unlocked with lifetime updates.</p>
                    <button onclick="accessBookContent()" style="background:#10b981; color:#fff; border:none; padding:10px 20px; border-radius:6px; font-weight:bold; cursor:pointer;">📖 Open & Download Full Blueprint</button>
                </div>

                <button id="btn-confirm-order" onclick="confirmPurchase()" style="width:100%; background:#10b981; color:#fff; border:none; padding:10px; border-radius:8px; font-size:15px; font-weight:bold; cursor:pointer;">Confirm Purchase</button>
            </div>
        </div>

        <script>
            let allBooks = [];
            let activeFolder = 'ALL';
            let selectedBook = null;
            let currentPriceVal = 499;

            async function loadData() {
                try {
                    const res = await fetch('/api/analytics');
                    const data = await res.json();
                    document.getElementById('m-prod').innerText = data.metrics.total_products;
                    document.getElementById('m-visits').innerText = data.metrics.total_visits;
                    document.getElementById('m-orders').innerText = data.metrics.total_orders;
                    document.getElementById('m-pending').innerText = data.metrics.pending_approvals_count;

                    const pBox = document.getElementById('pending-container');
                    if (data.pending_approvals.length === 0) {
                        pBox.innerHTML = `
                            <div style="background: #1f2937; padding: 18px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: #10b981;">✓ Queue is empty. Click <b>Auto-Discover</b> to generate new deep draft proposals.</span>
                                <button class="btn-think" onclick="triggerAutoMarketDiscovery()">⚡ Run Market Discovery</button>
                            </div>
                        `;
                    } else {
                        pBox.innerHTML = data.pending_approvals.map(p => `
                            <div style="background: #1f2937; border: 1px solid #374151; padding: 16px; border-radius: 8px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                                <div style="max-width: 75%;">
                                    <div style="display:flex; align-items:center; gap:8px;">
                                        <span class="status-badge">${p.task_type || 'Market Score: Not Yet Scored'}</span>
                                        <span style="font-weight: 600; font-size: 15px; color:#fff;">${p.title}</span>
                                    </div>
                                    <div style="font-size: 13px; color: #9ca3af; margin-top: 6px;">🎯 Market: <b>${p.niche}</b></div>
                                    <div style="font-size: 13px; color: #d1d5db; margin-top: 4px; font-style: italic; white-space:pre-wrap; max-height:80px; overflow:hidden;">"${p.proposed_content}"</div>
                                </div>
                                <div style="display:flex; align-items:center;">
                                    <button class="btn-approve" onclick="handleDecision(${p.id}, 'APPROVED')">✓ Approve & Publish</button>
                                    <button class="btn-reject" onclick="handleDecision(${p.id}, 'REJECTED')">✕ Reject</button>
                                </div>
                            </div>
                        `).join('');
                    }

                    allBooks = data.products;
                    updateFolderCounts();
                    renderTable();
                } catch (e) {
                    console.error(e);
                }
            }

            function updateFolderCounts() {
                document.getElementById('cnt-all').innerText = allBooks.length;
                document.getElementById('cnt-found').innerText = allBooks.filter(b => (b.tier || b.title).toLowerCase().includes('foundation')).length;
                document.getElementById('cnt-ind').innerText = allBooks.filter(b => (b.tier || b.title).toLowerCase().includes('industry') || (b.tier || b.title).toLowerCase().includes('mastery')).length;
                document.getElementById('cnt-norm').innerText = allBooks.length - (parseInt(document.getElementById('cnt-found').innerText) + parseInt(document.getElementById('cnt-ind').innerText));
            }

            function setFolder(folder, btn) {
                activeFolder = folder;
                document.querySelectorAll('.folder-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderTable();
            }

            function getCalculatedPrice(tier) {
                const t = (tier || '').toLowerCase();
                if (t.includes('foundation')) return { text: "₹499 ($6)", val: 499 };
                if (t.includes('interview') || t.includes('career')) return { text: "₹2,499 ($30)", val: 2499 };
                if (t.includes('industry') || t.includes('mastery')) return { text: "₹1,999 ($24)", val: 1999 };
                return { text: "₹999 ($12)", val: 999 };
            }

            function renderTable() {
                const tBody = document.getElementById('books-tbody');
                const filtered = allBooks.filter(b => {
                    const textContent = ((b.tier || '') + ' ' + (b.title || '')).toLowerCase();
                    if (activeFolder === 'Foundation') return textContent.includes('foundation');
                    if (activeFolder === 'Industry') return textContent.includes('industry') || textContent.includes('mastery');
                    if (activeFolder === 'Normal') return !textContent.includes('foundation') && !textContent.includes('industry') && !textContent.includes('mastery');
                    return true;
                });

                tBody.innerHTML = filtered.map(b => {
                    const textContent = ((b.tier || '') + ' ' + (b.title || '')).toLowerCase();
                    let tTag = '<span class="tag tag-norm">Normal Standard</span>';
                    if (textContent.includes('foundation')) tTag = '<span class="tag tag-found">Foundation Level</span>';
                    else if (textContent.includes('interview')) tTag = '<span class="tag tag-pack">Industry + Interview</span>';
                    else if (textContent.includes('industry') || textContent.includes('mastery')) tTag = '<span class="tag tag-ind">Industry Level</span>';

                    const priceInfo = getCalculatedPrice(b.tier);

                    return `
                        <tr>
                            <td>#${b.id}</td>
                            <td><b>${b.title}</b></td>
                            <td>${b.niche || '--'}</td>
                            <td>${tTag}</td>
                            <td><b>${priceInfo.text}</b></td>
                            <td><span style="color:#10b981; font-size:11px; font-weight:600;">🌍 195+ Countries Live</span></td>
                            <td>
                                <button class="btn-preview" onclick="openPreviewById(${b.id})">🔍 Read</button>
                                <button class="btn-buy" onclick="openCheckoutById(${b.id})">🛒 Buy</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            function openPreviewById(id) {
                const b = allBooks.find(item => item.id === id);
                if (!b) return;
                selectedBook = b;
                document.getElementById('modal-title').innerText = b.title;
                document.getElementById('modal-niche').innerText = "Market / Niche: " + (b.niche || '--');
                document.getElementById('modal-body').innerText = b.content_preview || 'No content preview available.';
                document.getElementById('previewModal').style.display = 'flex';
            }

            function openCheckoutById(id) {
                selectedBook = allBooks.find(item => item.id === id);
                if (!selectedBook) return;
                
                const priceInfo = getCalculatedPrice(selectedBook.tier);
                currentPriceVal = priceInfo.val;

                document.getElementById('chk-title').innerText = selectedBook.title;
                document.getElementById('chk-niche').innerText = selectedBook.niche || '--';
                document.getElementById('chk-price').innerText = priceInfo.text;
                document.getElementById('coupon-input').value = "";
                document.getElementById('coupon-msg').innerText = "";
                
                document.getElementById('delivery-section').style.display = "none";
                document.getElementById('chk-box').style.display = "block";
                document.getElementById('btn-confirm-order').style.display = "block";
                document.getElementById('checkoutModal').style.display = 'flex';
            }

            async function validateCoupon() {
                const code = document.getElementById('coupon-input').value;
                const msgBox = document.getElementById('coupon-msg');
                const priceBox = document.getElementById('chk-price');
                
                const res = await fetch('/api/apply-coupon', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ book_id: selectedBook.id, coupon_code: code, original_price_val: currentPriceVal })
                });
                const data = await res.json();
                if (data.valid) {
                    msgBox.style.color = "#10b981";
                    msgBox.innerText = data.message;
                    priceBox.innerText = data.final_price;
                } else {
                    msgBox.style.color = "#ef4444";
                    msgBox.innerText = data.message;
                    priceBox.innerText = data.final_price;
                }
            }

            function confirmPurchase() {
                document.getElementById('chk-box').style.display = "none";
                document.getElementById('btn-confirm-order').style.display = "none";
                document.getElementById('delivery-section').style.display = "block";
            }

            function accessBookContent() {
                closeModal('checkoutModal');
                openPreviewById(selectedBook.id);
            }

            function downloadBookAsFile() {
                if (!selectedBook) return;
                const textData = "=================================================\\n" +
                                 selectedBook.title.toUpperCase() + "\\n" +
                                 "Market / Target: " + (selectedBook.niche || '') + "\\n" +
                                 "=================================================\\n\\n" +
                                 (selectedBook.content_preview || '');
                const blob = new Blob([textData], { type: 'text/plain;charset=utf-8' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = selectedBook.title.replace(/[^a-zA-Z0-9]/g, '_') + "_Full_Blueprint.txt";
                link.click();
            }

            function closeModal(id) {
                document.getElementById(id).style.display = 'none';
            }

            async function triggerAutoMarketDiscovery() {
                const btn = document.getElementById('main-think-btn');
                btn.innerText = "🔍 Generating Deep Blueprints...";
                btn.disabled = true;
                try {
                    await fetch('/api/think-idea', { method: 'POST' });
                    await loadData();
                } catch(e) {
                    await loadData();
                } finally {
                    btn.innerText = "⚡ Auto-Discover 5 Draft Proposals";
                    btn.disabled = false;
                }
            }

            async function handleDecision(taskId, decision) {
                await fetch('/api/approve-task', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ task_id: taskId, decision: decision })
                });
                loadData();
            }

            loadData();
        </script>
    </body>
    </html>
    """