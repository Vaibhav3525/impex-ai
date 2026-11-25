"""Start the isolated local app and create unique installation credentials."""
import os
import secrets
import sys
from pathlib import Path
from dotenv import dotenv_values, set_key, load_dotenv

root = Path(__file__).resolve().parents[2]
os.chdir(root)
env = root / ".env"
values = dotenv_values(env)
if values.get("ADMIN_PASSWORD") in {None, "", "local-preview-2026-safe"}:
    set_key(str(env), "ADMIN_PASSWORD", secrets.token_urlsafe(24))
if not values.get("SECRET_KEY") or values["SECRET_KEY"].startswith("local-preview-"):
    set_key(str(env), "SECRET_KEY", secrets.token_urlsafe(48))
load_dotenv(env, override=True)
sys.path.insert(0, str(root / "backend"))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
