from urllib.parse import urlsplit
from datetime import datetime, timezone, timedelta
from app.models.evidence import ReviewedEvidence

EVIDENCE_WEIGHTS = {"identity": 20, "relevance": 20, "imports": 15, "independent": 15, "website": 15, "email": 15}

def usable_source(url: str | None) -> bool:
    try:
        parsed = urlsplit(url or "")
        host = (parsed.hostname or "").lower()
        forbidden = (".invalid", ".localhost", ".test", ".example")
        return parsed.scheme in {"http", "https"} and "." in host and not parsed.username and not host.endswith(forbidden) and not any(host == d or host.endswith("." + d) for d in ("example.com", "example.org", "example.net"))
    except ValueError:
        return False

def current_evidence(db, lead_id):
    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    rows = db.query(ReviewedEvidence).filter(ReviewedEvidence.lead_id == lead_id, ReviewedEvidence.reviewed_at >= cutoff).all()
    return {r.category: r for r in rows if usable_source(r.source_url)}
