#!/usr/bin/env python3
"""
Sicang5 生产构建脚本 (四码方案·纯单字流)

流程与 Wucang5 一致，但最长码限制为 4 码。
"""


import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from core.cangjie_builder import (
    CANGJIE5_DICT_PATH,
    DEFAULT_FULLCODE_YIELD_MIN_SCORE,
    ONE_CODE_PATH,
    SICANG5_DICT_PATH,
    THREE_CODE_PATH,
    TWO_CODE_PATH,
    Z_CODE_PATH,
    generate_dict,
    get_weighted_frequencies,
    SC_FREQ_WEIGHTS,
    SC_BALANCED_FREQ_WEIGHTS,
)
from core.gen_shortcut_2 import generate_shortcut_2
from core.gen_shortcut_3 import generate_shortcut_3

def main():
    parser = argparse.ArgumentParser(description="Sicang5 生产构建脚本 (四码方案·纯单字流)")
    parser.add_argument("--exclude-extended", action="store_true", default=False,
                        help="过滤 Rime 默认 charset_filter 会隐藏的增广字集")
    parser.add_argument("--s2-prefix", action=argparse.BooleanOptionalAction, default=True, help="二简：提取规则取前两码（而非首尾码）")
    parser.add_argument("--s2-count", type=int, default=300, help="二简：输出数量限制")
    parser.add_argument("--s2-coverage", type=float, default=0, help="二简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--s3-prefix", action=argparse.BooleanOptionalAction, default=True, help="三简：提取规则取前三码（而非前两码+末码）")
    parser.add_argument("--s3-count", type=int, default=800, help="三简：固定输出数量")
    parser.add_argument("--s3-coverage", type=float, default=0, help="三简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--protect-native", action=argparse.BooleanOptionalAction, default=True, help="保护高频 GB2312 原生二三码位")
    parser.add_argument("--protect-native-min-score", type=float, default=5000, help="综合字频门槛：原生二三码字达到该值才受保护，长码字达到该值才可入选简码")
    parser.add_argument("--fullcode-yield-min-score", type=float, default=5000, help="全码简码让位：可顶位字的最低综合字频")
    parser.add_argument("--suffix-z", action=argparse.BooleanOptionalAction, default=True, help="是否为无首选简码的第二候选生成 z 后缀直达码（默认开启）")
    parser.add_argument("--suffix-structure", action=argparse.BooleanOptionalAction, default=False, help="是否使用 IDS 结构后缀消重（默认 zxwa 键，默认关闭；默认仅使用 z 后缀）")
    parser.add_argument("--suffix-structure-charset", choices=("all", "gbk", "gb2312"), default="gbk",
                        help="结构后缀候选字集：all=不限，gbk=兼顾繁简常用，gb2312=极致简体优化")
    parser.add_argument("--suffix-structure-occupied-policy", choices=("skip-any", "protect-min-score"), default="protect-min-score",
                        help="结构后缀目标码位保护：skip-any=已占用即放弃，protect-min-score=只保护简码和高频既有码位")
    parser.add_argument("--suffix-structure-protect-min-score", type=float, default=100000,
                        help="结构后缀 protect-min-score 模式下，被占用码位首选字达到该综合字频则受保护")
    parser.add_argument("--suffix-structure-keymap", default="zxwa",
                        help="结构类别后缀键，按 左右/上下/包围/独体 顺序给 4 个小写字母；默认 zxwa")
    parser.add_argument("--only-first-full-code", action=argparse.BooleanOptionalAction, default=False, help="仅取第一个全码（用于去重）")
    parser.add_argument("--weights", choices=["sc_balanced", "sc"], default="sc_balanced",
                        help="字频权重模式：sc_balanced=简体均衡优先权重 (SC_BALANCED_FREQ_WEIGHTS), sc=简体绝对优先频数权重 (SC_FREQ_WEIGHTS)")
    args = parser.parse_args()

    # 0. 预加载加权字频
    weights = SC_FREQ_WEIGHTS if args.weights == "sc" else SC_BALANCED_FREQ_WEIGHTS
    char_scores = get_weighted_frequencies(weights)

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

    print("=" * 50)
    print("正在构建最终字典...")
    generate_dict(
        output_path=SICANG5_DICT_PATH,
        shortcut_paths={
            1: ONE_CODE_PATH,
            2: TWO_CODE_PATH,
            3: THREE_CODE_PATH,
            'z': Z_CODE_PATH,
        },
        source_dict=CANGJIE5_DICT_PATH,
        char_freqs=char_scores,
        max_code_length=4,
        exclude_extended=args.exclude_extended,
        only_first_full_code=args.only_first_full_code,
        fullcode_yield_min_score=args.fullcode_yield_min_score,
        suffix_z=args.suffix_z,
        suffix_structure=args.suffix_structure,
        suffix_structure_charset=args.suffix_structure_charset,
        suffix_structure_occupied_policy=args.suffix_structure_occupied_policy,
        suffix_structure_protect_min_score=args.suffix_structure_protect_min_score,
        suffix_structure_keymap=args.suffix_structure_keymap,
    )

if __name__ == "__main__":
    main()
