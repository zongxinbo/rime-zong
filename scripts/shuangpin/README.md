# 双拼音形生成系统

本目录用于生成「双拼 + 仓颉五代辅助码」音形方案。

当前构建目标：

- 单字：原型为双拼 2 码 + 仓颉五代首尾辅助码 2 码；最终码表显式展开为一/二/三/四码多编码条目。
- 词语：原型为 6 码词码；最终码表显式展开为 0/1/2 位辅助码词码。
- 仓颉：完整仓颉码前加 `o`，长度 2-6 码，候选排在普通条目之后。
- 输出：源码分层维护，Rime 最终使用一个合一的 `{schema}.dict.yaml`。
- 排序：最终码表使用 `sort: original`，不写词频列；同码候选按 `schemas/common/frequency` 下的简体字频、词频文件综合排序，`o` 前缀仓颉候选排在普通条目之后。
- 迁移：最终 `{schema}.dict.yaml` 不依赖 Rime 的补全功能，其他平台只要支持静态多编码码表即可使用。

## 目录结构

```text
scripts/shuangpin/
  gen_zrm.py              # 生成自然码·仓颉完整方案
  gen_flypy.py            # 生成小鹤·仓颉完整方案
  gen_chars.py            # 只生成单字原型
  core/                   # 构建模块
  prototypes/
    chars.txt             # 原始字音、繁简频率
    chars.dict.yaml       # 偏旁部首原型
    cangjie_aux.txt       # 手心输入法挂接用辅助码，格式为 字=辅码
    zrm/
      zrm.chars.txt
      zrm.words.txt
      zrm.cangjie.txt
      zrm.report.md
    flypy/
      flypy.chars.txt
```

## 使用

在仓库根目录执行：

```powershell
# 生成自然码·仓颉完整方案
python scripts/shuangpin/gen_zrm.py

# 仅生成自然码单字原型
python scripts/shuangpin/gen_chars.py --schema zrm

# 仅生成小鹤单字原型
python scripts/shuangpin/gen_chars.py --schema flypy
```

生成自然码完整方案时会输出：

```text
scripts/shuangpin/prototypes/zrm/zrm.chars.txt
scripts/shuangpin/prototypes/cangjie_aux.txt
scripts/shuangpin/prototypes/zrm/zrm.words.txt
scripts/shuangpin/prototypes/zrm/zrm.cangjie.txt
scripts/shuangpin/prototypes/zrm/zrm.report.md
schemas/zrm/zrm.dict.yaml
schemas/zrm/zrm.schema.yaml
```

## 词码规则

词语原型固定 6 码，最终码表同时输出去掉辅助码后的 4 码、加首字辅助码后的 5 码、以及首末辅助码完整 6 码。

```text
二字词：
  字1双拼全码 + 字2双拼全码
  字1双拼全码 + 字2双拼全码 + 首字辅码首码
  字1双拼全码 + 字2双拼全码 + 首字辅码首码 + 末字辅码首码

三字词：
  字1双拼首码 + 字2双拼首码 + 字3双拼全码
  字1双拼首码 + 字2双拼首码 + 字3双拼全码 + 首字辅码首码
  字1双拼首码 + 字2双拼首码 + 字3双拼全码 + 首字辅码首码 + 末字辅码首码

四字词：
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 字4双拼首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 字4双拼首码 + 首字辅码首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 字4双拼首码 + 首字辅码首码 + 末字辅码首码

五字及以上词：
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 末字双拼首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 末字双拼首码 + 首字辅码首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 末字双拼首码 + 首字辅码首码 + 末字辅码首码
```

默认词源使用 `schemas/pinyin_ice/pinyin_ice.base.dict.yaml`，只取 2-4 字且权重不低于 5000 的高频词，并过滤以语气词、结构助词、轻助动词和连接虚词组成的语流片段。它比 `pinyin_simp` 更现代，也更适合当前这种轻词库音形方案。
