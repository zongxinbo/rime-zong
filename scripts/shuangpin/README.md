# 双拼音形生成系统

本目录用于生成「双拼 + 仓颉五代辅助码」音形方案。

当前构建目标：

- 单字：原型为双拼 2 码 + 仓颉五代首尾辅助码 2 码；一位仓颉辅助码末尾补 `z`；最终码表只给高频主读音显式展开一/二/三码短码，所有字保留四码全码，异读不占短码。
- 词语：所有入库词生成全双拼码及其辅码定重码；只有高频词额外生成逐字首码短码及其辅码定重码。
- 仓颉：完整仓颉码前加 `o`，同字多码全部保留，候选排在普通条目之后；如果仓颉短码被普通候选挡住，且补码后不超过 6 码，则另补 `z` 尾码直达。
- 输出：源码分层维护，Rime 最终使用一个合一的 `{schema}.dict.yaml`。
- 排序：最终码表使用 `sort: original`，不写词频列；同码候选按 `schemas/common/frequency` 下的简体字频、词频文件综合排序，`o` 前缀仓颉候选排在普通条目之后。
- 迁移：最终 `{schema}.dict.yaml` 不依赖 Rime 的补全功能，其他平台只要支持静态多编码码表即可使用；Rime 端开启 `enable_completion`，用于全码路径未打完时提前显示候选。

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
scripts/shuangpin/prototypes/zrm/zrm.words.txt
scripts/shuangpin/prototypes/zrm/zrm.cangjie.txt
scripts/shuangpin/prototypes/zrm/zrm.report.md
schemas/shuangpin/cangjie_aux.txt
schemas/shuangpin/zrm/zrm.dict.yaml
schemas/shuangpin/zrm/zrm.schema.yaml
```

## 词码规则

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

默认词源使用 `schemas/pinyin_ice/pinyin_ice.base.dict.yaml`。默认入库阈值按词长区分：二字词权重不低于 10，三字和四字词权重不低于 3000；默认短码阈值为二字词不低于 100000、三字词不低于 100000、四字词不低于 300000。二字词不过滤语气词/助词结尾，以保留“我的”“好了”“走了”等口语高频词；三四字词继续过滤以语气词、结构助词、轻助动词、连接虚词和“是……”句段组成的语流片段。它比 `pinyin_simp` 更现代，也更适合当前这种轻词库音形方案。
