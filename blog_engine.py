import sqlite3, json, datetime, re
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

def get_db():
    conn = sqlite3.connect("autonomous_local.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_blog_schema():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS blog_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        content_html TEXT NOT NULL,
        excerpt TEXT,
        primary_keyword TEXT,
        secondary_keywords TEXT,
        search_intent TEXT,
        canonical_url TEXT,
        status TEXT DEFAULT 'PUBLISHED',
        content_type TEXT DEFAULT 'PILLAR',
        json_ld TEXT,
        faq_schema TEXT,
        published_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS attribution_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        product_id INTEGER,
        blog_post_id INTEGER,
        source TEXT,
        medium TEXT,
        campaign TEXT,
        content TEXT,
        landing_path TEXT,
        created_at TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()

def generate_blog_ecosystem_for_product(product_id: int):
    init_blog_schema()
    conn = get_db()
    cur = conn.cursor()
    prod = cur.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not prod or prod["status"] not in ["ACTIVE", "PUBLISHED"]:
        conn.close()
        return {"status": "skipped", "reason": "Product inactive or missing"}
    
    seo = cur.execute("SELECT * FROM product_seo_profiles WHERE product_id = ?", (product_id,)).fetchone()
    kw = seo["primary_keyword"] if seo and seo["primary_keyword"] else prod["title"]
    now = datetime.datetime.utcnow().isoformat()
    
    # Pillar Post
    slug_pillar = f"complete-guide-to-{prod['slug']}"
    title_pillar = f"The Complete Guide to {prod['title']}"
    html_pillar = f"<article><h1>{title_pillar}</h1><p>Comprehensive research and architectural guide on {kw} in modern business automation.</p><div class='cta-box'><a href='/product/{prod['slug']}?utm_source=blog&utm_medium=internal_pillar'>Access the full official handbook here</a></div></article>"
    json_ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": title_pillar})
    
    cur.execute("""INSERT OR IGNORE INTO blog_posts 
        (product_id, title, slug, content_html, excerpt, primary_keyword, canonical_url, status, content_type, json_ld, published_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PUBLISHED', 'PILLAR', ?, ?, ?, ?)""",
        (product_id, title_pillar, slug_pillar, html_pillar, f"Learn all about {kw}", kw, f"/blog/{slug_pillar}", json_ld, now, now, now))
    conn.commit()
    conn.close()
    return {"status": "success", "product_id": product_id, "slug": slug_pillar}

def sync_all_blog_content():
    init_blog_schema()
    conn = get_db()
    cur = conn.cursor()
    prods = cur.execute("SELECT id FROM products WHERE status IN ('ACTIVE', 'PUBLISHED')").fetchall()
    conn.close()
    res = {}
    for p in prods:
        res[p["id"]] = generate_blog_ecosystem_for_product(p["id"])
    return res

@router.get("/blog", response_class=HTMLResponse)
def get_blog_index():
    conn = get_db()
    cur = conn.cursor()
    posts = cur.execute("SELECT * FROM blog_posts WHERE status = 'PUBLISHED' ORDER BY id DESC").fetchall()
    conn.close()
    cards = ""
    for p in posts:
        cards += f"<div style='background:#1e293b; padding:16px; margin-bottom:12px; border-radius:8px;'><h2><a href='/blog/{p["slug"]}' style='color:#38bdf8; text-decoration:none;'>{p["title"]}</a></h2><p>{p["excerpt"]}</p></div>"
    return f"<!doctype html><html><body style='background:#0f172a; color:white; font-family:sans-serif; padding:20px;'><h1>Master Empire OS — Knowledge Hub</h1>{cards}</body></html>"

@router.get("/blog/{slug}", response_class=HTMLResponse)
def get_blog_post(slug: str):
    conn = get_db()
    cur = conn.cursor()
    post = cur.execute("SELECT * FROM blog_posts WHERE slug = ? AND status = 'PUBLISHED'", (slug,)).fetchone()
    conn.close()
    if not post:
        raise HTTPException(status_code=404, detail="Article not found")
    return f"<!doctype html><html><head><title>{post['title']}</title><script type='application/ld+json'>{post['json_ld']}</script></head><body style='background:#0f172a; color:white; font-family:sans-serif; padding:30px; max-width:800px; margin:auto;'>{post['content_html']}</body></html>"
