#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from core.paths import (
    COMMON_DIR,
    ESSAY_ZH_HANS_PATH,
    ONE_CODE_PATH,
    ROOT_CODE_PATH,
    SC_GLYPH_PREFERRED_CODE_PATH,
    SICANG5_DICT_PATH,
)
from core.word_dict_builder import build_word_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="生成带固定词库的四码仓颉码表")
    parser.add_argument("--source-dict", type=Path, default=SICANG5_DICT_PATH, help="已生成的 Sicang5 单字码表")
    parser.add_argument(
        "--words-dict",
        type=Path,
        default=COMMON_DIR / "words" / "mixed.words.dict.yaml",
        help="纯 text 列混合词库",
    )
    parser.add_argument("--essay", type=Path, default=ESSAY_ZH_HANS_PATH, help="排序用 essay-zh-hans.txt")
    parser.add_argument("--root-code", type=Path, default=ROOT_CODE_PATH, help="字根构词码原型")
    parser.add_argument("--one-code", type=Path, default=ONE_CODE_PATH, help="一简原型，用于构词时跳过一简码")
    parser.add_argument(
        "--preferred-code",
        type=Path,
        default=SC_GLYPH_PREFERRED_CODE_PATH,
        help="简体字形偏好编码，用于多编码字构词选码",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SICANG5_DICT_PATH.with_name("sicang5_words.dict.yaml"),
        help="输出码表",
    )
    args = parser.parse_args()

    stats = build_word_dict(
        source_dict=args.source_dict,
        words_dict=args.words_dict,
        essay_path=args.essay,
        output_path=args.output,
        name=args.output.name.split(".")[0],
        root_code_path=args.root_code,
        one_code_path=args.one_code,
        preferred_code_path=args.preferred_code,
    )
    print(
        f"完成：词条保留={stats['phrase_kept']}"
        f" 未在 essay-zh-hans={stats['phrase_dropped_not_in_essay']}"
        f" 缺字码={stats['phrase_dropped_missing_code']}"
        f" 重复={stats['phrase_dropped_duplicate']}"
        f" 偏好构词码={stats['preferred_base_codes']}"
        f" 输出={args.output}"
    )


if __name__ == "__main__":
    main()
