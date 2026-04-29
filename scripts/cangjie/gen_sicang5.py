#!/usr/bin/env python3
"""
Sicang5 生产构建脚本 (四码方案)
利用 cangjie_builder 引擎，将简码与单字打包。
"""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from core.cangjie_builder import generate_dict, REPO_ROOT
from core.gen_shortcut_2 import generate_shortcut_2
from core.gen_shortcut_3 import generate_shortcut_3

def main():
    parser = argparse.ArgumentParser(description="Sicang5 生产构建脚本 (四码方案)")
    parser.add_argument("--exclude-extended", action="store_true", default=False, help="过滤增广字集（Ext-B及以上）")
    parser.add_argument("--s2-prefix", action=argparse.BooleanOptionalAction, default=True, help="二简：提取规则取前两码（而非首尾码）")
    parser.add_argument("--s2-count", type=int, default=0, help="二简：输出数量限制")
    parser.add_argument("--s2-coverage", type=float, default=0.90, help="二简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--s3-prefix", action=argparse.BooleanOptionalAction, default=True, help="三简：提取规则取前三码（而非前两码+末码）")
    parser.add_argument("--s3-count", type=int, default=0, help="三简：固定输出数量")
    parser.add_argument("--s3-coverage", type=float, default=0.90, help="三简：按累计字频覆盖率自动决定数量")
    args = parser.parse_args()

    # 动态生成 2、3 简码，保证使用相同的规则（一简和 Z 码为写死的静态文件不重新生成）
    print("正在生成二简原型...")
    generate_shortcut_2(prefix=args.s2_prefix, count=args.s2_count, auto_coverage=args.s2_coverage)
    print("正在生成三简原型...")
    generate_shortcut_3(prefix=args.s3_prefix, count=args.s3_count, auto_coverage=args.s3_coverage)

    generate_dict(
        output_path = REPO_ROOT / "sicang5/sicang5.dict.yaml",
        shortcut_paths = {
            1: REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt",
            2: REPO_ROOT / "scripts/cangjie/prototypes/two_code.txt",
            3: REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt",
            'z': REPO_ROOT / "scripts/cangjie/prototypes/z_code.txt"
        },
        source_dict = REPO_ROOT / "cangjie5/cangjie5.dict.yaml",
        freq_file = REPO_ROOT / "frequency/word/essay-zh-hans.txt",
        vocabulary = "essay-zh-hans",
        max_code_length = 4,
        max_phrase_length = 7,
        min_phrase_weight = 100,
        include_phrases = False,
        exclude_extended=args.exclude_extended
    )

if __name__ == "__main__":
    main()
