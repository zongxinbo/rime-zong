from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_FULLCODE_YIELD_MIN_SCORE = 1000

SCHEMAS_DIR = REPO_ROOT / "schemas"
CANGJIE_SCHEMAS_DIR = SCHEMAS_DIR / "cangjie"
COMMON_DIR = SCHEMAS_DIR / "common"
COMMON_CHAR_FREQ_DIR = COMMON_DIR / "frequency" / "char"
COMMON_SC_FREQ_DIR = COMMON_CHAR_FREQ_DIR / "sc"
COMMON_TC_FREQ_DIR = COMMON_CHAR_FREQ_DIR / "tc"

CANGJIE5_DICT_PATH = CANGJIE_SCHEMAS_DIR / "cangjie5" / "cangjie5.dict.yaml"
SANCANG5_DICT_PATH = CANGJIE_SCHEMAS_DIR / "sancang5" / "sancang5.dict.yaml"
SICANG5_DICT_PATH = CANGJIE_SCHEMAS_DIR / "sicang5" / "sicang5.dict.yaml"
WUCANG5_DICT_PATH = CANGJIE_SCHEMAS_DIR / "wucang5" / "wucang5.dict.yaml"

CANGJIE_DIR = REPO_ROOT / "scripts" / "cangjie"
PROTOTYPES_DIR = CANGJIE_DIR / "prototypes"
Z_CODE_PATH = PROTOTYPES_DIR / "z_code.txt"
ONE_CODE_PATH = PROTOTYPES_DIR / "one_code.txt"
ONE_CODE_REPORT_PATH = PROTOTYPES_DIR / "one_code_report.md"
TWO_CODE_PATH = PROTOTYPES_DIR / "two_code.txt"
THREE_CODE_PATH = PROTOTYPES_DIR / "three_code.txt"
FOUR_CODE_PATH = PROTOTYPES_DIR / "four_code.txt"

IDS_PATH = REPO_ROOT / "scripts" / "ids" / "ids.txt"

DIALOGUE_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "dialogue_char_freq.txt"
SUBTLEX_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "subtlex_char_freq.txt"
ZHIHU_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "zhihu_char_freq.txt"
BLCU_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "blcu_char_freq.txt"
ESSAY_ZH_HANS_PATH = COMMON_DIR / "essay-zh-hans.txt"

FREQ_PATHS = {
    "Dialogue": DIALOGUE_CHAR_FREQ_PATH,
    "Subtlex": SUBTLEX_CHAR_FREQ_PATH,
    "Zhihu": ZHIHU_CHAR_FREQ_PATH,
    "BLCU": BLCU_CHAR_FREQ_PATH,
    "Essay": ESSAY_ZH_HANS_PATH,
}
FREQ_WEIGHTS = {"Dialogue": 6, "Subtlex": 5, "Zhihu": 4, "BLCU": 2, "Essay": 1}
