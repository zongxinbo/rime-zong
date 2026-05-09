# 双拼音形生成系统

本目录用于生成「双拼 + 仓颉五代辅助码」音形方案。

当前构建目标：

- 单字：双拼 2 码 + 仓颉五代首尾辅助码 2 码，共 4 码。
- 词语：全部显式生成 6 码词码，不生成一简、二简或 5 码词简码。
- 仓颉：完整仓颉码前加 `o`，长度 2-6 码，候选使用低权重放到最后。
- 输出：源码分层维护，Rime 最终使用一个合一的 `{schema}.dict.yaml`。

## 目录结构

```text
scripts/shuangpin/
  gen_zrm.py              # 生成自然码双拼音形完整方案
  gen_flypy.py            # 生成小鹤双拼音形完整方案
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
# 生成自然码完整方案
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

所有词码固定 6 码。

```text
二字词：
  字1双拼全码 + 字2双拼全码 + 首字辅码首码 + 末字辅码首码

三字词：
  字1双拼首码 + 字2双拼首码 + 字3双拼全码 + 首字辅码首码 + 末字辅码首码

四字词：
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 字4双拼首码 + 首字辅码首码 + 末字辅码首码

五字及以上词：
  字1双拼首码 + 字2双拼首码 + 字3双拼首码 + 末字双拼首码 + 首字辅码首码 + 末字辅码首码
```

默认词源使用 `schemas/pinyin_simp/pinyin_simp.dict.yaml`。它比雾凇基础词库小得多，更适合作为音形方案的初始核心词库。
