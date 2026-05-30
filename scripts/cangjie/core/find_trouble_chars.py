import sys
from pathlib import Path
from collections import defaultdict

# 避免 Windows 终端输出编码错误
sys.stdout.reconfigure(encoding='utf-8')

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root / "scripts/assess"))

from utils import parse_rime_dict, load_freq, is_gb2312

def main():
    dict_path = "schemas/cangjie/sicang5/sicang5.dict.yaml"
    freq_path = "schemas/common/frequency/char/sc/zhihu_char_freq.txt"
    
    # 1. 加载字频
    freqs, _ = load_freq(freq_path)
    
    # 2. 解析字典
    _, entries = parse_rime_dict(dict_path)
    
    # 3. 建立全局上下文
    global_context = defaultdict(list)
    for char, code, _ in entries:
        if len(char) == 1:
            if char not in global_context[code]:
                global_context[code].append(char)
                
    # 4. 收集字符的所有编码
    char_to_codes = defaultdict(list)
    for char, code, _ in entries:
        if is_gb2312(char):
            char_to_codes[char].append(code)
            
    # 5. 找出在所有编码下都不是首选的汉字
    trouble_chars = []
    for char in char_to_codes:
        is_first_anywhere = False
        for code in char_to_codes[char]:
            if global_context[code] and global_context[code][0] == char:
                is_first_anywhere = True
                break
        if not is_first_anywhere:
            weight = freqs.get(char, 0)
            trouble_chars.append((char, weight, char_to_codes[char]))
            
    # 按字频降序排列
    trouble_chars.sort(key=lambda x: x[1], reverse=True)
    
    print("==================================================")
    print(f"知乎简体下，任何编码都无法首选的痛点汉字 (总数: {len(trouble_chars)}):")
    total_trouble_freq = sum(x[1] for x in trouble_chars)
    print(f"累计痛点字频占比: {total_trouble_freq*10000:.2f} Ɒ")
    print("--------------------------------------------------")
    for i, (char, weight, codes) in enumerate(trouble_chars[:30], 1):
        details = []
        for code in codes:
            first_char = global_context[code][0] if global_context[code] else "无"
            pos = global_context[code].index(char) + 1 if char in global_context[code] else -1
            details.append(f"{code}(首选:{first_char},位置:{pos})")
        print(f"No.{i}: {char} (字频占比:{weight*10000:.4f} ⱱ) | 编码情况: {', '.join(details)}")
    print("==================================================")

if __name__ == "__main__":
    main()
