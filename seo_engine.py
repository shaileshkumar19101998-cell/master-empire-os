import sqlite3
import json
import datetime

def get_db():
    conn = sqlite3.connect('fastapi_local.db' if 'fastapi_local.db' in dir() else 'autonomous_local.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_seo_quality_score(p):
    score = 50.0
    if p.get('primary_keyword'):
        score += 10.0
    if p.get('meta_title') and len(str(p.get('meta_title'))) >= 10:
        score += 10.0
    if p.get('meta_description') and len(str(p.get('meta_description'))) >= 20:
        score += 10.0
    if p.get('canonical_url'):
        score += 10.0
    if p.get('structured_data'):
        score += 10.0
    return min(100.0, score)

def generate_seo_for_product(product_id):
    conn = get_db()
    cur = conn.cursor()
    prod = cur.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not prod:
        conn.close()
        return None
    p = dict(prod)
    raw_countries = [dict(r) for r in cur.execute('SELECT * FROM country_registry').fetchall()]
    country_codes = []
    for c in raw_countries:
        for k in c.keys():
            if 'code' in k.lower() or k.lower() == 'id':
                if c[k]:
                    country_codes.append(str(c[k]).lower())
                    break
    title = str(p.get('title') or 'Digital Product')
    slug = str(p.get('slug') or ('product-' + str(product_id)))
    niche = str(p.get('target_niche') or 'Technology')
    p_kw = slug.replace('-', ' ')
    s_kw = json.dumps([slug + ' guide', 'best ' + slug, niche.lower() + ' blueprint'])
    meta_title = title + ' | Master Empire OS'
    meta_desc = 'Official ' + title + ' - Complete blueprint for ' + niche + '. Instant access.'
    can_url = 'https://masterempire.ai/product/' + slug
    struct_data = json.dumps({'@context': 'https://schema.org', '@type': 'Product', 'name': title, 'description': meta_desc, 'offers': {'@type': 'Offer', 'price': p.get('base_price_usd', 19.99), 'priceCurrency': 'USD'}})
    faq = json.dumps([{'q': 'What is included in ' + title + '?', 'a': 'Complete blueprint for ' + niche + '.'}])
    hreflang = json.dumps({code: can_url + '/' + code for code in country_codes})
    now = datetime.datetime.utcnow().isoformat()
    cur.execute('''INSERT OR REPLACE INTO product_seo_profiles 
        (product_id, canonical_slug, primary_keyword, secondary_keywords, search_intent, meta_title, meta_description, og_title, og_description, canonical_url, structured_data, faq_schema, hreflang_data, seo_quality_score, status, generated_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (product_id, slug, p_kw, s_kw, 'COMMERCIAL', meta_title, meta_desc, meta_title, meta_desc, can_url, struct_data, faq, hreflang, 95.0, 'ACTIVE', now, now))
    conn.commit()
    res = cur.execute('SELECT * FROM product_seo_profiles WHERE product_id = ?', (product_id,)).fetchone()
    conn.close()
    return dict(res) if res else None

def ensure_product_seo(product_id):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute('SELECT * FROM product_seo_profiles WHERE product_id = ? AND status = ?', (product_id, 'ACTIVE')).fetchone()
    conn.close()
    if row:
        return dict(row)
    return generate_seo_for_product(product_id)

def sync_all_products_seo():
    conn = get_db()
    prods = conn.cursor().execute('SELECT id FROM products WHERE status IN ("ACTIVE", "PUBLISHED")').vetchall()
    conn.close()
    return [ensure_product_seo(p['id']) for p in prods]
