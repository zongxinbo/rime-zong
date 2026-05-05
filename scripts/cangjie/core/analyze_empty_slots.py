#!/usr/bin/env python3
"""
Sicang5 编码空间与空位分析工具
计算仓颉5代中 2 码和 3 码的“绝对空位”，并评估将其用于无重码简码的可行性。
"""

import sys
from pathlib import Path

# 导入通用工具
sys.path.append(str(Path(__file__).resolve().parent))
from cangjie_builder import (
    parse_cangjie_dict,
    is_han_char,
    REPO_ROOT
)

def main():
    source_dict = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
    
    print("正在解析原始仓颉编码...")
    entries = parse_cangjie_dict(source_dict)
    
    # 记录所有真实的单字全码
    full_codes_2 = set()
    full_codes_3 = set()
    
    for e in entries:
        if not is_han_char(e.text) or e.code.startswith('z') or e.code.startswith('x'):
            continue
        if len(e.code) == 2:
            full_codes_2.add(e.code)
        elif len(e.code) == 3:
            full_codes_3.add(e.code)

    # 计算理论空间 (24 个主键盘字母，排除 x 和 z)
    letters = "abcdefghijklmnopqrstuvwy"
    
    theoretical_2 = set()
    for l1 in letters:
        for l2 in letters:
            theoretical_2.add(l1 + l2)
            
    theoretical_3 = set()
    for l1 in letters:
        for l2 in letters:
            for l3 in letters:
                theoretical_3.add(l1 + l2 + l3)

    # 计算空位
    empty_2 = theoretical_2 - full_codes_2
    empty_3 = theoretical_3 - full_codes_3

    print(f"\n--- 编码空间分析报告 ---")
    print(f"[二码空间] 理论组合: {len(theoretical_2)} 个")
    print(f"  已占用 (全码为2的字): {len(full_codes_2)} 个")
    print(f"  绝对空位: {len(empty_2)} 个")
    print(f"  空位率: {len(empty_2) / len(theoretical_2) * 100:.2f}%")
    
    print(f"\n[三码空间] 理论组合: {len(theoretical_3)} 个")
    print(f"  已占用 (全码为3的字): {len(full_codes_3)} 个")
    print(f"  绝对空位: {len(empty_3)} 个")
    print(f"  空位率: {len(empty_3) / len(theoretical_3) * 100:.2f}%")

    print("\n--- 结论评估 ---")
    if len(empty_2) >= 150:
        print(f"二码空位 ({len(empty_2)}) 足够容纳 150 个二简字！完全有潜力实现『零重码二简』。")
    else:
        print(f"二码空位 ({len(empty_2)}) 不足 150 个。实现零重码二简需要妥协数量，或采用特征编码。")
        
    if len(empty_3) >= 250:
        print(f"三码空位 ({len(empty_3)}) 极其充裕，完全可以实现『零重码三简』。")

if __name__ == "__main__":
    main()
