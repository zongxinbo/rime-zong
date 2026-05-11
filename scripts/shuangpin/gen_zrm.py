#!/usr/bin/env python3
from __future__ import annotations

import argparse

from core.builder import build_scheme


def main() -> None:
    parser = argparse.ArgumentParser(description="生成自然码双拼 + 仓颉辅助码音形方案。")
    parser.add_argument(
        "--simplified",
        dest="simplified",
        action="store_true",
        default=True,
        help="使用简体字频列生成单字主读音和排序权重（默认）。",
    )
    parser.add_argument(
        "--traditional",
        dest="simplified",
        action="store_false",
        help="使用繁体字频列生成单字主读音和排序权重。",
    )
    parser.add_argument(
        "--min-word-weight",
        type=int,
        default=None,
        help="覆盖各词长默认收词阈值；不传则 essay 主词源按二字词 50、三字词 100、四字词 50。",
    )
    parser.add_argument("--max-word-length", type=int, default=4, help="收词的最大词长。")
    args = parser.parse_args()

    build_scheme(
        "zrm",
        simplified=args.simplified,
        min_word_weight=args.min_word_weight,
        max_word_length=args.max_word_length,
    )


if __name__ == "__main__":
    main()
