"""Launch the CISA KEV desktop GUI."""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kev_analysis.gui.app import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="启动后立即加载课程 KEV JSON")
    arguments = parser.parse_args()
    raise SystemExit(run(arguments.input))
