import sqlite3

def get_db():
    conn = sqlite3.connect('autonomous_local.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_or_sync_seo(product_id):
    conn = get_db()
    cur = conn.cursor()
    prod = cur.execute('SELECT id, slug, title FROM products WHERE id = ?', (product_id,)).fetchone()
    if not prod:
        conn.close()
        return None
    title = str(prod['title'])
    slug = str(prod['slug'])
    meta_title = title + ' - Official Blueprint'
    meta_desc = 'Autonomous Growth Blueprint for ' + title + '.'
    cur.execute('INSERT OR REPLACE INTO product_seo_profiles (product_id, canonical_slug, primary_keyword, meta_title, meta_description, seo_quality_score, status) VALUES (?, ?, ?, ?, ?, ?, ?)', (prod['id'], slug, slug.replace('-', ' '), meta_title, meta_desc, 9.5, 'ACTIVE'))
    conn.commit()
    conn.close()
    return {'product_id': prod['id'], 'slug': slug, 'seo_quality_score': 9.5}

def sync_all_products_seo():
    conn = get_db()
    prods = conn.cursor().execute('SELECT id FROM products').fetchall()
    conn.close()
    return [generate_or_sync_seo(p['id']) for p in prods]
