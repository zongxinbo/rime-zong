import sys
from pathlib import Path

# 获取仓库根目录
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def load_freq(path):
    freqs = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) == 2:
                freqs[parts[0]] = int(parts[1])
    return freqs

def get_top(freqs, n=25):
    # Only single characters
    chars = [c for c in freqs.keys() if len(c) == 1]
    return sorted(chars, key=lambda x: freqs[x], reverse=True)[:n]

essay_freqs = load_freq(REPO_ROOT / 'sancang5/essay-zh-hans.txt')
zhihu_freqs = load_freq(REPO_ROOT / 'frequency/zhihu_freq.txt')
blcu_freqs = load_freq(REPO_ROOT / 'frequency/blcu_freq.txt')

print("Top 25 comparison:")
print(f"{'Rank':<5} | {'Essay':<5} | {'Zhihu':<5} | {'BLCU':<5}")
print("-" * 30)
top_essay = get_top(essay_freqs)
top_zhihu = get_top(zhihu_freqs)
top_blcu = get_top(blcu_freqs)

for i in range(25):
    print(f"{i+1:<5} | {top_essay[i]:<5} | {top_zhihu[i]:<5} | {top_blcu[i]:<5}")
