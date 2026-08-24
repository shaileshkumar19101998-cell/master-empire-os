import os
import math
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

import pdf_engine

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)

app = FastAPI(title="Autonomous Business OS - Global Enterprise Engine", version="7.0.0")

# Mount Static Files for Secure Delivery
os.makedirs(pdf_engine.PDF_STORAGE_DIR, exist_ok=True)
app.mount("/static/pdfs", StaticFiles(directory=pdf_engine.PDF_STORAGE_DIR), name="pdfs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateOrderRequest(BaseModel):
    product_id: int
    customer_email: str = "customer@global-enterprise.org"
    coupon_code: Optional[str] = None

class ApprovalRequest(BaseModel):
    task_id: int
    decision: str

@app.get("/robots.txt", response_class=Response)
def get_robots():
    content = "User-agent: *\nAllow: /\nSitemap: [https://master-empire-os.onrender.com/sitemap.xml](https://master-empire-os.onrender.com/sitemap.xml)\n"
    return Response(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=Response)
def get_sitemap():
    try:
        with engine.connect() as conn:
            books_res = conn.execute(text("SELECT id, title FROM books ORDER BY id DESC;")).mappings().all()
        
        xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="[http://www.sitemaps.org/schemas/sitemap/0.9](http://www.sitemaps.org/schemas/sitemap/0.9)">']
        xml.append('<url><loc>[https://master-empire-os.onrender.com/](https://master-empire-os.onrender.com/)</loc><changefreq>daily</changefreq><priority>1.0</priority></url>')
        for b in books_res:
            xml.append(f'<url><loc>[https://master-empire-os.onrender.com/#book-](https://master-empire-os.onrender.com/#book-){b["id"]}</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>')
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
            orders_res = conn.execute(text("SELECT COUNT(*) AS total_orders FROM orders WHERE status = 'PAID';")).scalar() or 0
            rev_res = conn.execute(text("SELECT COALESCE(SUM(net_revenue), 0) FROM revenue_ledger;")).scalar() or 0

            total_visits = sum(b.get("visits", 0) for b in books_res)

        return {
            "metrics": {
                "total_products": len(books_res),
                "total_visits": total_visits,
                "total_orders": orders_res,
                "total_revenue": f"₹{rev_res:,}",
                "pending_approvals_count": len(pending_res)
            },
            "products": [dict(b) for b in books_res],
            "pending_approvals": [dict(p) for p in pending_res],
            "system_logs": [dict(l) for l in logs_res]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders/create")
def create_secure_order(req: CreateOrderRequest):
    try:
        with engine.begin() as conn:
            product = conn.execute(
                text("SELECT * FROM products WHERE id = :pid"), 
                {"pid": req.product_id}
            ).mappings().first()
            
            if not product:
                book = conn.execute(
                    text("SELECT * FROM books WHERE id = :bid"), 
                    {"bid": req.product_id}
                ).mappings().first()
                if not book:
                    raise HTTPException(status_code=404, detail="Product not found")
                
                price_val = book.get("price_val", 999)
                usd_val = max(1, math.floor(price_val / 82))
                slug_val = f"book-{book['id']}"
                conn.execute(text("""
                    INSERT INTO products (id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status)
                    VALUES (:id, :slug, :title, :tier, :niche, :pinr, :pusd, :pdf, 'ACTIVE')
                    ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, pdf_file_path = EXCLUDED.pdf_file_path
                """), {
                    "id": book["id"], "slug": slug_val, "title": book["title"],
                    "tier": book.get("tier", "Standard"), "niche": book.get("niche", "General"),
                    "pinr": price_val, "pusd": usd_val, "pdf": book.get("file", "")
                })
                gross_amount = price_val
                pdf_path = book.get("file", "")
            else:
                gross_amount = product["base_price_inr"]
                pdf_path = product["pdf_file_path"]

            cust = conn.execute(
                text("SELECT id FROM customers WHERE email = :email"), 
                {"email": req.customer_email.strip().lower()}
            ).mappings().first()
            
            if not cust:
                cust_id = conn.execute(
                    text("INSERT INTO customers (email) VALUES (:email) RETURNING id"), 
                    {"email": req.customer_email.strip().lower()}
                ).scalar()
            else:
                cust_id = cust["id"]

            coupon_id = None
            discount_amount = 0
            order_type = "PAID"
            requires_payment = True

            if req.coupon_code:
                code_clean = req.coupon_code.strip().upper()
                coupon = conn.execute(
                    text("SELECT * FROM coupons WHERE code = :code AND is_active = TRUE AND expires_at > NOW() FOR UPDATE"),
                    {"code": code_clean}
                ).mappings().first()

                if coupon:
                    coupon_id = coupon["id"]
                    if coupon["discount_type"] == "PERCENT":
                        discount_amount = math.floor(gross_amount * (coupon["discount_value"] / 100))
                    requires_payment = coupon["requires_payment"]
                    if not requires_payment or discount_amount >= gross_amount:
                        order_type = "FREE"
                        requires_payment = False

            net_amount = max(0, gross_amount - discount_amount)
            initial_status = "PAID" if not requires_payment else "PENDING"
            
            order_id = conn.execute(text("""
                INSERT INTO orders (customer_id, product_id, coupon_id, order_type, gross_amount, discount_amount, net_amount, currency, status)
                VALUES (:cid, :pid, :cpid, :otype, :gross, :disc, :net, 'INR', :status)
                RETURNING id
            """), {
                "cid": cust_id, "pid": req.product_id, "cpid": coupon_id,
                "otype": order_type, "gross": gross_amount, "disc": discount_amount,
                "net": net_amount, "status": initial_status
            }).scalar()

            if not requires_payment:
                conn.execute(text("""
                    INSERT INTO system_logs (module, status, message, created_at)
                    VALUES ('ORDER_ENGINE', 'SUCCESS', :msg, NOW())
                """), {"msg": f"Order #{order_id} activated via 100% Free Pass."})
                if coupon_id:
                    conn.execute(text("UPDATE coupons SET used_count = used_count + 1 WHERE id = :id"), {"id": coupon_id})

            return {
                "order_id": str(order_id),
                "gross_amount": gross_amount,
                "discount_amount": discount_amount,
                "net_amount": net_amount,
                "requires_payment": requires_payment,
                "order_type": order_type,
                "status": initial_status,
                "download_url": f"/api/download/{order_id}" if not requires_payment else None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{order_id}")
def download_secure_book(order_id: str):
    """Database-Verified Download Gatekeeper"""
    try:
        with engine.connect() as conn:
            order = conn.execute(
                text("SELECT * FROM orders WHERE id = :oid"), 
                {"oid": order_id}
            ).mappings().first()
            
            if not order:
                raise HTTPException(status_code=404, detail="Order not found.")
            if order["status"] != "PAID":
                raise HTTPException(status_code=403, detail="Payment pending. Access denied.")
            
            product = conn.execute(
                text("SELECT * FROM products WHERE id = :pid"), 
                {"pid": order["product_id"]}
            ).mappings().first()
            
            if not product or not product["pdf_file_path"]:
                # Fallback to books table
                book = conn.execute(
                    text("SELECT * FROM books WHERE id = :bid"), 
                    {"bid": order["product_id"]}
                ).mappings().first()
                if not book or not book.get("file"):
                    raise HTTPException(status_code=404, detail="PDF asset not yet generated for this product.")
                pdf_rel_path = book["file"]
            else:
                pdf_rel_path = product["pdf_file_path"]

        # Clean relative path to absolute
        clean_name = os.path.basename(pdf_rel_path)
        abs_path = os.path.join(pdf_engine.PDF_STORAGE_DIR, clean_name)
        
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="PDF file missing from secure storage.")
            
        return FileResponse(abs_path, media_type="application/pdf", filename=clean_name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/approve-task")
def approve_task(req: ApprovalRequest):
    """Human Approval Gate with Automated PDF Compilation & Integrity Gate"""
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

                # 1. Compile PDF Asset
                pdf_filename = f"asset_{req.task_id}_{int(time.time())}.pdf"
                pdf_res = pdf_engine.compile_markdown_to_pdf(
                    title=row["title"],
                    tier_level=tier_val,
                    target_niche=row["niche"],
                    markdown_content=row["proposed_content"],
                    output_filename=pdf_filename
                )

                if not pdf_res["success"]:
                    # Rollback / Log Failure
                    conn.execute(text("""
                        INSERT INTO system_logs (module, status, message, created_at)
                        VALUES ('PDF_ENGINE', 'FAILED', :msg, NOW())
                    """), {"msg": f"PDF compilation failed for task #{req.task_id}: {pdf_res.get('error')}"})
                    raise HTTPException(status_code=500, detail=f"PDF Generation Failed: {pdf_res.get('error')}")

                pdf_path = pdf_res["file_path"]

                # 2. Insert into legacy books table
                new_book_id = conn.execute(text("""
                    INSERT INTO books (title, niche, tier, price, price_val, market_price, badge, visits, orders, revenue, content_preview, file, seo_status, status)
                    VALUES (:title, :niche, :tier, :price, :price_val, :mkt_price, 'ENTERPRISE PRODUCTION ASSET', 0, 0, 0, :content, :file, '195+ Countries Live', 'ACTIVE')
                    RETURNING id
                """), {
                    "title": row["title"], "niche": row["niche"], "tier": tier_val,
                    "price": price_str, "price_val": price_val, "mkt_price": mkt_price,
                    "content": row["proposed_content"], "file": pdf_path
                }).scalar()

                # 3. Sync into products relational table
                usd_val = max(1, math.floor(price_val / 82))
                conn.execute(text("""
                    INSERT INTO products (id, slug, title, tier_level, target_niche, base_price_inr, base_price_usd, pdf_file_path, status)
                    VALUES (:id, :slug, :title, :tier, :niche, :pinr, :pusd, :pdf, 'ACTIVE')
                    ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, pdf_file_path = EXCLUDED.pdf_file_path, status = 'ACTIVE'
                """), {
                    "id": new_book_id, "slug": f"asset-{new_book_id}", "title": row["title"],
                    "tier": tier_val, "niche": row["niche"], "pinr": price_val, "pusd": usd_val, "pdf": pdf_path
                })

                conn.execute(text("""
                    INSERT INTO system_logs (module, status, message, created_at)
                    VALUES ('PDF_ENGINE', 'SUCCESS', :msg, NOW())
                """), {"msg": f"Asset #{new_book_id} compiled ({pdf_res['page_count']} pages, {pdf_res['file_size_kb']} KB in {pdf_res['elapsed_time_seconds']}s)"})

        return {"status": "SUCCESS", "pdf": pdf_res}
    except HTTPException:
        raise
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
        <title>Autonomous Business OS | Enterprise Assets</title>
        <meta name="robots" content="index, follow">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f3f4f6; margin: 0; padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1f2937; padding-bottom: 16px; margin-bottom: 24px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
            .card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 18px; }
            .card-title { font-size: 13px; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }
            .card-value { font-size: 24px; font-weight: bold; color: #fff; }
            .section { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 20px; margin-bottom: 24px; }
            .btn-preview { background: #374151; color: #60a5fa; border: 1px solid #4b5563; padding: 6px 10px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; margin-right:6px; }
            .btn-buy { background: #10b981; color: #fff; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1f2937; font-size: 14px; }
            th { color: #9ca3af; }
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; }
            .modal-content { background: #111827; border: 1px solid #374151; padding: 24px; border-radius: 12px; width: 800px; max-width: 95%; color: #f3f4f6; }
            .close-btn { background: #ef4444; color: #fff; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; float: right; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1 style="margin: 0; font-size: 22px;">Autonomous Business OS</h1>
                <p style="margin: 4px 0 0 0; color: #9ca3af; font-size: 14px;">Enterprise Engine (Phase 0.4 Active: PDF & Zero-Trust Delivery)</p>
            </div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-title">Active Products</div><div class="card-value" id="m-prod">--</div></div>
            <div class="card"><div class="card-title">Total Visits</div><div class="card-value" id="m-visits">--</div></div>
            <div class="card"><div class="card-title">Verified Paid Orders</div><div class="card-value" id="m-orders" style="color: #10b981;">--</div></div>
            <div class="card"><div class="card-title">Verified Net Revenue</div><div class="card-value" id="m-rev" style="color: #3b82f6;">--</div></div>
        </div>

        <div class="section">
            <h2 style="font-size: 16px; margin-top: 0;">📁 Published Enterprise Assets</h2>
            <table>
                <thead>
                    <tr><th>ID</th><th>Book Title</th><th>Target Market</th><th>Tier</th><th>Price</th><th>Format</th><th>Actions</th></tr>
                </thead>
                <tbody id="books-tbody"></tbody>
            </table>
        </div>

        <!-- Read Modal -->
        <div id="previewModal" class="modal">
            <div class="modal-content">
                <button class="close-btn" onclick="closeModal('previewModal')">Close ✕</button>
                <h3 id="modal-title" style="margin-top:0; color:#60a5fa;">Document Reader</h3>
                <div id="modal-body" style="background:#1f2937; padding:20px; border-radius:8px; font-size:13.5px; line-height:1.75; max-height:460px; overflow-y:auto; white-space:pre-wrap; font-family: monospace;"></div>
            </div>
        </div>

        <!-- Checkout Modal -->
        <div id="checkoutModal" class="modal">
            <div class="modal-content" style="max-width:520px;">
                <button class="close-btn" onclick="closeModal('checkoutModal')">Close ✕</button>
                <h3 id="chk-title" style="margin-top:0; color:#10b981;">Server-Verified Checkout</h3>
                <div id="chk-box" style="margin:16px 0; background:#1f2937; padding:16px; border-radius:8px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                        <span>Retail Base Price:</span>
                        <b id="chk-price" style="font-size:16px; color:#fff;">--</b>
                    </div>
                    <div style="display:flex; gap:8px; margin-top:12px;">
                        <input type="text" id="coupon-input" placeholder="Enter Promo Code (e.g. SHAILJA)" style="flex:1; padding:8px 12px; background:#111827; border:1px solid #4b5563; border-radius:6px; color:#fff; text-transform:uppercase;">
                    </div>
                    <div id="coupon-msg" style="font-size:12px; margin-top:8px;"></div>
                </div>

                <div id="delivery-section" style="display:none; background:#064e3b; border:1px solid #059669; padding:16px; border-radius:8px; margin-bottom:16px; text-align:center;">
                    <h4 style="margin:0 0 6px 0; color:#6ee7b7;">🎉 Access Granted!</h4>
                    <p style="font-size:13px; margin:0 0 12px 0; color:#d1fae5;" id="order-confirm-msg">Order registered in secure database.</p>
                    <div style="display:flex; gap:8px; justify-content:center;">
                        <button onclick="accessBookContent()" style="background:#10b981; color:#fff; border:none; padding:10px 16px; border-radius:6px; font-weight:bold; cursor:pointer;">📖 Read Online</button>
                        <a id="btn-download-pdf" href="#" target="_blank" style="display:none; background:#3b82f6; color:#fff; text-decoration:none; padding:10px 16px; border-radius:6px; font-weight:bold;">📥 Download Official PDF</a>
                    </div>
                </div>

                <button id="btn-confirm-order" onclick="executeServerOrder()" style="width:100%; background:#10b981; color:#fff; border:none; padding:10px; border-radius:8px; font-size:15px; font-weight:bold; cursor:pointer;">Create Order & Verify</button>
            </div>
        </div>

        <script>
            let allBooks = [];
            let selectedBook = null;

            async function loadData() {
                const res = await fetch('/api/analytics');
                const data = await res.json();
                document.getElementById('m-prod').innerText = data.metrics.total_products;
                document.getElementById('m-visits').innerText = data.metrics.total_visits;
                document.getElementById('m-orders').innerText = data.metrics.total_orders;
                document.getElementById('m-rev').innerText = data.metrics.total_revenue;

                allBooks = data.products;
                const tBody = document.getElementById('books-tbody');
                tBody.innerHTML = allBooks.map(b => `
                    <tr>
                        <td>#${b.id}</td>
                        <td><b>${b.title}</b></td>
                        <td>${b.niche || '--'}</td>
                        <td>${b.tier || 'Standard'}</td>
                        <td><b>${b.price}</b></td>
                        <td><span style="color:#60a5fa; font-size:11px;">📄 PDF + Web Reader</span></td>
                        <td>
                            <button class="btn-preview" onclick="openPreviewById(${b.id})">🔍 Read</button>
                            <button class="btn-buy" onclick="openCheckoutById(${b.id})">🛒 Buy</button>
                        </td>
                    </tr>
                `).join('');
            }

            function openPreviewById(id) {
                const b = allBooks.find(item => item.id === id);
                if (!b) return;
                selectedBook = b;
                document.getElementById('modal-title').innerText = b.title;
                document.getElementById('modal-body').innerText = b.content_preview || 'Content loading...';
                document.getElementById('previewModal').style.display = 'flex';
            }

            function openCheckoutById(id) {
                selectedBook = allBooks.find(item => item.id === id);
                if (!selectedBook) return;
                document.getElementById('chk-title').innerText = selectedBook.title;
                document.getElementById('chk-price').innerText = selectedBook.price;
                document.getElementById('coupon-input').value = "";
                document.getElementById('coupon-msg').innerText = "";
                document.getElementById('delivery-section').style.display = "none";
                document.getElementById('btn-download-pdf').style.display = "none";
                document.getElementById('chk-box').style.display = "block";
                document.getElementById('btn-confirm-order').style.display = "block";
                document.getElementById('checkoutModal').style.display = 'flex';
            }

            async function executeServerOrder() {
                const code = document.getElementById('coupon-input').value.trim();
                const res = await fetch('/api/orders/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ product_id: selectedBook.id, coupon_code: code, customer_email: 'buyer@global-net.org' })
                });
                const data = await res.json();
                
                if (res.ok) {
                    document.getElementById('chk-box').style.display = "none";
                    document.getElementById('btn-confirm-order').style.display = "none";
                    document.getElementById('delivery-section').style.display = "block";
                    document.getElementById('order-confirm-msg').innerText = `Order ID: ${data.order_id} | Net Payable: ₹${data.net_amount}`;
                    if (data.download_url) {
                        const dBtn = document.getElementById('btn-download-pdf');
                        dBtn.href = data.download_url;
                        dBtn.style.display = "inline-block";
                    }
                    loadData();
                } else {
                    document.getElementById('coupon-msg').innerText = data.detail || "Order Failed";
                    document.getElementById('coupon-msg').style.color = "#ef4444";
                }
            }

            function accessBookContent() {
                closeModal('checkoutModal');
                openPreviewById(selectedBook.id);
            }

            function closeModal(id) {
                document.getElementById(id).style.display = 'none';
            }

            loadData();
        </script>
    </body>
    </html>
    """