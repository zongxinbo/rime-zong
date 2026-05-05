# 字频工具 (Frequency Utilities)

本目录包含处理和比较不同汉字字频数据的脚本。

## 脚本说明

### 1. `convert_frequencies.py`
将不同格式的原始字频表转换为 Rime 兼容的 `字符\t频次` 格式。
- **Zhihu CSV**: 从 `schemas/frequency/6亿知乎语料通规汉字字频表.csv` 提取汉字和频次。
- **BLCU XLSX**: 从 `schemas/frequency/北京语言大学25亿字语料汉字字频表.xlsx` 提取汉字和频次（Token）。

### 2. `compare_freqs.py`
对比三个主要语料库（Essay, Zhihu, BLCU）的前 25 名高频单字，用于分析简码分配的合理性。

### 3. `inspect_xlsx.py` & `inspect_xlsx_header.py`
用于检查 XLSX 文件的结构和表头，确定数据列。

## 使用方法

建议在仓库根目录执行，或在脚本中手动调整路径。

```powershell
python scripts/freq_utils/convert_frequencies.py
python scripts/freq_utils/compare_freqs.py
```

## 转换逻辑
- **CSV 转换**: 使用 `csv.DictReader` 读取，确保编码为 UTF-8。
- **XLSX 转换**: 使用 `openpyxl` 加载，读取 `data_only=True` 以获取公式计算后的值。
- **整数化**: 统一提取原始计数（count/token），确保频次为整数。
