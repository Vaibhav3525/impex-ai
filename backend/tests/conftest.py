import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Isolate all tests to dedicated test database file so production DB remains 100% clean
import tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(prefix="impex-tests-"), "tests.db").replace("\\", "/")
os.environ["ADMIN_PASSWORD"] = "test-operator-password-never-production"
os.environ["SECRET_KEY"] = "test-signing-secret-only-for-isolated-unit-tests"
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "False"
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["OUTREACH_ENABLED"] = "False"

