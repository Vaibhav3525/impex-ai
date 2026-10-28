from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)
    if is_sqlite:
        with engine.connect() as conn:
            try:
                cursor = conn.exec_driver_sql("PRAGMA table_info(leads)")
                cols = {row[1] for row in cursor.fetchall()}
                if "id" in cols:
                    if "payment_risk_score" not in cols:
                        conn.exec_driver_sql("ALTER TABLE leads ADD COLUMN payment_risk_score FLOAT DEFAULT 0.0")
                    if "risk_level" not in cols:
                        conn.exec_driver_sql("ALTER TABLE leads ADD COLUMN risk_level VARCHAR(20) DEFAULT 'LOW'")
                    conn.commit()
            except Exception:
                pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
