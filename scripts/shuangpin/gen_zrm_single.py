#!/usr/bin/env python3
from __future__ import annotations

import argparse

from core.builder import build_scheme


def main() -> None:
    parser = argparse.ArgumentParser(description="生成自然码双拼 + 仓颉兜底的纯单字方案。")
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
    args = parser.parse_args()

    build_scheme(
        "zrm_single",
        simplified=args.simplified,
        include_words=False,
        max_code_length=6,
    )


if __name__ == "__main__":
    main()
