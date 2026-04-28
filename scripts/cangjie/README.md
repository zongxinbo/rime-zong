# 仓颉方案生成器 (Cangjie Scheme Generators)

本目录包含用于生成各种仓颉简码方案的脚本。

## 脚本说明

### 1. `cangjie_builder.py`
核心逻辑库，提供解析字典、过滤汉字、提取简码等通用功能。

### 2. `gen_sancang5.py`
生成三码仓颉五代方案（Sancang5）。
- 提取规则：首次末码。

### 3. `gen_sicang5.py`
**Sicang5 生产构建脚本**。
- 将一、二、三简码与全量单字、词组打包成最终的 `sicang5.dict.yaml`。
- 优先级：简码 (1/2/3/z) > 单字四码 > 词组四码。

### 4. `gen_sicang5_1.py`
**一简方案设计与生成脚本**。
- 基于 Dialogue、Subtlex、Zhihu、BLCU、Essay 等多源语料加权分配一简。
- 对比不同语料方案并生成 `sicang5/one_code_comparison.md`。
- 自动更新 `sicang5/sicang5_1.txt`。

### 5. `gen_sicang5_2.py`
**二简方案设计与生成脚本**。
- 提取规则：单字首尾码 (Aa + Az)。
- 自动按加权频次生成 Top 150 建议稿至 `sicang5/sicang5_2.txt`。

### 6. `gen_sicang5_3.py`
**三简方案设计与生成脚本**。
- 提取规则：单字首次末码 (Aa + Ab + Az)。
- 自动按加权频次生成 Top 250 建议稿至 `sicang5/sicang5_3.txt`。

## 使用方法

建议从仓库根目录执行设计脚本进行调优，最后执行生产脚本：

```powershell
# 1. 设计简码
python scripts/cangjie/gen_sicang5_1.py
python scripts/cangjie/gen_sicang5_2.py
python scripts/cangjie/gen_sicang5_3.py

# 2. 生成最终词库
python scripts/cangjie/gen_sicang5.py
```

### 常用选项 (cangjie_builder 继承)

- `--include-phrases`: 读取词频文件中的多字词并生成编码。
- `--frequency-file <path>`: 指定字频/词频文件。
- `--generated-phrase-min-weight <int>`: 设置生成词组的最小权重。
