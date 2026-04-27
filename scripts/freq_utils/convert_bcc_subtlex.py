import os
from pathlib import Path

# 获取仓库根目录
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def convert_bcc(input_path, output_path):
    print(f"Converting BCC: {input_path} -> {output_path}")
    with open(input_path, 'r', encoding='utf-8') as f_in:
        # Skip header: token,count
        header = f_in.readline()
        if not header.startswith('token,count'):
            print(f"Warning: Unexpected header in {input_path}: {header.strip()}")
        
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    f_out.write(f"{parts[0]}\t{parts[1]}\n")

def convert_subtlex(input_path, output_path, is_word=False):
    print(f"Converting SUBTLEX: {input_path} -> {output_path}")
    with open(input_path, 'r', encoding='gbk') as f_in:
        # Skip header lines (Total count, Context number, Column headers)
        lines = f_in.readlines()
        data_start = 0
        for i, line in enumerate(lines):
            if line.startswith('Character') or line.startswith('Word'):
                data_start = i + 1
                break
        
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for line in lines[data_start:]:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    # Column 0 is character/word, Column 1 is CHRCount/WCount
                    f_out.write(f"{parts[0]}\t{parts[1]}\n")

if __name__ == "__main__":
    # BCC Dialogue
    convert_bcc(
        REPO_ROOT / 'frequency/_original/dialogue_char_freq.txt',
        REPO_ROOT / 'frequency/char/dialogue_char_freq.txt'
    )
    convert_bcc(
        REPO_ROOT / 'frequency/_original/dialogue_word_freq.txt',
        REPO_ROOT / 'frequency/word/dialogue_word_freq.txt'
    )
    
    # BCC Multi-domain
    convert_bcc(
        REPO_ROOT / 'frequency/_original/multi_domain_total_char_freq.txt',
        REPO_ROOT / 'frequency/char/multi_domain_char_freq.txt'
    )
    convert_bcc(
        REPO_ROOT / 'frequency/_original/multi_domain_total_word_freq.txt',
        REPO_ROOT / 'frequency/word/multi_domain_word_freq.txt'
    )
    
    # SUBTLEX
    convert_subtlex(
        REPO_ROOT / 'frequency/_original/SUBTLEX-CH-CHR',
        REPO_ROOT / 'frequency/char/subtlex_char_freq.txt'
    )
    convert_subtlex(
        REPO_ROOT / 'frequency/_original/SUBTLEX-CH-WF',
        REPO_ROOT / 'frequency/word/subtlex_word_freq.txt'
    )
    
    print("All conversions completed.")
