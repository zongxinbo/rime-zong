from __future__ import annotations

from pathlib import Path


CORE_DIR = Path(__file__).resolve().parent
SHUANGPIN_DIR = CORE_DIR.parent
SCRIPTS_DIR = SHUANGPIN_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parent

PROTOTYPES_DIR = SHUANGPIN_DIR / "prototypes"
SCHEMAS_DIR = REPO_ROOT / "schemas"

CHARS_SOURCE = PROTOTYPES_DIR / "chars.txt"
CHARS_HEADER_TEMPLATE = PROTOTYPES_DIR / "chars.dict.yaml"
PINYIN_SIMP_DICT = SCHEMAS_DIR / "pinyin_simp" / "pinyin_simp.dict.yaml"
CANGJIE5_DICT = SCHEMAS_DIR / "cangjie" / "cangjie5" / "cangjie5.dict.yaml"

