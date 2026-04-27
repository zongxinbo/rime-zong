# 仓颉方案生成器 (Cangjie Scheme Generators)

本目录包含用于生成各种仓颉简码方案的脚本。

## 脚本说明

### 1. `cangjie_builder.py`
核心逻辑库，提供解析字典、过滤汉字、提取简码等通用功能。

### 2. `gen_sancang5.py`
生成三码仓颉五代方案（Sancang5）。
- 提取规则：首次末码。
- 支持词频排序。

### 3. `gen_sicang5.py`
生成四码仓颉五代方案（Sicang5）。
- 提取规则：一二三末码。
- 包含自动化一简分配算法及人工校准逻辑。

### 4. `compare_one_codes.py`
一简方案分配分析工具。
- 对比知乎、北语大、Essay 等不同语料库的一简分配方案。
- 生成 `sicang5/one_code_comparison.md` 报表。
- 实现了“精英平衡版”加权共识算法。

## 使用方法

建议从仓库根目录执行：

```powershell
python scripts/cangjie/gen_sancang5.py
python scripts/cangjie/gen_sicang5.py
```

### 常用选项

- `--include-phrases`: 读取词频文件中的多字词并生成编码。
- `--no-vocabulary`: 不写入 Rime 的 `vocabulary` 字段，生成纯码表。
- `--frequency-file <path>`: 指定字频/词频文件。
- `--generated-phrase-min-weight <int>`: 设置生成词组的最小权重。
