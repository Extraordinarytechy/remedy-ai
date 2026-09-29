import os
import sys
from pathlib import Path

# backend/ is the Lambda package root; make `import src...` work from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Tests never touch AWS state.
os.environ.pop("TABLE_NAME", None)
os.environ.pop("SNAPSHOT_BUCKET", None)
