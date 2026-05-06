#!/usr/bin/env python3
"""
Wucang5 生产构建脚本 (五码方案·纯单字流)

流程：
  1. 生成二简（空槽全占，GB2312 保护）
  2. 生成三简（空槽全占，GB2312 保护，排除 S2 字）
  3. 生成强制四简（GB2312 五码字截断到四码）
  4. 调用 cangjie_builder 生成最终字典（位置降权排序）
"""

import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from core.cangjie_builder import generate_dict, REPO_ROOT, get_weighted_frequencies
from core.gen_shortcut_2 import generate_shortcut_2
from core.gen_shortcut_3 import generate_shortcut_3
from core.gen_shortcut_4 import generate_shortcut_4

def main():
    parser = argparse.ArgumentParser(description="Wucang5 生产构建脚本 (五码方案·纯单字流)")
    parser.add_argument("--exclude-extended", action="store_true", default=False,
                        help="过滤增广字集（Ext-B及以上）")
    parser.add_argument("--gb-only", action="store_true", default=False, help="仅对 GB2312 汉字生成简码并实施保护")
    parser.add_argument("--s2-prefix", action=argparse.BooleanOptionalAction, default=True, help="二简：提取规则取前两码（而非首尾码）")
    parser.add_argument("--s2-count", type=int, default=0, help="二简：输出数量限制")
    parser.add_argument("--s2-coverage", type=float, default=0.90, help="二简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--s3-prefix", action=argparse.BooleanOptionalAction, default=True, help="三简：提取规则取前三码（而非前两码+末码）")
    parser.add_argument("--s3-count", type=int, default=0, help="三简：固定输出数量")
    parser.add_argument("--s3-coverage", type=float, default=0.90, help="三简：按累计字频覆盖率自动决定数量")
    parser.add_argument("--s4", action=argparse.BooleanOptionalAction, default=False, help="四简：是否生成强制四简（截断五码）")
    parser.add_argument("--only-first-full-code", action=argparse.BooleanOptionalAction, default=False, help="仅取第一个全码（用于去重）")
    args = parser.parse_args()

    # 0. 预加载加权字频（统一语料库得分）
    char_scores = get_weighted_frequencies()

    # 按依赖顺序生成简码：S2 → S3 → S4
    print("=" * 50)
    print("正在生成二简原型...")
    generate_shortcut_2(
        gb_only=args.gb_only,
        prefix=args.s2_prefix,
        count=args.s2_count,
        auto_coverage=args.s2_coverage,
        char_scores=char_scores
    )

    print("正在生成三简原型...")
    generate_shortcut_3(
        gb_only=args.gb_only,
        prefix=args.s3_prefix,
        count=args.s3_count,
        auto_coverage=args.s3_coverage,
        char_scores=char_scores
    )

    # 只有显式开启 --s4，或者在 --gb-only 模式下，才生成并包含四简
    shortcut_paths = {
        1: REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt",
        2: REPO_ROOT / "scripts/cangjie/prototypes/two_code.txt",
        3: REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt",
        'z': REPO_ROOT / "scripts/cangjie/prototypes/z_code.txt",
    }
    if args.s4 or args.gb_only:
        print("正在生成四简原型...")
        generate_shortcut_4(gb_only=args.gb_only)
        shortcut_paths[4] = REPO_ROOT / "scripts/cangjie/prototypes/four_code.txt"
    else:
        # 如果不使用四简，确保旧的原型文件不会被包含（如果它还存在的话）
        p4 = REPO_ROOT / "scripts/cangjie/prototypes/four_code.txt"
        if p4.exists():
            p4.unlink()  # 删除旧的四简原型文件，防止误入字典

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
    )

if __name__ == "__main__":
    main()
