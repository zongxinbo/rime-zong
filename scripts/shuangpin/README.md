# 双拼音形生成系统

本目录用于生成「双拼 + 仓颉五代辅助码」音形方案。

当前构建目标：

- 单字：原型为双拼 2 码 + 仓颉五代首尾辅助码 2 码；一位仓颉辅助码末尾补 `z`；一简按首键取首选，二码按双拼音节保底首选并收少量高频次选，三码按“双拼 + 首辅码”保底首选并收高频次选，所有字保留四码全码，异读不占短码。
- 词语：所有入库词生成全双拼码及其辅码定重码；只有高频词额外生成逐字首码短码及其辅码定重码。
- 单字版：`zrm_single`、`flypy_single` 不收词、不造词，只保留双拼音形单字和 `o` 前缀仓颉兜底；当前只生成自然码单字方案。
- 仓颉：完整仓颉码前加 `o`，同字多码全部保留，候选排在普通条目之后；如果仓颉短码被普通候选挡住，且补码后不超过 6 码，则另补 `z` 尾码直达。
- 输出：源码分层维护，Rime 最终使用一个合一的 `{schema}.dict.yaml`。
- 排序：最终码表使用 `sort: original`，不写词频列；单字按 `schemas/common/frequency` 下的简体字频排序，词语主要按 `essay-zh-hans` 频率排序，`o` 前缀仓颉候选排在普通条目之后。
- 迁移：最终 `{schema}.dict.yaml` 不依赖 Rime 的补全功能，其他平台只要支持静态多编码码表即可使用；Rime 端开启 `enable_completion`，用于全码路径未打完时提前显示候选。

## 目录结构

```text
scripts/shuangpin/
  gen_zrm.py              # 生成自然码·仓颉完整方案
  gen_zrm_single.py       # 生成自然码·仓颉纯单字方案
  gen_flypy.py            # 生成小鹤·仓颉完整方案
  gen_flypy_single.py     # 生成小鹤·仓颉纯单字方案（脚本已支持，默认不生成产物）
  gen_chars.py            # 只生成单字原型
  core/                   # 构建模块
  prototypes/
    chars.txt             # 原始字音、繁简频率
    chars.dict.yaml       # 偏旁部首原型
    zrm/
      zrm.chars.txt
      zrm.words.txt
      zrm.cangjie.txt
      zrm.report.md
    zrm_single/
      zrm_single.chars.txt
      zrm_single.cangjie.txt
      zrm_single.report.md
    flypy/
      flypy.chars.txt
```

## 使用

在仓库根目录执行：

```powershell
# 生成自然码·仓颉完整方案
python scripts/shuangpin/gen_zrm.py

# 生成自然码·仓颉纯单字方案
python scripts/shuangpin/gen_zrm_single.py

# 生成小鹤·仓颉纯单字方案；仓库默认不生成对应产物
python scripts/shuangpin/gen_flypy_single.py

# 仅生成自然码单字原型
python scripts/shuangpin/gen_chars.py --schema zrm

# 仅生成小鹤单字原型
python scripts/shuangpin/gen_chars.py --schema flypy
```

生成自然码完整方案时会输出：

```text
scripts/shuangpin/prototypes/zrm/zrm.chars.txt
scripts/shuangpin/prototypes/zrm/zrm.words.txt
scripts/shuangpin/prototypes/zrm/zrm.cangjie.txt
scripts/shuangpin/prototypes/zrm/zrm.report.md
schemas/shuangpin/cangjie_aux.txt
schemas/shuangpin/zrm/zrm.dict.yaml
schemas/shuangpin/zrm/zrm.schema.yaml
```

生成自然码纯单字方案时会输出：

```text
scripts/shuangpin/prototypes/zrm_single/zrm_single.chars.txt
scripts/shuangpin/prototypes/zrm_single/zrm_single.cangjie.txt
scripts/shuangpin/prototypes/zrm_single/zrm_single.report.md
schemas/shuangpin/cangjie_aux.txt
schemas/shuangpin/zrm_single/zrm_single.dict.yaml
schemas/shuangpin/zrm_single/zrm_single.schema.yaml
```

## 词码规则

本节只适用于带词方案；`zrm_single` 不生成任何词码。

词语同时支持短码路线和全码路线：短码使用逐字双拼首码，并可追加首末字仓颉辅码；全码使用逐字双拼全码，也可追加首末字仓颉辅码。为了减少噪音，短码只给高频词生成；低频词仍保留全码路线。

```text
二字词：
  字1双拼首码 + 字2双拼首码
  字1双拼首码 + 字2双拼首码 + 首字辅码首码
  字1双拼首码 + 字2双拼首码 + 首字辅码首码 + 末字辅码首码
  字1双拼全码 + 字2双拼全码
  字1双拼全码 + 字2双拼全码 + 首字辅码首码
  字1双拼全码 + 字2双拼全码 + 首字辅码首码 + 末字辅码首码

三字词：
  字1双拼首码 + 字2双拼首码 + 字3双拼首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 首字辅码首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 首字辅码首码 + 末字辅码首码
  字1双拼全码 + 字2双拼全码 + 字3双拼全码
  字1双拼全码 + 字2双拼全码 + 字3双拼全码 + 首字辅码首码
  字1双拼全码 + 字2双拼全码 + 字3双拼全码 + 首字辅码首码 + 末字辅码首码

四字词：
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 字4双拼首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 字4双拼首码 + 首字辅码首码
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 字4双拼首码 + 首字辅码首码 + 末字辅码首码
  字1双拼全码 + 字2双拼全码 + 字3双拼全码 + 字4双拼全码
  字1双拼全码 + 字2双拼全码 + 字3双拼全码 + 字4双拼全码 + 首字辅码首码
  字1双拼全码 + 字2双拼全码 + 字3双拼全码 + 字4双拼全码 + 首字辅码首码 + 末字辅码首码
```

默认主词源使用 `schemas/common/essay-zh-hans.txt`，用它决定“哪些词值得收”和最终排序频率；词级读音优先借用 `schemas/pinyin_ice/pinyin_ice.base.dict.yaml`，再用 `scripts/shuangpin/prototypes/chars.txt` 对无多音歧义的词做兜底。默认入库阈值按 essay 频率区分：二字词不低于 50，三字词不低于 100，四字词不低于 30；四字词如果能拆成两个已经入库的二字词，则不再作为固定四字词收录。pinyin_ice 不再反向抬高 essay 条目的权重，避免“我们将”“为保证”这类低频语流片段回流。另外从 `pinyin_ice.base` 只补 essay 缺失且权重不低于 500000 的高频二字词，补入词只生成全码路线。默认短码阈值同样按 essay 频率判断：二字词不低于 12000、三字词不低于 8000、四字词不低于 3000。这个设计把“主词库质量/排序”和“词级读音/极少量补缺”拆开，同时保留“白术”这类需要词级异读的条目。
