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
DATA_DIR = CANGJIE_DIR / "data"
PROTOTYPES_DIR = CANGJIE_DIR / "prototypes"
SC_GLYPH_PREFERRED_CODE_PATH = DATA_DIR / "sc_glyph_preferred_code.txt"
TC_GLYPH_PREFERRED_CODE_PATH = DATA_DIR / "tc_glyph_preferred_code.txt"
ROOT_CODE_PATH = PROTOTYPES_DIR / "root_code.txt"
ONE_CODE_PATH = PROTOTYPES_DIR / "one_code.txt"
ONE_CODE_REPORT_PATH = PROTOTYPES_DIR / "one_code_report.md"
FIXED_PREFIX_CODE_PATH = PROTOTYPES_DIR / "fixed_prefix_code.txt"
TWO_CODE_PATH = PROTOTYPES_DIR / "two_code.txt"
THREE_CODE_PATH = PROTOTYPES_DIR / "three_code.txt"
FOUR_CODE_PATH = PROTOTYPES_DIR / "four_code.txt"
PREFIX_CODE_2_PATH = PROTOTYPES_DIR / "prefix_code_2.txt"
PREFIX_CODE_3_PATH = PROTOTYPES_DIR / "prefix_code_3.txt"
PREFIX_CODE_2_SICANG5_PATH = PROTOTYPES_DIR / "prefix_code_2_sicang5.txt"
PREFIX_CODE_3_SICANG5_PATH = PROTOTYPES_DIR / "prefix_code_3_sicang5.txt"
PREFIX_CODE_4_SICANG5_PATH = PROTOTYPES_DIR / "prefix_code_4_sicang5.txt"
PREFIX_CODE_2_WUCANG5_PATH = PROTOTYPES_DIR / "prefix_code_2_wucang5.txt"
PREFIX_CODE_3_WUCANG5_PATH = PROTOTYPES_DIR / "prefix_code_3_wucang5.txt"
PREFIX_CODE_4_WUCANG5_PATH = PROTOTYPES_DIR / "prefix_code_4_wucang5.txt"
PREFIX_CODE_5_WUCANG5_PATH = PROTOTYPES_DIR / "prefix_code_5_wucang5.txt"
SUFFIX_CODE_SICANG5_PATH = PROTOTYPES_DIR / "suffix_code_sicang5.txt"
SUFFIX_CODE_WUCANG5_PATH = PROTOTYPES_DIR / "suffix_code_wucang5.txt"

IDS_PATH = REPO_ROOT / "scripts" / "ids" / "ids.txt"

DIALOGUE_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "dialogue_char_freq.txt"
SUBTLEX_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "subtlex_char_freq.txt"
ZHIHU_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "zhihu_char_freq.txt"
BLCU_CHAR_FREQ_PATH = COMMON_SC_FREQ_DIR / "blcu_char_freq.txt"
TAIWAN_CHAR_FREQ_PATH = COMMON_TC_FREQ_DIR / "taiwan_char_freq.txt"
GUJI_CHAR_FREQ_PATH = COMMON_TC_FREQ_DIR / "guji_char_freq.txt"
ESSAY_ZH_HANS_PATH = COMMON_DIR / "essay-zh-hans.txt"

FREQ_PATHS = {
    "Dialogue": DIALOGUE_CHAR_FREQ_PATH,
    "Subtlex": SUBTLEX_CHAR_FREQ_PATH,
    "Zhihu": ZHIHU_CHAR_FREQ_PATH,
    "BLCU": BLCU_CHAR_FREQ_PATH,
    "Taiwan": TAIWAN_CHAR_FREQ_PATH,
    "Guji": GUJI_CHAR_FREQ_PATH,
    "Essay": ESSAY_ZH_HANS_PATH,
}
SC_FREQ_WEIGHTS = {
    "Dialogue": 0.207475789,
    "Subtlex": 0.275685250,
    "Zhihu": 0.279235620,
    "BLCU": 0.237603341
}
SC_BALANCED_FREQ_WEIGHTS = {
    "Zhihu": 0.33,
    "BLCU": 0.27,
    "Taiwan": 0.22,
    "Guji": 0.18
}
SC_DAILY_FREQ_WEIGHTS = {
    "Dialogue": 0.03,
    "Zhihu": 0.4235,
    "BLCU": 0.3465,
    "Taiwan": 0.11,
    "Guji": 0.09
}
TC_FREQ_WEIGHTS = {
    "Taiwan": 1.0,
}
