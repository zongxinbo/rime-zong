#!/usr/bin/env python3
"""仓颉构建兼容入口。

具体职责已拆分到同目录模块：
- `dict_builder.py`：生产字典构建、全码让位、后缀消重
- `legacy_generator.py`：旧投影生成器 CLI
- `charset.py`：汉字/GB2312/GBK 判定
- `frequency.py`：频率文件读取和加权频率
- `io.py`：仓颉码表读取和路径显示
- `code_utils.py`：投影取码和候选排序工具
- `ids.py`：IDS 结构信息读取

保留本文件是为了兼容现有脚本的 `from core.cangjie_builder import ...`。
"""

from __future__ import annotations

from .charset import (
    HAN_RANGES,
    gb2312_level,
    is_common_han_char,
    is_extended_cjk,
    is_gb2312,
    is_gbk,
    is_han_char,
    is_han_text,
    suffix_structure_charset_allows,
)
from .code_utils import (
    build_fullcode_yield_order,
    build_shortcut_leader_chars,
    project_code,
)
from .dict_builder import (
    build_base_entries,
    build_fullcode_entries,
    build_structure_suffix_entries,
    build_z_suffix_entries,
    collect_char_full_codes,
    generate_dict,
    load_shortcut_entries,
    unique_seen_entries,
    write_final_dict,
)
from .frequency import (
    FREQ_PATHS,
    get_weighted_frequencies,
    parse_frequency_file,
)
from .ids import load_ids_structure_map
from .io import display_path, normalize_prefixes, parse_cangjie_dict
from .legacy_generator import build_output, run_generator
from .models import Entry, FrequencyEntry, OutputEntry
from .paths import (
    SC_FREQ_WEIGHTS,
    SC_BALANCED_FREQ_WEIGHTS,
    BLCU_CHAR_FREQ_PATH,
    CANGJIE5_DICT_PATH,
    CANGJIE_DIR,
    CANGJIE_SCHEMAS_DIR,
    COMMON_CHAR_FREQ_DIR,
    COMMON_DIR,
    COMMON_SC_FREQ_DIR,
    COMMON_TC_FREQ_DIR,
    DEFAULT_FULLCODE_YIELD_MIN_SCORE,
    DIALOGUE_CHAR_FREQ_PATH,
    ESSAY_ZH_HANS_PATH,
    FOUR_CODE_PATH,
    IDS_PATH,
    ONE_CODE_PATH,
    ONE_CODE_REPORT_PATH,
    PROTOTYPES_DIR,
    REPO_ROOT,
    SANCANG5_DICT_PATH,
    SCHEMAS_DIR,
    SCRIPT_DIR,
    SICANG5_DICT_PATH,
    SUBTLEX_CHAR_FREQ_PATH,
    THREE_CODE_PATH,
    TWO_CODE_PATH,
    WUCANG5_DICT_PATH,
    Z_CODE_PATH,
    ZHIHU_CHAR_FREQ_PATH,
)


__all__ = [
    "DEFAULT_FULLCODE_YIELD_MIN_SCORE",
    "BLCU_CHAR_FREQ_PATH",
    "CANGJIE5_DICT_PATH",
    "CANGJIE_DIR",
    "CANGJIE_SCHEMAS_DIR",
    "COMMON_CHAR_FREQ_DIR",
    "COMMON_DIR",
    "COMMON_SC_FREQ_DIR",
    "COMMON_TC_FREQ_DIR",
    "DIALOGUE_CHAR_FREQ_PATH",
    "ESSAY_ZH_HANS_PATH",
    "Entry",
    "FREQ_PATHS",
    "SC_FREQ_WEIGHTS",
    "SC_BALANCED_FREQ_WEIGHTS",
    "FOUR_CODE_PATH",
    "FrequencyEntry",
    "HAN_RANGES",
    "IDS_PATH",
    "ONE_CODE_PATH",
    "ONE_CODE_REPORT_PATH",
    "OutputEntry",
    "PROTOTYPES_DIR",
    "REPO_ROOT",
    "SANCANG5_DICT_PATH",
    "SCHEMAS_DIR",
    "SCRIPT_DIR",
    "SICANG5_DICT_PATH",
    "SUBTLEX_CHAR_FREQ_PATH",
    "THREE_CODE_PATH",
    "TWO_CODE_PATH",
    "WUCANG5_DICT_PATH",
    "Z_CODE_PATH",
    "ZHIHU_CHAR_FREQ_PATH",
    "build_base_entries",
    "build_fullcode_entries",
    "build_fullcode_yield_order",
    "build_output",
    "build_shortcut_leader_chars",
    "build_structure_suffix_entries",
    "build_z_suffix_entries",
    "collect_char_full_codes",
    "display_path",
    "gb2312_level",
    "generate_dict",
    "get_weighted_frequencies",
    "is_common_han_char",
    "is_extended_cjk",
    "is_gb2312",
    "is_gbk",
    "is_han_char",
    "is_han_text",
    "load_ids_structure_map",
    "load_shortcut_entries",
    "normalize_prefixes",
    "parse_cangjie_dict",
    "parse_frequency_file",
    "project_code",
    "run_generator",
    "suffix_structure_charset_allows",
    "unique_seen_entries",
    "write_final_dict",
]
