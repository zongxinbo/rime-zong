#!/usr/bin/env python3
"""
Sicang5 生产构建脚本 (四码方案·纯单字流)

流程与 Wucang5 一致，但最长码限制为 4 码。
"""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from core.cangjie_builder import generate_dict, REPO_ROOT, get_weighted_frequencies
from core.gen_shortcut_2 import generate_shortcut_2
from core.gen_shortcut_3 import generate_shortcut_3

def main():
    parser = argparse.ArgumentParser(description="Sicang5 生产构建脚本 (四码方案·纯单字流)")
    parser.add_argument("--exclude-extended", action="store_true", default=False,
                        help="过滤增广字集（Ext-B及以上）")
    parser.add_argument("--s2-prefix", action=argparse.BooleanOptionalAction, default=True, help="二简：提取规则取前两码（而非首尾码）")
    parser.add_argument("--s2-count", type=int, default=150, help="二简：输出数量限制")
    parser.add_argument("--s2-coverage", type=float, default=0, help="二简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--s3-prefix", action=argparse.BooleanOptionalAction, default=True, help="三简：提取规则取前三码（而非前两码+末码）")
    parser.add_argument("--s3-count", type=int, default=300, help="三简：固定输出数量")
    parser.add_argument("--s3-coverage", type=float, default=0, help="三简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--protect-native", action=argparse.BooleanOptionalAction, default=True, help="二简保护高频 GB2312 原生二码位，三简保护已有原生三码位")
    parser.add_argument("--s2-protect-native-min-score", type=float, default=100000, help="原生二码字达到该综合字频才受保护")
    parser.add_argument("--only-first-full-code", action=argparse.BooleanOptionalAction, default=False, help="仅取第一个全码（用于去重）")
    args = parser.parse_args()

    # 0. 预加载加权字频
    char_scores = get_weighted_frequencies()

    # 一简是单独校准的原型文件，生产构建只消费，不自动重算。
    # 按依赖顺序生成二简、三简。
    print("=" * 50)
    print("正在生成二简原型...")
    generate_shortcut_2(
        prefix=args.s2_prefix,
        count=args.s2_count,
        auto_coverage=args.s2_coverage,
        char_scores=char_scores,
        protect_native=args.protect_native,
        protect_native_min_score=args.s2_protect_native_min_score
    )

    print("正在生成三简原型...")
    generate_shortcut_3(
        prefix=args.s3_prefix,
        count=args.s3_count,
        auto_coverage=args.s3_coverage,
        char_scores=char_scores,
        protect_native=args.protect_native
    )

    print("=" * 50)
    print("正在构建最终字典...")
    generate_dict(
        output_path=REPO_ROOT / "schemas/cangjie/sicang5/sicang5.dict.yaml",
        shortcut_paths={
            1: REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt",
            2: REPO_ROOT / "scripts/cangjie/prototypes/two_code.txt",
            3: REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt",
            'z': REPO_ROOT / "scripts/cangjie/prototypes/z_code.txt",
        },
        source_dict=REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml",
        char_freqs=char_scores,
        max_code_length=4,
        exclude_extended=args.exclude_extended,
        only_first_full_code=args.only_first_full_code,
    )

if __name__ == "__main__":
    main()
