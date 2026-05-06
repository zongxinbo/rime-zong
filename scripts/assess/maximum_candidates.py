import argparse
from collections import defaultdict
from utils import parse_rime_dict, is_gb2312

def analyze_max_candidates(dict_path, charset_filter=is_gb2312):
    """分析编码对应的候选项个数"""
    _, entries = parse_rime_dict(dict_path)
    
    code_map = defaultdict(list)
    char_seen = set()
    
    for char, code, _ in entries:
        if charset_filter(char) and char not in char_seen:
            char_seen.add(char)
            code_map[code].append(char)
            
    if not code_map:
        return None
        
    max_cands = 0
    max_codes = []
    
    # 统计最大候选项个数及对应的编码
    for code, chars in code_map.items():
        if len(chars) > max_cands:
            max_cands = len(chars)
            max_codes = [code]
        elif len(chars) == max_cands:
            max_codes.append(code)
            
    return {
        "max_candidates": max_cands,
        "max_codes": max_codes,
        "avg_candidates": sum(len(c) for c in code_map.values()) / len(code_map)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分析 Rime 字典的候选项个数分布")
    parser.add_argument("--dict", required=True, help="字典文件路径")
    args = parser.parse_args()
    
    res = analyze_max_candidates(args.dict)
    if res:
        print(f"最大候选项个数: {res['max_candidates']}")
        print(f"平均候选项个数: {res['avg_candidates']:.2f}")
        print(f"达到最大候选项个数的编码: {', '.join(res['max_codes'][:10])}{'...' if len(res['max_codes']) > 10 else ''}")
