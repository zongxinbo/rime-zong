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
    FIXED_PREFIX_CODE_PATH,
    SICANG5_DICT_PATH,
    THREE_CODE_PATH,
    TWO_CODE_PATH,
    ROOT_CODE_PATH,
    generate_dict,
    get_weighted_frequencies,
    SUFFIX_CODE_SICANG5_PATH,
)
from core.gen_shortcut_2 import generate_shortcut_2
from core.gen_shortcut_3 import generate_shortcut_3
from core.dedup import parse_prefix_levels, parse_rank_suffixes
from core.weight_profiles import get_weight_profile

def main():
    parser = argparse.ArgumentParser(description="Sicang5 生产构建脚本 (四码方案·纯单字流)")
    parser.add_argument("--exclude-extended", action="store_true", default=False,
                        help="过滤 Rime 默认 charset_filter 会隐藏的增广字集")
    parser.add_argument("--s2-prefix", action=argparse.BooleanOptionalAction, default=True, help="二简：提取规则取前两码（而非首尾码）")
    parser.add_argument("--s2-count", type=int, default=300, help="二简：输出数量限制")
    parser.add_argument("--s2-coverage", type=float, default=0, help="二简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--s3-prefix", action=argparse.BooleanOptionalAction, default=True, help="三简：提取规则取前三码（而非前两码+末码）")
    parser.add_argument("--s3-count", type=int, default=1300, help="三简：固定输出数量")
    parser.add_argument("--s3-coverage", type=float, default=0, help="三简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--protect-native", action=argparse.BooleanOptionalAction, default=True, help="保护指定字集内的高频原生二三码位")
    parser.add_argument("--protect-native-charset", choices=("all", "frequency", "gbk", "gb2312"), default="gbk",
                        help="原生二三码位保护字集：all=不限，frequency=仅综合字频中出现的字，gbk=常见繁简字，gb2312=简体常用字")
    parser.add_argument("--protect-native-min-score", type=float, default=3000, help="综合字频门槛：原生二三码字达到该值才受保护")
    parser.add_argument("--shortcut-candidate-min-score", type=float, default=3000, help="综合字频门槛：长码字达到该值才可入选二三简")
    parser.add_argument("--fullcode-yield", action=argparse.BooleanOptionalAction, default=False,
                        help="是否启用出简让全：已有普通简码的字在全码候选中让位给无简码常用字（默认关闭）")
    parser.add_argument("--fullcode-yield-min-score", type=float, default=1000, help="全码简码让位：可顶位字的最低综合字频")
    parser.add_argument("--fixed-prefix", action=argparse.BooleanOptionalAction, default=False,
                        help="是否加载 fixed_prefix_code.txt 中的 z?/x? 固定前缀码（默认关闭）")
    parser.add_argument("--suffix-z", action=argparse.BooleanOptionalAction, default=True, help="是否为无首选简码的短码候选生成 z/x 后缀直达码（默认开启）")
    parser.add_argument("--suffix-z-charset", choices=("all", "frequency", "gbk", "gb2312"), default="frequency",
                        help="z/x 后缀候选字集：all=不限，frequency=仅综合字频中出现的字，gbk=常见繁简字，gb2312=简体常用字")
    parser.add_argument("--suffix-z-min-score", type=float, default=1,
                        help="z/x 后缀候选最低综合字频；默认 1")
    parser.add_argument("--suffix-z-ranks", default="2:z,3:x",
                        help="z/x 后缀候选位规则，格式如 2:z,3:x；Sicang5 默认第 2 候选补 z、第 3 候选补 x")
    parser.add_argument("--suffix-z-max-source-length", type=int, default=3,
                        help="z/x 后缀只处理不超过该长度的源码；Sicang5 默认 3，即不处理四码全码")
    parser.add_argument("--suffix-z-occupied-policy", choices=("strict", "ignore-nonfrequency-or-shortcut"),
                        default="ignore-nonfrequency-or-shortcut",
                        help="z/x 后缀目标码占用策略：strict=任意占用即跳过；ignore-nonfrequency-or-shortcut=忽略字集外或已有普通简码的占用")
    parser.add_argument("--dedup-prefix", action=argparse.BooleanOptionalAction, default=True,
                        help="是否自动生成 z/x 前缀短码和四码前缀选重码（默认开启）")
    parser.add_argument("--dedup-prefix-charset", choices=("all", "frequency", "gbk", "gb2312"), default="frequency",
                        help="z/x 前缀候选字集：all=不限，frequency=仅综合字频中出现的字，gbk=常见繁简字，gb2312=简体常用字")
    parser.add_argument("--dedup-prefix-min-score", type=float, default=1,
                        help="z/x 前缀候选最低综合字频；默认 1")
    parser.add_argument("--dedup-prefix-short", action=argparse.BooleanOptionalAction, default=True,
                        help="是否生成 z?/x?、z??/x?? 高频前缀短码（默认开启）")
    parser.add_argument("--dedup-prefix-full", action=argparse.BooleanOptionalAction, default=True,
                        help="是否为四码全码第 2/3 候选生成 z前三/x前三 前缀选重码（默认开启）")
    parser.add_argument("--dedup-prefix-short-levels", default="2,3",
                        help="z/x 高频前缀短码层级，格式如 2,3；2=二键 z?/x?，3=三键 z??/x??")
    parser.add_argument("--dedup-prefix-full-source-length", type=int, default=4,
                        help="z/x 四码前缀选重只处理该源码长度；Sicang5 默认 4")
    parser.add_argument("--dedup-prefix-deep-rank-multiplier", type=float, default=1.5,
                        help="第 3 候选及以后进入前缀短码层时的痛点倍率；默认 1.5")
    parser.add_argument("--dedup-prefix-source-max-code-length", type=int, default=4,
                        help="z/x 前缀生成使用的投影基线码长；默认 4，保证 Sicang5/Wucang5 前缀码一致")
    parser.add_argument("--dedup-prefix-level2-weights", choices=["sc", "sc_daily", "sc_balanced"], default="sc",
                        help="z?/x? 二码前缀权重；默认 sc，对标普通一码")
    parser.add_argument("--dedup-prefix-level3-weights", choices=["sc", "sc_daily", "sc_balanced"], default="sc_daily",
                        help="z??/x?? 三码前缀权重；默认 sc_daily，对标普通二码")
    parser.add_argument("--dedup-prefix-full-weights", choices=["sc", "sc_daily", "sc_balanced"], default="sc_daily",
                        help="z???/x??? 四码前缀权重；默认 sc_daily，对标普通三码")
    parser.add_argument("--suffix-structure", action=argparse.BooleanOptionalAction, default=False, help="是否使用 IDS 结构后缀消重（默认 zxwa 键，默认关闭；默认仅使用 z/x 后缀）")
    parser.add_argument("--suffix-structure-charset", choices=("all", "gbk", "gb2312"), default="gbk",
                        help="结构后缀候选字集：all=不限，gbk=兼顾繁简常用，gb2312=极致简体优化")
    parser.add_argument("--suffix-structure-occupied-policy", choices=("skip-any", "protect-min-score"), default="protect-min-score",
                        help="结构后缀目标码位保护：skip-any=已占用即放弃，protect-min-score=只保护简码和高频既有码位")
    parser.add_argument("--suffix-structure-protect-min-score", type=float, default=100000,
                        help="结构后缀 protect-min-score 模式下，被占用码位首选字达到该综合字频则受保护")
    parser.add_argument("--suffix-structure-keymap", default="zxwa",
                        help="结构类别后缀键，按 左右/上下/包围/独体 顺序给 4 个小写字母；默认 zxwa")
    parser.add_argument("--only-first-full-code", action=argparse.BooleanOptionalAction, default=False, help="仅取第一个全码（用于去重）")
    parser.add_argument("--weights", choices=["sc", "sc_daily", "sc_balanced"], default="sc_daily",
                        help="字频权重模式：sc=现代简体，sc_daily=简繁日常通用，sc_balanced=简繁均衡")
    args = parser.parse_args()
    suffix_z_rank_suffixes = parse_rank_suffixes(args.suffix_z_ranks)
    dedup_prefix_short_levels = parse_prefix_levels(args.dedup_prefix_short_levels)

    # 0. 预加载加权字频
    weights = get_weight_profile(args.weights)
    char_scores = get_weighted_frequencies(weights)
    prefix_level2_scores = get_weighted_frequencies(get_weight_profile(args.dedup_prefix_level2_weights))
    prefix_level3_scores = get_weighted_frequencies(get_weight_profile(args.dedup_prefix_level3_weights))
    prefix_full_scores = get_weighted_frequencies(get_weight_profile(args.dedup_prefix_full_weights))

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
        protect_native_charset=args.protect_native_charset,
        protect_native_min_score=args.protect_native_min_score,
        shortcut_candidate_min_score=args.shortcut_candidate_min_score,
        weights=args.weights,
    )

    print("正在生成三简原型...")
    generate_shortcut_3(
        prefix=args.s3_prefix,
        count=args.s3_count,
        auto_coverage=args.s3_coverage,
        char_scores=char_scores,
        protect_native=args.protect_native,
        protect_native_charset=args.protect_native_charset,
        protect_native_min_score=args.protect_native_min_score,
        shortcut_candidate_min_score=args.shortcut_candidate_min_score,
        weights=args.weights,
    )

    print("=" * 50)
    print("正在构建最终字典...")
    generate_dict(
        output_path=SICANG5_DICT_PATH,
        shortcut_paths={
            1: ONE_CODE_PATH,
            "fixed_prefix": FIXED_PREFIX_CODE_PATH if args.fixed_prefix else None,
            2: TWO_CODE_PATH,
            3: THREE_CODE_PATH,
            "root": ROOT_CODE_PATH,
        },
        source_dict=CANGJIE5_DICT_PATH,
        char_freqs=char_scores,
        max_code_length=4,
        exclude_extended=args.exclude_extended,
        only_first_full_code=args.only_first_full_code,
        fullcode_yield=args.fullcode_yield,
        fullcode_yield_min_score=args.fullcode_yield_min_score,
        suffix_z=args.suffix_z,
        suffix_z_charset=args.suffix_z_charset,
        suffix_z_min_score=args.suffix_z_min_score,
        suffix_z_rank_suffixes=suffix_z_rank_suffixes,
        suffix_z_max_source_length=args.suffix_z_max_source_length,
        suffix_z_occupied_policy=args.suffix_z_occupied_policy,
        suffix_code_path=SUFFIX_CODE_SICANG5_PATH,
        dedup_prefix=args.dedup_prefix,
        dedup_prefix_charset=args.dedup_prefix_charset,
        dedup_prefix_min_score=args.dedup_prefix_min_score,
        dedup_prefix_short=args.dedup_prefix_short,
        dedup_prefix_full=args.dedup_prefix_full,
        dedup_prefix_short_levels=dedup_prefix_short_levels,
        dedup_prefix_full_source_length=args.dedup_prefix_full_source_length,
        dedup_prefix_deep_rank_multiplier=args.dedup_prefix_deep_rank_multiplier,
        dedup_prefix_source_max_code_length=args.dedup_prefix_source_max_code_length,
        dedup_prefix_scheme="sicang5",
        dedup_prefix_scheme_short_levels=(),
        dedup_prefix_scheme_full_source_length=4,
        dedup_prefix_short_level_char_freqs={
            2: prefix_level2_scores,
            3: prefix_level3_scores,
        },
        dedup_prefix_full_char_freqs=prefix_full_scores,
        suffix_structure=args.suffix_structure,
        suffix_structure_charset=args.suffix_structure_charset,
        suffix_structure_occupied_policy=args.suffix_structure_occupied_policy,
        suffix_structure_protect_min_score=args.suffix_structure_protect_min_score,
        suffix_structure_keymap=args.suffix_structure_keymap,
        z_special=True,
        z_special_code_length=4,
        weights=args.weights,
    )

if __name__ == "__main__":
    main()
