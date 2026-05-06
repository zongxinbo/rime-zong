import argparse
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from duplicate_analysis import analyze_duplicates
from short_code_efficiency import analyze_efficiency, analyze_top_n_efficiency
from speed_equivalent import analyze_speed_equivalent
from maximum_candidates import analyze_max_candidates
from keyboard_heatmap import analyze_heatmap
from utils import parse_rime_dict, get_charset_filter, load_freq, merge_freq
import unicodedata

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def get_display_width(s):
    width = 0
    for char in s:
        if char == '‱' or unicodedata.east_asian_width(char) in ('W', 'F'):
            width += 2
        else:
            width += 1
    return width

def pad_wide(s, width, align='left'):
    s = str(s)
    display_width = get_display_width(s)
    padding = max(0, width - display_width)
    if align == 'left':
        return s + ' ' * padding
    elif align == 'right':
        return ' ' * padding + s
    else:
        left_pad = padding // 2
        right_pad = padding - left_pad
        return ' ' * left_pad + s + ' ' * right_pad

def render_bar(percent, max_width=20):
    filled = int(percent * max_width / 100)
    bar = "█" * filled + "░" * (max_width - filled)
    return f"{bar} {percent:5.1f}%"

def main():
    parser = argparse.ArgumentParser(description="Rime 方案全维度性能评估报告")
    parser.add_argument("--dict", required=True, help="待评估的字典文件路径")
    parser.add_argument("--equiv", default="scripts/assess/data/equiv_table.json", help="速度当量表路径")
    args = parser.parse_args()

    dict_path = args.dict
    print("正在加载字频数据...")
    freq_sources = {
        "知乎简体": "schemas/frequency/char/sc/zhihu_char_freq.txt",
        "北语简体": "schemas/frequency/char/sc/blcu_char_freq.txt",
        "台标繁体": "schemas/frequency/char/tc/taiwan_char_freq.txt",
        "古籍繁体": "schemas/frequency/char/tc/guji_char_freq.txt"
    }
    
    freq_data = {}
    norm_freq_data = {}
    for name, path in freq_sources.items():
        if not Path(path).exists(): continue
        norm, _ = load_freq(path)
        freq_data[name] = norm
        norm_freq_data[name] = norm
        
    if "北语简体" in norm_freq_data and "台标繁体" in norm_freq_data:
        joint_norm, _ = merge_freq(norm_freq_data["北语简体"], norm_freq_data["台标繁体"])
        freq_data["繁简联合"] = joint_norm
    
    charsets = [
        ("GB2312", "GB2312"),
        ("CJK_BASIC", "CJK基本"),
        ("CJK_A", "到CJK_A"),
        ("CJK_B", "到CJK_B"),
        ("CJK_ALL", "全字符集")
    ]
    
    # --- [表格 1] 静态重码分析 ---
    print("\n" + "="*30 + " [1] 静态重码分析 " + "="*30)
    header_row = [pad_wide('字符集', 12), pad_wide('全码重码组', 10), pad_wide('全码重码字', 10), pad_wide('简码重码组', 10), pad_wide('简码重码字', 10)]
    header = " | ".join(header_row)
    print(header)
    print("-" * get_display_width(header))
    for cs_key, cs_label in charsets:
        cs_filter = get_charset_filter(cs_key)
        res_long = analyze_duplicates(dict_path, "", charset_filter=cs_filter, mode='longest', _preloaded_freq={})
        res_short = analyze_duplicates(dict_path, "", charset_filter=cs_filter, mode='shortest', _preloaded_freq={})
        print(f"{pad_wide(cs_label, 12)} | {pad_wide(res_long['dup_groups'], 10)} | {pad_wide(res_long['dup_chars'], 10)} | {pad_wide(res_short['dup_groups'], 10)} | {pad_wide(res_short['dup_chars'], 10)}")

    # --- [表格 2] 动态选重率分析 ---
    print("\n" + "="*30 + " [2] 动态选重率分析 " + "="*30)
    header_row = [pad_wide('字频来源', 15), pad_wide('频率降序-全码', 14), pad_wide('频率降序-简码', 14), pad_wide('原始码表-全码', 14), pad_wide('原始码表-简码', 14)]
    header = " | ".join(header_row)
    print(header)
    print("-" * get_display_width(header))
    
    source_to_charset = {"知乎简体": "GB2312", "北语简体": "GB2312", "台标繁体": "GUOZI", "古籍繁体": "CJK_BASIC", "繁简联合": "CJK_BASIC"}

    for freq_name, norm in freq_data.items():
        cs_name = source_to_charset.get(freq_name, "GB2312")
        cs_filter = get_charset_filter(cs_name)
        rate_lf = analyze_duplicates(dict_path, "", charset_filter=cs_filter, mode='longest', sort_method='frequency', _preloaded_freq=norm)['dynamic_rate']
        rate_sf = analyze_duplicates(dict_path, "", charset_filter=cs_filter, mode='shortest', sort_method='frequency', _preloaded_freq=norm)['dynamic_rate']
        rate_lo = analyze_duplicates(dict_path, "", charset_filter=cs_filter, mode='longest', sort_method='original', _preloaded_freq=norm)['dynamic_rate']
        rate_so = analyze_duplicates(dict_path, "", charset_filter=cs_filter, mode='shortest', sort_method='original', _preloaded_freq=norm)['dynamic_rate']
        
        def fmt_cell(val):
            num_str = f"{val*10000:7.2f}"
            return pad_wide(f"  {num_str}‱", 14)
        print(f"{pad_wide(freq_name, 15)} | {fmt_cell(rate_lf)} | {fmt_cell(rate_sf)} | {fmt_cell(rate_lo)} | {fmt_cell(rate_so)}")

    # --- [表格 3] 候选数分析 ---
    print("\n" + "="*30 + " [3] 候选数分析 " + "="*30)
    header = f"{pad_wide('字符集', 12)} | {pad_wide('最大候选项数', 12)} | {pad_wide('平均候选项数', 12)}"
    print(header)
    print("-" * get_display_width(header))
    for cs_key, cs_label in charsets:
        cs_filter = get_charset_filter(cs_key)
        mc = analyze_max_candidates(dict_path, charset_filter=cs_filter)
        if mc:
            print(f"{pad_wide(cs_label, 12)} | {pad_wide(mc['max_candidates'], 12)} | {pad_wide(f'{mc['avg_candidates']:.2f}', 12)}")

    # --- [表格 4] 速度当量分析 ---
    print("\n" + "="*30 + " [4] 速度当量分析 " + "="*30)
    header_row = [pad_wide('字频来源', 15), pad_wide('全码当量', 10), pad_wide('一级简码', 10), pad_wide('二级简码', 10), pad_wide('全部简码', 10)]
    header = " | ".join(header_row)
    print(header)
    print("-" * get_display_width(header))
    
    for name, norm in freq_data.items():
        cs_name = source_to_charset.get(name, "GB2312")
        cs_filter = get_charset_filter(cs_name)
        eq_full = analyze_speed_equivalent(dict_path, norm, args.equiv, charset_filter=cs_filter, mode='full')
        eq_s1 = analyze_speed_equivalent(dict_path, norm, args.equiv, charset_filter=cs_filter, mode='s1')
        eq_s2 = analyze_speed_equivalent(dict_path, norm, args.equiv, charset_filter=cs_filter, mode='s2')
        eq_all = analyze_speed_equivalent(dict_path, norm, args.equiv, charset_filter=cs_filter, mode='all')
        row = [pad_wide(name+"字频", 15), pad_wide(f"{eq_full:.4f}", 10), pad_wide(f"{eq_s1:.4f}", 10), pad_wide(f"{eq_s2:.4f}", 10), pad_wide(f"{eq_all:.4f}", 10)]
        print(" | ".join(row))

    # --- [表格 5] 简码效率分析 ---
    print("\n" + "="*30 + " [5] 简码效率 (加权平均码长随简码量变化) " + "="*30)
    header_row = [pad_wide('简码数量', 10), pad_wide('知乎简体', 12), pad_wide('北语简体', 12), pad_wide('台标繁体', 12), pad_wide('古籍繁体', 12), pad_wide('繁简联合', 12)]
    header = " | ".join(header_row)
    print(header)
    print("-" * get_display_width(header))
    
    top_n_list = [0, 25, 50, 100, 200, 500]
    for n in top_n_list:
        row = [pad_wide(str(n), 10)]
        for name in ["知乎简体", "北语简体", "台标繁体", "古籍繁体", "繁简联合"]:
            if name not in freq_data: continue
            cs_name = source_to_charset.get(name, "GB2312")
            cs_filter = get_charset_filter(cs_name)
            val = analyze_top_n_efficiency(dict_path, freq_data[name], n, charset_filter=cs_filter)
            row.append(pad_wide(f"{val:.4f}", 12))
        print(" | ".join(row))

    # --- [表格 6] 键盘热力与负载 ---
    print("\n" + "="*30 + " [6] 键盘热力与负载分析 " + "="*30)
    # 严格对齐 yuhao-assess：默认使用 北语简体 (BLCU)
    blcu_norm = freq_data.get("北语简体", {})
    hm = analyze_heatmap(dict_path, "", _preloaded_freq=blcu_norm)
    if hm:
        print(f"  [左右手平衡 (相对比)]")
        l_p, r_p = hm['hand_balance']['left'], hm['hand_balance']['right']
        print(f"  左手: {render_bar(l_p, 30)}")
        print(f"  右手: {render_bar(r_p, 30)}")
        
        print(f"\n  [手指负载分布]")
        finger_order = ['左小指', '左无名指', '左中指', '左食指', '双拇指', '右食指', '右中指', '右无名指', '右小指']
        for finger in finger_order:
            val = hm['finger_load'].get(finger, 0.0)
            print(f"  {pad_wide(finger, 10)}: {render_bar(val, 25)}")
            
        print(f"\n  [排级负载分布]")
        row_order = ['数字排', '上排', '中排', '下排', '空格排']
        for row_name in row_order:
            val = hm['row_load'].get(row_name, 0.0)
            print(f"  {pad_wide(row_name, 10)}: {render_bar(val, 25)}")

    print("\n评估完成。")

if __name__ == "__main__":
    main()
