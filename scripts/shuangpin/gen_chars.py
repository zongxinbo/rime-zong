#!/usr/bin/env python3
from __future__ import annotations

import argparse

from core.builder import build_chars_prototype


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate shuangpin character prototype with Cangjie auxiliary codes.")
    parser.add_argument("--simplified", action="store_true", help="Use simplified frequency weights")
    parser.add_argument("--schema", choices=["zrm", "flypy"], default="zrm", help="Target double pinyin schema")
    args = parser.parse_args()

    entries, dropped, path = build_chars_prototype(args.schema, simplified=args.simplified)
    print(f"Generated {path}")
    print(f"Character entries: {len(entries)}")
    print(f"Dropped characters without usable Cangjie aux code: {len(dropped)}")


if __name__ == "__main__":
    main()

