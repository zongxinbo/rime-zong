import os
import argparse
from utils import freq_simp_table, freq_trad_table, get_chars_version
from zrmify import zrmify
from flypyify import flypyify
from collections import defaultdict

def get_cangjie_mapping(cangjie_path='../../schemas/cangjie/cangjie5/cangjie5.dict.yaml'):
    char_raw_codes = defaultdict(list)
    with open(cangjie_path, 'r', encoding='utf-8') as f:
        in_body = False
        for line in f:
            if line.strip() == '...':
                in_body = True
                continue
            if not in_body or not line.strip() or line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                char, code = parts[0], parts[1]
                char_raw_codes[char].append(code)
    
    mapping = {}
    for char, codes in char_raw_codes.items():
        preferred_shorts = []
        other_shorts = []
        for code in codes:
            short = code[0] + code[-1] if len(code) > 1 else code
            if not (code.startswith('z') or code.startswith('x')):
                if short not in preferred_shorts:
                    preferred_shorts.append(short)
            else:
                if short not in other_shorts and short not in preferred_shorts:
                    other_shorts.append(short)
        
        all_shorts = preferred_shorts + other_shorts
        if all_shorts:
            mapping[char] = all_shorts
            
    return mapping

def main():
    parser = argparse.ArgumentParser(description="Generate double pinyin dict (full) and Shouxin aux text (GBK only).")
    parser.add_argument('--simplified', action='store_true', help="Use simplified frequency table")
    parser.add_argument('--schema', choices=['zrm', 'flypy'], default='zrm', help="Target double pinyin schema")
    args = parser.parse_args()

    if args.simplified:
        freq_table = freq_simp_table
    else:
        freq_table = freq_trad_table

    print("Loading Cangjie5 dict...")
    cangjie_map = get_cangjie_mapping()
    
    # --- Part 1: Generate Shouxin aux text (GBK only, multi-line) ---
    aux_txt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prototypes/cangjie_aux.txt')
    print(f"Generating Shouxin aux text to {aux_txt_path}...")
    
    # 回退到 UTF-16 (带 BOM 的 UTF-16 LE)
    with open(aux_txt_path, 'w', encoding='utf-8') as f:
        all_chars_in_dict = {char for (char, py), w in freq_table.items()}
        
        for char, aux_list in cangjie_map.items():
            if char in all_chars_in_dict:
                try:
                    char.encode('gbk')
                    for aux in aux_list:
                        f.write(f'{char}={aux}\n')
                except UnicodeEncodeError:
                    continue
    
    # --- Part 2: Generate Full Rime Dictionary (Full Scale, single best code) ---
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prototypes/chars.dict.yaml')
    with open(template_path, 'r', encoding='utf-8') as f:
        header_template = f.read()

    header = header_template.replace('YYYYmmdd', get_chars_version())
    import re
    header = re.sub(r'name: \w+\.chars', f'name: {args.schema}.chars', header)

    output_dir = f'../../schemas/{args.schema}'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'{args.schema}.chars.dict.yaml')

    print(f"Generating full Rime dictionary to {output_path}...")
    dropped_chars = set()

    with open(output_path, 'w', encoding='utf-8') as out_f:
        new_header_lines = []
        in_radicals = False
        for line in header.split('\n'):
            if line.startswith('# 偏旁部首'):
                in_radicals = True
            
            if in_radicals and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 2 and ';' in parts[1]:
                    char = parts[0]
                    sp, _ = parts[1].split(';', 1)
                    if char in cangjie_map:
                        best_aux = cangjie_map[char][0]
                        parts[1] = f"{sp};{best_aux}"
                        new_header_lines.append('\t'.join(parts))
                    else:
                        dropped_chars.add(char)
                else:
                    new_header_lines.append(line)
            else:
                new_header_lines.append(line)
                
        out_f.write('\n'.join(new_header_lines) + '\n')

        for ((char, py), w) in freq_table.items():
            if args.schema == 'flypy':
                sp = flypyify(py)
            else:
                sp = zrmify(py)
                
            if char in cangjie_map:
                best_aux = cangjie_map[char][0]
                out_f.write(f'{char}\t{sp};{best_aux}\t{w}\n')
            else:
                dropped_chars.add(char)
                
    print(f"Generation complete. {len(dropped_chars)} chars in Rime dict lack Cangjie codes.")
    if dropped_chars:
        dropped_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'prototypes/_tmp_dropped_chars.txt')
        with open(dropped_file_path, 'w', encoding='utf-8') as f:
            for c in sorted(list(dropped_chars)):
                f.write(c + '\n')
        print(f"Dropped character log updated: {dropped_file_path}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
