from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3
import json
import seo_engine

router = APIRouter()

def get_db():
    conn = sqlite3.connect('fastapi_local.db' if 'fastapi_local.db' in dir() else 'autonomous_local.db')
    conn.row_factory = sqlite3.Row
    return conn

@router.get('/sitemap.xml')
def get_sitemap():
    conn = get_db()
    prods = conn.cursor().execute("SELECT slug FROM products WHERE status IN ('ACTIVE', 'PUBLISHED')").fetchall()
    conn.close()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">', '  <url><loc>https://masterempire.ai/</loc></url>']
    for p in prods:
        xml.append('  <url><loc>https://masterempire.ai/product/' + str(p["slug"]) + '</loc></url>')
    xml.append('</urlset>')
    return Response(content='\n'.join(xml), media_type='application/xml')

@router.get('/robots.txt')
def get_robots():
    content = "User-agent: *\nAllow: /\nSitemap: https://masterempire.ai/sitemap.xml"
    return Response(content=content, media_type='text/plain')

@router.get('/product/{slug}')
def get_product(slug: str):
    conn = get_db()
    row = conn.cursor().execute("SELECT * FROM products WHERE slug = ? AND status IN ('ACTIVE', 'PUBLISHED')", (slug,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    prod = dict(row)
    seo = seo_engine.ensure_product_seo(prod['id'])
    conn.close()
    m_title = str(seo.get('meta_title', prod['title']))
    m_desc = str(seo.get('meta_description', ''))
    p_title = str(prod.get('title', ''))
    p_niche = str(prod.get('target_niche', ''))
    html = '<!DOCTYPE html><html><head><title>' + m_title + '</title><meta name="description" content="' + m_desc + '"></head><body><h1>' + p_title + '</h1><p>Niche: ' + p_niche + '</p></body></html>'
    return HTMLResponse(content=html)

@router.get('/seo/{slug}')
def get_seo(slug: str):
    conn = get_db()
    row = conn.cursor().execute("SELECT id FROM products WHERE slug = ?", (slug,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")
    prod = dict(row)
    seo = seo_engine.ensure_product_seo(prod['id'])
    conn.close()
    return JSONResponse(content=dict(seo))
