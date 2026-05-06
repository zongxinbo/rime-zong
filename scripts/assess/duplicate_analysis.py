import argparse
from collections import defaultdict
from utils import parse_rime_dict, is_gb2312, load_freq

def analyze_duplicates(dict_path, freq_path, charset_filter=is_gb2312, mode='all', sort_method='frequency', _preloaded_freq=None, _preloaded_entries=None):
    """分析重码情况 (支持上下文感知的原始码表模拟)"""
    if _preloaded_entries is not None:
        entries = _preloaded_entries
    else:
        header, entries = parse_rime_dict(dict_path)
    if _preloaded_freq is not None:
        freqs = _preloaded_freq
    else:
        freqs, _ = load_freq(freq_path)
    
    # 1. 建立全局上下文：模拟真实输入法在处理该字典时的候选词序
    # code -> [char1, char2, ...] (按字典出现顺序)
    global_context = defaultdict(list)
    for char, code, _ in entries:
        # 只有单字进入重码分析 (yuhao-assess 逻辑)
        if len(char) == 1:
            if char not in global_context[code]:
                global_context[code].append(char)

    # 2. 收集参与评估的字符及其编码
    char_to_codes = defaultdict(list)
    for char, code, _ in entries:
        if charset_filter(char):
            char_to_codes[char].append(code)
            
    # 3. 根据模式 (shortest/longest/all/mixed) 筛选评估点
    eval_points = [] # list of (char, code)
    if mode == 'mixed':
        # 混合输入模式：评估的是“字”而非“条目”
        # 只要该字在任意一个编码下是第一候选，则视为“可盲打”
        char_is_first_anywhere = {}
        for char in char_to_codes:
            is_first = False
            for code in char_to_codes[char]:
                if global_context[code] and global_context[code][0] == char:
                    is_first = True
                    break
            char_is_first_anywhere[char] = is_first
            
        total_eval_freq = sum(freqs.get(char, 0) for char in char_to_codes)
        total_dup_freq = sum(freqs.get(char, 0) for char, is_first in char_is_first_anywhere.items() if not is_first)
        
        return {
            "total_chars": len(char_to_codes),
            "dup_groups": sum(1 for is_first in char_is_first_anywhere.values() if not is_first), # 这里的“组”定义为无法首选的字数
            "dup_chars": sum(1 for is_first in char_is_first_anywhere.values() if not is_first),
            "dynamic_rate": total_dup_freq / total_eval_freq if total_eval_freq > 0 else 0
        }

    for char, codes in char_to_codes.items():
        if mode == 'shortest':
            eval_points.append((char, min(codes, key=len)))
        elif mode == 'longest':
            eval_points.append((char, max(codes, key=len)))
        else:
            for c in codes:
                eval_points.append((char, c))

    # 4. 计算重码
    dup_groups_count = 0
    dup_chars_count = 0
    total_dup_freq = 0.0
    
    # 统计所有参与评估字符的总频率 (分母)
    # 注意：这里要按照 yuhao-assess 逻辑，以 eval_points 中的字符为准
    total_eval_freq = sum(freqs.get(char, 0) for char, _ in eval_points)

    # 为了计算“组”，我们需要再次按编码聚类
    code_to_eval_chars = defaultdict(list)
    for char, code in eval_points:
        code_to_eval_chars[code].append(char)

    for code, chars in code_to_eval_chars.items():
        if sort_method == 'frequency':
            # 理想模式：仅看评估范围内的字符，并按频率重排
            if len(chars) > 1:
                dup_groups_count += 1
                dup_chars_count += len(chars)
                sorted_chars = sorted(chars, key=lambda x: freqs.get(x, 0), reverse=True)
                group_freq = sum(freqs.get(c, 0) for c in sorted_chars)
                total_dup_freq += (group_freq - freqs.get(sorted_chars[0], 0))
        else:
            # 原始码表模式：必须参考 global_context (上下文)
            # 即使评估集中只有一个字，如果它在全局上下文中不是首选，也算重码
            full_candidates = global_context[code]
            for char in chars:
                pos = full_candidates.index(char) + 1
                if pos > 1:
                    # 只要不是第一个，就是重码
                    total_dup_freq += freqs.get(char, 0)
            
            # 静态指标统计 (依然保持局部统计)
            if len(chars) > 1:
                dup_groups_count += 1
                dup_chars_count += len(chars)

    return {
        "total_chars": len(eval_points),
        "dup_groups": dup_groups_count,
        "dup_chars": dup_chars_count,
        "dynamic_rate": total_dup_freq / total_eval_freq if total_eval_freq > 0 else 0
    }

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument("--dict", required=True)
    parser.add_argument("--freq", default="schemas/common/frequency/char/sc/zhihu_char_freq.txt")
    parser.add_argument("--mode", choices=['shortest', 'longest', 'all', 'mixed'], default='all')
    parser.add_argument("--sort", choices=['frequency', 'original'], default='frequency')
    parser.add_argument("--all-chars", action="store_true", help="Analyze all characters, not just GB2312")
    args = parser.parse_args()
    
    charset_filter = lambda x: True if args.all_chars else is_gb2312
    res = analyze_duplicates(args.dict, args.freq, charset_filter=charset_filter, mode=args.mode, sort_method=args.sort)
    print(f"评估条目数: {res['total_chars']}")
    print(f"重码组数: {res['dup_groups']}")
    print(f"重码字数: {res['dup_chars']}")
    print(f"动态选重率: {res['dynamic_rate']*10000:.2f}‱")
