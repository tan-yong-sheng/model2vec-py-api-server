import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

collect_ignore = [
    "smoke_auth_test.py",
    "smoke_test.py",
    "smoke_validate_cache_test.py",
]
