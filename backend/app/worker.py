"""Continuous worker: python -m app.worker [--once]."""
import argparse
import logging
import signal
import threading
from app.main import app  # Registers models and validates production configuration.
from app.core.database import SessionLocal
from app.models.automation import AutomationState
from app.services.automation_service import run_cycle, utcnow

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one due cycle, suitable for cron.")
    args = parser.parse_args()
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    logging.basicConfig(level=logging.INFO)
    while not stop.is_set():
        with SessionLocal() as db:
            try:
                state = db.get(AutomationState, 1)
                state.heartbeat_at = utcnow()
                db.commit()
                result = run_cycle(db)
                logging.info("Automation cycle: %s", result.get("status"))
            except Exception:
                db.rollback()
                logging.exception("Automation worker cycle failed")
        if args.once:
            break
        stop.wait(30)

if __name__ == "__main__":
    main()
