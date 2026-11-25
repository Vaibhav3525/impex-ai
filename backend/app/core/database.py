from sqlalchemy import create_engine, inspect, Table, Column, String, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}

database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(
    database_url,
    connect_args=connect_args,
    echo=settings.DEBUG,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
maintenance = Table("maintenance_state", Base.metadata, Column("name", String(100), primary_key=True))

def init_db():
    from app.models.automation import AutomationPolicy, AutomationState, AutomationRun
    from app.models.evidence import ReviewedEvidence
    from app.models.dispatch_lock import DispatchLock
    Base.metadata.create_all(bind=engine)
    # Additive migration shared by SQLite and PostgreSQL; migration errors are fatal.
    additions = {
        "leads": {"payment_risk_score": "FLOAT DEFAULT 0.0", "risk_level": "VARCHAR(20) DEFAULT 'LOW'"},
        "outreach_emails": {"scheduled_for": "TIMESTAMP"},
        "product_profiles": {"price_unit": "VARCHAR(20)"},
        "deals": {"payment_evidence_reference": "TEXT", "payment_verified_by": "VARCHAR(100)", "payment_verified_at": "TIMESTAMP"},
    }
    with engine.begin() as conn:
        inspector = inspect(conn)
        for table, columns in additions.items():
            if not inspector.has_table(table):
                continue
            present = {c["name"] for c in inspector.get_columns(table)}
            for column, sql_type in columns.items():
                if column not in present:
                    conn.exec_driver_sql(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {sql_type}')

    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO dispatch_lock (id, version) VALUES (1, 0) ON CONFLICT (id) DO NOTHING")
        conn.exec_driver_sql("INSERT INTO automation_state (id, enabled) VALUES (1, false) ON CONFLICT (id) DO NOTHING")
        if not conn.exec_driver_sql("SELECT name FROM maintenance_state WHERE name='security_revision_3'").first():
            conn.execute(text("""UPDATE leads SET verification_status='Rejected', buyer_score=0,
                risk_level='CRITICAL', risk_flags='[\"FLAG_SYNTHETIC_RECORD\"]',
                outreach_status='Suppressed', pipeline_stage='Lost / Rejected'
                WHERE company_name LIKE :synthetic_name"""), {"synthetic_name": "% Import Hub % #%"})
            conn.exec_driver_sql("UPDATE leads SET pipeline_stage='Verification Pending' WHERE verification_status='Unverified' AND pipeline_stage NOT IN ('Discovered','Lost / Rejected')")
            conn.exec_driver_sql("INSERT INTO maintenance_state (name) VALUES ('security_revision_3')")
        if conn.exec_driver_sql("SELECT name FROM maintenance_state WHERE name='security_revision_2'").first():
            return

        # Preserve legacy records, but remove unsupported trust and delivery claims.
        conn.exec_driver_sql(
            """UPDATE leads SET verification_status='Unverified', buyer_score=0,
               risk_level=CASE WHEN risk_level='CRITICAL' THEN risk_level ELSE 'MEDIUM' END,
               risk_flags='[\"FLAG_DOCUMENTARY_REVIEW_REQUIRED\"]'
               WHERE verification_status IN ('Verified', 'Partially Verified')
               AND NOT EXISTS (SELECT 1 FROM reviewed_evidence e WHERE e.lead_id=leads.lead_id)"""
        )
        conn.exec_driver_sql("UPDATE product_profiles SET export_readiness=false WHERE export_readiness=true")
        conn.exec_driver_sql(
            """UPDATE outreach_emails SET status='Delivery Unknown',
               error_message='Legacy send status was not provider-confirmed.' WHERE status='Sent'"""
        )
        conn.exec_driver_sql("UPDATE outreach_emails SET status='Rejected', rejection_reason='Legacy draft requires fresh evidence and product review.' WHERE status IN ('Queued','Approved')")
        conn.exec_driver_sql("UPDATE deals SET stage='Payment Verification', payment_risk_status='Pending Review' WHERE stage IN ('Order Confirmed','Completed') AND payment_evidence_reference IS NULL")
        conn.exec_driver_sql("INSERT INTO maintenance_state (name) VALUES ('security_revision_2')")
        conn.exec_driver_sql("UPDATE leads SET pipeline_stage='Verification Pending' WHERE verification_status='Unverified' AND pipeline_stage NOT IN ('Discovered','Lost / Rejected')")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
