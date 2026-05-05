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

from core.cangjie_builder import generate_dict, REPO_ROOT
from core.gen_shortcut_2 import generate_shortcut_2
from core.gen_shortcut_3 import generate_shortcut_3
from core.gen_shortcut_4 import generate_shortcut_4

def main():
    parser = argparse.ArgumentParser(description="Wucang5 生产构建脚本 (五码方案·纯单字流)")
    parser.add_argument("--exclude-extended", action="store_true", default=False,
                        help="过滤增广字集（Ext-B及以上）")
    args = parser.parse_args()

    # 按依赖顺序生成简码：S2 → S3 → S4
    print("=" * 50)
    print("正在生成二简原型...")
    generate_shortcut_2()

    print("正在生成三简原型...")
    generate_shortcut_3()

    print("正在生成四简原型...")
    generate_shortcut_4()

    print("=" * 50)
    print("正在构建最终字典...")
    generate_dict(
        output_path=REPO_ROOT / "schemas/cangjie/wucang5/wucang5.dict.yaml",
        shortcut_paths={
            1: REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt",
            2: REPO_ROOT / "scripts/cangjie/prototypes/two_code.txt",
            3: REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt",
            4: REPO_ROOT / "scripts/cangjie/prototypes/four_code.txt",
            'z': REPO_ROOT / "scripts/cangjie/prototypes/z_code.txt",
        },
        source_dict=REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml",
        freq_file=REPO_ROOT / "schemas/common/essay-zh-hans.txt",
        max_code_length=5,
        exclude_extended=args.exclude_extended,
    )

if __name__ == "__main__":
    main()
