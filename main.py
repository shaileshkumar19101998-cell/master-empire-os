load_dotenv()
db_url = os.getenv("DATABASE_URL", "sqlite:///./autonomous_local.db")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if "sqlite" in db_url:
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    # Render Postgres SSL connection handling
    connect_args = {}
    if "postgresql" in db_url:
        connect_args = {"sslmode": "require"}
    engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)