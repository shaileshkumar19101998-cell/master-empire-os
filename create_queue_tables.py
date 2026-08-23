import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, MetaData, Table
from datetime import datetime

load_dotenv()
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
metadata = MetaData()

# 1. Human-in-the-loop Pending Approvals Table
approvals_table = Table(
    'pending_approvals', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('task_type', String(100), nullable=False),
    Column('title', String(500), nullable=False),
    Column('niche', String(255)),
    Column('proposed_content', Text),
    Column('status', String(50), default='PENDING'), # PENDING, APPROVED, REJECTED
    Column('created_at', DateTime, default=datetime.utcnow)
)

# 2. System Audit & Task Logs Table
logs_table = Table(
    'system_logs', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('module', String(100), nullable=False),
    Column('status', String(50), nullable=False), # SUCCESS, FAILED, RETRY
    Column('message', Text),
    Column('created_at', DateTime, default=datetime.utcnow)
)

def create_tables():
    metadata.create_all(engine)
    print("✅ 'pending_approvals' and 'system_logs' tables created successfully!")

if __name__ == "__main__":
    create_tables()