import csv
import openpyxl
import os
from pathlib import Path

# 获取仓库根目录
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def convert_zhihu(csv_path, output_path):
    print(f"Converting {csv_path} to {output_path}...")
    with open(csv_path, 'r', encoding='utf-8') as f_in:
        reader = csv.DictReader(f_in)
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for row in reader:
                char = row['char']
                count = row['count']
                if char and count:
                    f_out.write(f"{char}\t{count}\n")

def convert_blcu(xlsx_path, output_path):
    print(f"Converting {xlsx_path} to {output_path}...")
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    sheet = wb.active
    with open(output_path, 'w', encoding='utf-8') as f_out:
        # Assuming header is row 0, data starts at row 1
        # Column 1: character, Column 2: token
        for row in sheet.iter_rows(min_row=2, values_only=True):
            char = row[1]
            count = row[2]
            if char and count is not None:
                f_out.write(f"{char}\t{int(count)}\n")

if __name__ == "__main__":
    convert_zhihu(REPO_ROOT / 'frequency/6亿知乎语料通规汉字字频表.csv', REPO_ROOT / 'frequency/zhihu_freq.txt')
    convert_blcu(REPO_ROOT / 'frequency/北京语言大学25亿字语料汉字字频表.xlsx', REPO_ROOT / 'frequency/blcu_freq.txt')
    print("Done.")
