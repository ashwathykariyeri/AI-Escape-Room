# conftest.py - pytest runs this first. We add the v2 folder to Python's search path
# so the tests can write "from engine import ..." no matter where pytest is started.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))