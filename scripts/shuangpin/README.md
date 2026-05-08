# 双拼与辅助码生成工具集 (scripts/shuangpin)

本目录包含了用于维护、定制和重新生成双拼（自然码/小鹤）方案字典及辅助码数据的脚本。

这些脚本致力于构建一套基于**双拼 + 仓颉五代辅码**的输入体系，旨在实现极致的输入确定性和高效率。

## 文件目录结构

*   **`prototypes/`**: 存放所有核心原始数据文件。
    *   `chars.txt`: 包含十万字全拼读音和词频的核心字表。
    *   `chars.dict.yaml`: 生成字典时的 YAML 头部模板（已包含偏旁部首的快捷输入映射）。
    *   `cangjie_aux.txt`: 自动生成的 字-辅码 对照表，方便查阅。
*   **`gen_chars.py`**: 核心生成引擎。负责读取全拼数据、转换双拼（自然码/小鹤）、匹配仓颉辅码并输出最终字典。
*   **`cangjie_aux.py`**: 仓颉辅助码提取库。负责解析仓颉字典并计算首尾两码。
*   **`utils.py` / `zrmify.py` / `flypyify.py`**: 提供底层数据读取和双拼转换算法支持。

## 使用流程

如果你更新了 `prototypes/chars.txt` 或 `cangjie5.dict.yaml`，请在项目根目录下依次执行：

```bash
# 1. 生成自然码双拼版单字字典 (输出到 schemas/zrm/zrm.chars.dict.yaml)
python scripts/shuangpin/gen_chars.py --schema zrm

# 2. 生成小鹤双拼版单字字典 (输出到 schemas/flypy/flypy.chars.dict.yaml)
python scripts/shuangpin/gen_chars.py --schema flypy
```

## 功能说明

*   **仓颉辅码生成**：`gen_chars.py` 会自动遍历当前字表中的汉字，并在 `prototypes/cangjie_aux.txt` 中同步生成一份详尽的汉字到仓颉首尾码的对照表。
*   **自动填充**：在生成 Rime 字典时，脚本会自动将对应的辅码注入到 `拼音;辅码` 的格式中，确保字典与辅码库永远保持一致。
*   **纠错与记录**：任何在 `chars.txt` 中存在但未能在仓颉字典中匹配到编码的字符，都会被记录在 `prototypes/_tmp_dropped_chars.txt` 中，方便你手动补全或排查。
