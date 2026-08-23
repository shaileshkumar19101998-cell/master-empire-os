import json
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, MetaData, Table

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
metadata = MetaData()

books_table = Table(
    'books', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('title', String(500), nullable=False),
    Column('niche', String(255)),
    Column('tier', String(100)),
    Column('price', String(50)),
    Column('price_val', Integer),
    Column('market_price', String(50)),
    Column('badge', String(255)),
    Column('visits', Integer, default=0),
    Column('orders', Integer, default=0),
    Column('revenue', Integer, default=0),
    Column('content_preview', Text),
    Column('file', String(500)),
    Column('seo_status', String(255)),
    Column('status', String(50), default='ACTIVE')
)

def run_migration():
    metadata.create_all(engine)
    
    with open('data/analytics.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    raw_books = data.get('published_books', [])
    print(f"📦 Local JSON me total {len(raw_books)} books mili.")

    with engine.begin() as conn:
        conn.execute(books_table.delete())
        for b in raw_books:
            conn.execute(books_table.insert().values(
                title=b.get('title'),
                niche=b.get('niche'),
                tier=b.get('tier'),
                price=b.get('price'),
                price_val=b.get('price_val', 0),
                market_price=b.get('market_price'),
                badge=b.get('badge'),
                visits=b.get('visits', 0),
                orders=b.get('orders', 0),
                revenue=b.get('revenue', 0),
                content_preview=b.get('content_preview'),
                file=b.get('file'),
                seo_status=b.get('seo_status'),
                status='ACTIVE'
            ))
        print(f"✅ {len(raw_books)} books successfully PostgreSQL me migrate ho gayi!")

if __name__ == "__main__":
    run_migration()