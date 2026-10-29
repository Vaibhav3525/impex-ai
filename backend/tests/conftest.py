import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Isolate all tests to dedicated test database file so production DB remains 100% clean
os.environ["DATABASE_URL"] = "sqlite:///./test_impex_runner.db"

