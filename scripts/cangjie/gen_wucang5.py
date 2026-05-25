#!/usr/bin/env python3
"""
Wucang5 生产构建脚本 (五码方案·纯单字流)

流程：
  1. 生成二简（常用字集空槽，高频 GB2312 原住民保护）
  2. 生成三简（常用字集空槽，高频 GB2312 原住民保护，排除 S2 字）
  3. 可选生成四简（默认关闭，可显式启用 GB2312 五码字截断到四码）
  4. 调用 cangjie_builder 生成最终字典（位置降权排序）
"""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from core.cangjie_builder import DEFAULT_FULLCODE_YIELD_MIN_SCORE, generate_dict, REPO_ROOT, get_weighted_frequencies
from core.gen_shortcut_2 import generate_shortcut_2
from core.gen_shortcut_3 import generate_shortcut_3
from core.gen_shortcut_4 import DEFAULT_LEVEL2_MIN_SCORE, generate_shortcut_4

def main():
    parser = argparse.ArgumentParser(description="Wucang5 生产构建脚本 (五码方案·纯单字流)")
    parser.add_argument("--exclude-extended", action="store_true", default=False,
                        help="过滤 Rime 默认 charset_filter 会隐藏的增广字集")
    parser.add_argument("--s2-prefix", action=argparse.BooleanOptionalAction, default=True, help="二简：提取规则取前两码（而非首尾码）")
    parser.add_argument("--s2-count", type=int, default=300, help="二简：输出数量限制")
    parser.add_argument("--s2-coverage", type=float, default=0, help="二简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--s3-prefix", action=argparse.BooleanOptionalAction, default=True, help="三简：提取规则取前三码（而非前两码+末码）")
    parser.add_argument("--s3-count", type=int, default=800, help="三简：固定输出数量")
    parser.add_argument("--s3-coverage", type=float, default=0, help="三简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--protect-native", action=argparse.BooleanOptionalAction, default=True, help="保护高频 GB2312 原生二三码位")
    parser.add_argument("--protect-native-min-score", type=float, default=100000, help="综合字频门槛：原生二三码字达到该值才受保护，长码字达到该值才可入选简码")
    parser.add_argument("--fullcode-yield-min-score", type=float, default=DEFAULT_FULLCODE_YIELD_MIN_SCORE, help="全码简码让位：可顶位字的最低综合字频")
    parser.add_argument("--suffix-z", action=argparse.BooleanOptionalAction, default=True, help="是否为无首选简码的第二候选生成 z 后缀直达码（默认开启）")
    parser.add_argument("--s4", action=argparse.BooleanOptionalAction, default=False, help="四简：是否生成 GB2312 五码字四简（默认关闭，可用 --s4 开启）")
    parser.add_argument("--s4-mode", choices=["safe", "balanced", "aggressive"], default="balanced",
                        help="四简模式：safe=不压原生四码；balanced=高频优势足够才压；aggressive=GB 五码全量截断")
    parser.add_argument("--s4-count", type=int, default=1000, help="四简：固定输出数量；0 表示不限制")
    parser.add_argument("--s4-level2-min-score", type=float, default=DEFAULT_LEVEL2_MIN_SCORE,
                        help="四简：GB2312 二级字最低综合字频；0 表示不过滤二级字")
    parser.add_argument("--only-first-full-code", action=argparse.BooleanOptionalAction, default=False, help="仅取第一个全码（用于去重）")
    args = parser.parse_args()

    # 0. 预加载加权字频（统一语料库得分）
    char_scores = get_weighted_frequencies()

    # 一简是单独校准的原型文件，生产构建只消费，不自动重算。
    # 按依赖顺序生成简码：S2 → S3 → S4
    print("=" * 50)
    print("正在生成二简原型...")
    generate_shortcut_2(
        prefix=args.s2_prefix,
        count=args.s2_count,
        auto_coverage=args.s2_coverage,
        char_scores=char_scores,
        protect_native=args.protect_native,
        protect_native_min_score=args.protect_native_min_score
    )

    print("正在生成三简原型...")
    generate_shortcut_3(
        prefix=args.s3_prefix,
        count=args.s3_count,
        auto_coverage=args.s3_coverage,
        char_scores=char_scores,
        protect_native=args.protect_native,
        protect_native_min_score=args.protect_native_min_score
    )

    shortcut_paths = {
        1: REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt",
        2: REPO_ROOT / "scripts/cangjie/prototypes/two_code.txt",
        3: REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt",
        'z': REPO_ROOT / "scripts/cangjie/prototypes/z_code.txt",
    }
    s4_count_text = "不限制" if args.s4_count == 0 else str(args.s4_count)
    s4_level2_text = "不过滤" if args.s4_level2_min_score == 0 else str(args.s4_level2_min_score)
    if args.s4:
        print(f"正在生成四简原型... (模式: {args.s4_mode} 数量限制: {s4_count_text} 二级字门槛: {s4_level2_text})")
        generate_shortcut_4(
            mode=args.s4_mode,
            count=args.s4_count,
            level2_min_score=args.s4_level2_min_score,
            char_scores=char_scores,
        )
        shortcut_paths[4] = REPO_ROOT / "scripts/cangjie/prototypes/four_code.txt"
    else:
        print(f"四简未启用: 跳过生成（可用 --s4 开启；当前预设: 模式 {args.s4_mode} 数量限制 {s4_count_text} 二级字门槛 {s4_level2_text})")
        # 如果不使用四简，确保旧的原型文件不会被包含（如果它还存在的话）
        p4 = REPO_ROOT / "scripts/cangjie/prototypes/four_code.txt"
        if p4.exists():
            p4.unlink()  # 删除旧的四简原型文件，防止误入字典
            print(f"已删除旧四简原型文件: {p4}")
        else:
            print("四简原型文件不存在，无需清理")

    print("=" * 50)
    print("正在构建最终字典...")
    generate_dict(
        output_path=REPO_ROOT / "schemas/cangjie/wucang5/wucang5.dict.yaml",
        shortcut_paths=shortcut_paths,
        source_dict=REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml",
        char_freqs=char_scores,
        max_code_length=5,
        exclude_extended=args.exclude_extended,
        only_first_full_code=args.only_first_full_code,
        fullcode_yield_min_score=args.fullcode_yield_min_score,
        suffix_z=args.suffix_z,
    )

if __name__ == "__main__":
    main()
