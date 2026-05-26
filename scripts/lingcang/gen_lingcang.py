#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.lingcang.core.builder import generate_lingcang
from scripts.lingcang.core.paths import OUTPUT_DICT, REPORT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="生成灵仓 A/B 互斥前缀码实验字典")
    parser.add_argument("--only-first-full-code", action=argparse.BooleanOptionalAction, default=False, help="每字仅使用源表第一个编码")
    args = parser.parse_args()

    entries = generate_lingcang(only_first_full_code=args.only_first_full_code)
    print(f"完成：条目={len(entries)} 输出={OUTPUT_DICT} 报告={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
