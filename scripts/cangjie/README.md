# 仓颉方案生成系统

本目录用于管理 Sicang5/Wucang5 方案的生成与简码设计。

## 1. 设计简码原型

核心脚本会读取仓颉五码源表与加权字频，生成 `prototypes/` 下的简码原型文件。

```powershell
python scripts/cangjie/core/gen_shortcut_1.py
python scripts/cangjie/core/gen_shortcut_2.py
python scripts/cangjie/core/gen_shortcut_3.py
python scripts/cangjie/core/gen_shortcut_4.py
```

## 2. 生成 Wucang5

默认构建参数：

- 二简：上限 `300` 个；默认保护高频 GBK 原生二码位，综合字频门槛 `3000`
- 三简：固定 `800` 个；默认保护高频 GBK 原生三码位，综合字频门槛 `3000`
- 二简、三简候选池按 Rime 默认 `extended_charset=常用` 状态过滤；长码候选也需达到综合字频门槛才可入选
- 四简：默认关闭，可用 `--s4` 开启 `balanced` 模式，给 GB2312 五码字生成四简
- 四简数量：启用后默认上限 `1000` 个；GB2312 二级字需达到综合字频 `1000` 才可进入
- 一简：单独运行 `core/gen_shortcut_1.py` 生成校准表；生产构建只消费 `one_code.txt`，不自动重算
- 简码总量：builder 口径含 `z_code` 字根码 31 个、一简 25 个、二简 300 个、三简 800 个，默认合计 `1156` 个
- 字根字：未被一简校准表选中的字根字不保留原生一简入口，统一经 `az/azz` 等 `z_code` 字根码输入
- 全码排序：采用简码让位；已有简码字让位给同码且达到综合字频 `1000` 的无简码字，可用 `--fullcode-yield-min-score` 调整
- 后缀选重：Sicang5/Wucang5 默认开启 `z` 后缀直达第二候选；如果第二候选已有首选简码，则不再补后缀
- 前缀选重：满码长重码字默认开启自然 `z/x` 前缀直达码；默认仅处理综合字频中出现的字

```powershell
python scripts/cangjie/gen_wucang5.py
```

常用参数：

```powershell
# 开启四简
python scripts/cangjie/gen_wucang5.py --s4

# 指定四简模式
python scripts/cangjie/gen_wucang5.py --s4 --s4-mode safe
python scripts/cangjie/gen_wucang5.py --s4 --s4-mode balanced
python scripts/cangjie/gen_wucang5.py --s4 --s4-mode aggressive

# 固定四简数量
python scripts/cangjie/gen_wucang5.py --s4 --s4-count 1000

# 调整 GB2312 二级字进入四简的门槛；0 表示不过滤二级字
python scripts/cangjie/gen_wucang5.py --s4 --s4-level2-min-score 1000

# 改用覆盖率决定二简/三简数量
python scripts/cangjie/gen_wucang5.py --s2-count 0 --s2-coverage 0.85 --s3-count 0 --s3-coverage 0.90

# 关闭原生码位保护，恢复高频长码字抢二简/三简码位
python scripts/cangjie/gen_wucang5.py --no-protect-native

# 分别调整二三简原生码位保护与长码候选入选门槛
python scripts/cangjie/gen_wucang5.py --protect-native-min-score 3000 --shortcut-candidate-min-score 3000

# 调整二三简原生码位保护字集
python scripts/cangjie/gen_wucang5.py --protect-native-charset gbk

# 调整全码简码让位的顶位门槛
python scripts/cangjie/gen_wucang5.py --fullcode-yield-min-score 1000

# 关闭或开启 z 后缀直达第二候选
python scripts/cangjie/gen_wucang5.py --no-suffix-z
python scripts/cangjie/gen_sicang5.py --no-suffix-z

# 关闭 z/x 前缀直达码
python scripts/cangjie/gen_wucang5.py --no-dedup-prefix
python scripts/cangjie/gen_sicang5.py --no-dedup-prefix

# 调整 z/x 前缀候选字集和最低综合字频
python scripts/cangjie/gen_sicang5.py --dedup-prefix-charset gbk --dedup-prefix-min-score 1
```

`--protect-native-charset` 支持：

- `gbk`：默认值，保护 GBK 可编码字符，兼顾常见繁简字。
- `gb2312`：仅保护 GB2312 汉字。
- `frequency`：仅保护当前综合字频中出现的字。
- `all`：不限制汉字范围，适合实验。

`z` 后缀和 `z/x` 前缀覆盖互补场景：

- 原码短于方案最大码长：使用 `原码 + z`。
- 原码已经达到方案最大码长：依次尝试 `z + 前两码`、`x + 前两码`、`z + 前三码`、`x + 前三码`。
- 四条自然路径均被占用：不生成直达码，不分配无法推导的任意编码。

`--dedup-prefix-charset` 支持：

- `frequency`：默认值，仅处理当前综合字频中出现的字。
- `gbk`：处理 GBK 可编码字符，兼顾常见繁简字。
- `gb2312`：仅处理 GB2312 汉字。
- `all`：不限制汉字范围，适合实验。

四简模式说明：

- `safe`：不压原生四码位，只给没有原生四码冲突的 GB 五码字发四简。
- `balanced`：启用四简时的默认模式。可压低频原生四码位，但候选五码字需要明显高频，或原主已有更短简码。
- `aggressive`：GB 五码字全量截四码，保留更多覆盖，但更容易制造候选压力。

四简启用时只让 GB2312 一级字直接进入；GB2312 二级字需要达到 `--s4-level2-min-score` 门槛，避免大量冷僻二级字挤入四简层。

## 3. 生成 Sicang5

Sicang5 支持与 Wucang5 相同的二简/三简参数化配置，但不包含四简层。

```powershell
python scripts/cangjie/gen_sicang5.py
```

## 4. 技术规范

详见 [CANGJIE_SPEC.md](CANGJIE_SPEC.md) 了解详细的设计算法与取码规则。
