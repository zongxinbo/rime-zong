#!/usr/bin/env python3
from __future__ import annotations

import argparse

from core.builder import build_scheme


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the zrm shuangpin + Cangjie auxiliary scheme.")
    parser.add_argument("--simplified", action="store_true", help="Use simplified character frequency weights")
    parser.add_argument("--min-word-weight", type=int, default=1, help="Minimum source word weight")
    parser.add_argument("--max-word-length", type=int, default=8, help="Maximum word length")
    args = parser.parse_args()

    build_scheme(
        "zrm",
        simplified=args.simplified,
        min_word_weight=args.min_word_weight,
        max_word_length=args.max_word_length,
    )


if __name__ == "__main__":
    main()

