#!/usr/bin/env python3
"""
Wucang5 生产构建脚本 (五码方案)
利用 cangjie_builder 引擎，将简码与单字打包。
"""

import argparse
from pathlib import Path
from core.cangjie_builder import generate_dict, REPO_ROOT

def main():
    parser = argparse.ArgumentParser(description="Wucang5 生产构建脚本 (五码方案)")
    parser.add_argument("--exclude-extended", action="store_true", default=False, help="过滤增广字集（Ext-B及以上）")
    args = parser.parse_args()

    generate_dict(
        output_path = REPO_ROOT / "wucang5/wucang5.dict.yaml",
        shortcut_paths = {
            1: REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt",
            2: REPO_ROOT / "scripts/cangjie/prototypes/two_code.txt",
            3: REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt",
            'z': REPO_ROOT / "scripts/cangjie/prototypes/z_code.txt"
        },
        source_dict = REPO_ROOT / "cangjie5/cangjie5.dict.yaml",
        freq_file = REPO_ROOT / "frequency/word/essay-zh-hans.txt",
        max_code_length = 5,
        include_phrases = False,
        exclude_extended=args.exclude_extended
    )

if __name__ == "__main__":
    main()
