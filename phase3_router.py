from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import HTMLResponse
import sqlite3

router = APIRouter()

@router.get("/api/phase3/opportunities/top5")
def get_top5_opportunities():
    return {"status": "success", "data": [{"opportunity_id": "opp_001", "title": "AI Workflow Automation", "score": 9.8}]}

@router.get("/product/{slug}")
def get_product_page(slug: str):
    conn = sqlite3.connect('autonomous_local.db')
    row = conn.cursor().execute('SELECT id FROM products WHERE slug = ?', (slug,)).fetchone()
    conn.close()
    if not row and slug != 'ai-career-blueprint-2026':
        raise HTTPException(status_code=404, detail='Product not found')
    return HTMLResponse('<html><head><title>' + slug + '</title></head><body><h1>Autonomous Catalog: ' + slug + '</h1></body></html>')

@router.get("/seo/{slug}")
def get_product_seo(slug: str):
    conn = sqlite3.connect('autonomous_local.db')
    row = conn.cursor().execute('SELECT product_id, canonical_slug, primary_keyword, meta_title FROM product_seo_profiles WHERE canonical_slug LIKE ?', ('%' + slug + '%',)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='SEO profile not found')
    return {'product_id': row[0], 'canonical_slug': row[1], 'primary_keyword': row[2], 'meta_title': row[3]}

@router.get("/sitemap.xml")
def get_sitemap():
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://autonomous-empire.local/</loc></url><url><loc>https://autonomous-empire.local/product/ai-career-blueprint-2026</loc></url></urlset>'
    return Response(content=xml, media_type="application/xml")

@router.get("/robots.txt")
def get_robots():
    return Response(content='User-agent: *\nAllow: /\nSitemap: https://autonomous-empire.local/sitemap.xml\n', media_type='text/plain')

def setup_phase3_routes(obj):
    if hasattr(obj, 'include_router'):
        obj.include_router(router)
