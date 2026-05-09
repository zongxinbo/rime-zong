from __future__ import annotations

from pathlib import Path


CORE_DIR = Path(__file__).resolve().parent
SHUANGPIN_DIR = CORE_DIR.parent
SCRIPTS_DIR = SHUANGPIN_DIR.parent
REPO_ROOT = SCRIPTS_DIR.parent

PROTOTYPES_DIR = SHUANGPIN_DIR / "prototypes"
SCHEMAS_DIR = REPO_ROOT / "schemas"
SHUANGPIN_SCHEMAS_DIR = SCHEMAS_DIR / "shuangpin"
FREQUENCY_DIR = SCHEMAS_DIR / "common" / "frequency"

CHARS_SOURCE = PROTOTYPES_DIR / "chars.txt"
CHARS_HEADER_TEMPLATE = PROTOTYPES_DIR / "chars.dict.yaml"
PINYIN_SIMP_DICT = SCHEMAS_DIR / "pinyin_simp" / "pinyin_simp.dict.yaml"
PINYIN_ICE_BASE_DICT = SCHEMAS_DIR / "pinyin_ice" / "pinyin_ice.base.dict.yaml"
CANGJIE5_DICT = SCHEMAS_DIR / "cangjie" / "cangjie5" / "cangjie5.dict.yaml"

CHAR_FREQUENCY_SOURCES = [
    (3.0, FREQUENCY_DIR / "char" / "sc" / "dialogue_char_freq.txt"),
    (3.0, FREQUENCY_DIR / "char" / "sc" / "subtlex_char_freq.txt"),
    (2.0, FREQUENCY_DIR / "char" / "sc" / "zhihu_char_freq.txt"),
    (2.0, FREQUENCY_DIR / "char" / "sc" / "blcu_char_freq.txt"),
    (1.0, FREQUENCY_DIR / "char" / "sc" / "multi_domain_char_freq.txt"),
]

WORD_FREQUENCY_SOURCES = [
    (3.0, FREQUENCY_DIR / "word" / "sc" / "dialogue_word_freq.txt"),
    (3.0, FREQUENCY_DIR / "word" / "sc" / "subtlex_word_freq.txt"),
    (1.0, FREQUENCY_DIR / "word" / "sc" / "multi_domain_word_freq.txt"),
]
