from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SOURCE_DICT = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
OUTPUT_DIR = REPO_ROOT / "schemas/lingcang"
OUTPUT_DICT = OUTPUT_DIR / "lingcang.dict.yaml"
REPORT_PATH = REPO_ROOT / "scripts/lingcang/lingcang.report.md"
PROTOTYPE_DIR = REPO_ROOT / "scripts/lingcang/prototypes"
ONE_CODE_PATH = PROTOTYPE_DIR / "one_code.txt"
TWO_CODE_PATH = PROTOTYPE_DIR / "two_code.txt"
