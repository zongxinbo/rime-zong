# 仓颉方案生成系统

本目录用于管理 Sicang5/Wucang5 方案的生成与简码设计。

## 1. 设计简码原型

核心脚本会读取仓颉五码源表与加权字频，生成 `prototypes/` 下的简码原型文件。

```powershell
python scripts/cangjie/core/gen_shortcut_1.py --weights sc
# 盲测：不让当前人工定稿影响候选保底或主推荐排序，并避免覆盖常规报告
python scripts/cangjie/core/gen_shortcut_1.py --weights sc --blind --output _tmp/one_code_report_blind.md
python scripts/cangjie/core/gen_shortcut_2.py
python scripts/cangjie/core/gen_shortcut_3.py
python scripts/cangjie/core/gen_shortcut_4.py
```

简体/通用一简与繁体专精一简分表维护：`one_code.txt` 服务当前通用方案；需要繁体专精时生成并人工定稿 `one_code_tc.txt`，构建繁体方案时替换主一简层。`z?`、`x?` 不承载繁体高频补位；默认由自动前缀层按频率和重码痛点生成。

人工复核固定简码时，使用真实后续分层重放脚本计算净码长收益：

```powershell
# 一简替换
python scripts/cangjie/core/shortcut_gain.py --layer one --code t --char 其 --weights sc

# z?/x? 固定二码新增或替换
python scripts/cangjie/core/shortcut_gain.py --layer fixed-prefix --code xp --char 恐 --weights sc_daily
```

`gen_shortcut_1.py` 先静态初筛，再调用 `shortcut_gain.py` 核心重放真实 S2/S3。单独使用 `shortcut_gain.py` 时，可评估 one 或 fixed-prefix 层的替换收益；生产构建默认不加载 fixed-prefix。详细算法见 [CANGJIE_SPEC.md](CANGJIE_SPEC.md) 9.3。

`gen_shortcut_1.py` 默认每键重放静态 Top 8。需要扩大深扫范围时使用 `--gain-candidates-per-key`，耗时近似线性增长。

`a-z` 一简的静态排序只使用日常字频和记忆锚点，不加入码长、重码或前缀占位救援权重。`x/z` 没有普通仓颉锚点，使用 `--append-xz` 追加时按日常字频生成全局候选。真实 S2/S3 重放仍用于展示副作用和排除负收益替换；普通二三四简和自动消重层保留重码救援评分。

`gen_shortcut_1.py --blind` 用于执行无人工定稿偏置的逐键替换审计。盲测仍以当前正式版计算替换净收益并输出对照，但不会把当前字强制塞入静态短名单；若当前字凭自身频率和锚点自然入围，则以收益 `0` 的基线正常参与排序。它不是从空白状态独立生成完整一简方案。建议配合 `--output` 写入单独报告。

默认权重分工：

- 普通一简审阅：`gen_shortcut_1.py --weights sc`，对标现代简体日用一简。
- 生产二简、三简、全码排序、后缀救援：`gen_sicang5.py` / `gen_wucang5.py --weights sc_daily`。
- 生产四简：默认关闭；显式 `--s4` 开启后同样使用主构建 `--weights`，默认 `sc_daily`。
- 自动前缀：独立于主构建 `--weights`；二码前缀默认 `sc`，三码及更深层默认 `sc_daily`。
- `sc_balanced` 是简繁 60/40 的实验口径，需要显式传入。

`SC_FREQ_WEIGHTS` 使用现代简体日用语料共识自动优化。重算比例：

```powershell
python scripts/cangjie/core/optimize_sc_weights.py
```

脚本将口语、字幕、知乎和北语字频各自归一化后等权作为目标，以平均 Jensen-Shannon 距离最小化搜索混合比例。`Essay` 可参与候选混合，但当前最优解会将其剔除为零权重。

同一 Unicode 字可能因地区字形存在多个仓颉码。生成大陆字形首选码表时，全部以教育大学汉语多功能字库中带 `GBK` 的字形记录为准；`data/cj5-90000.txt` 不再作为离线交集来源：

```powershell
# 每次最多查询 150 个剩余歧义字；换 VPN 节点后重复运行
python scripts/cangjie/core/fetch_sc_glyph_preferred_codes.py --workers 2 --delay 1 --limit 150

# 只整理 sc_glyph_preferred_code.txt 顺序，不读取码表、不合并缓存、不访问网络
python scripts/cangjie/core/fetch_sc_glyph_preferred_codes.py --sort-by-code

# 人工确认 sc_glyph_manual_preferred_code.txt 后反填 cache，并刷新 preferred/unresolved；不访问网络
python scripts/cangjie/core/fetch_sc_glyph_preferred_codes.py --backfill-from-preferred

# 只重查当前 unresolved 中的字，会先删除这些字的旧 cache
python scripts/cangjie/core/fetch_sc_glyph_preferred_codes.py --refetch-unresolved

# 小批量验证
python scripts/cangjie/core/fetch_sc_glyph_preferred_codes.py --chars 着,的,真 --limit 3
```

脚本仅处理 GBK 范围内的一字多普通码汉字，并排除最终结果中的 `x/z` 前缀编码。脚本通过系统 `curl` 请求字库页面；在线结果优先采用唯一 GBK 普通码；若 GBK 字形块的键盘字母为 `x/xx...` 前缀且页面给出 `五倉重碼`，则优先用 `五倉重碼` 命中源码候选；否则再尝试去掉前缀后直接命中源码候选，或将其唯一展开为以该缩略码开头的源码候选。在线缓存位于 `data/chidic_glyph_cache.json`，每字落盘；空页面不会视为成功缓存。仍无法唯一判断的字会写入 `data/sc_glyph_unresolved_code.txt`，供人工确认。`--refetch-unresolved` 只重查当前未决文件中的字，并先删除这些字的旧 cache。`--backfill-from-preferred` 会把人工维护的 `data/sc_glyph_manual_preferred_code.txt` 反填进 cache，并重算 `sc_glyph_preferred_code.txt` 和 `sc_glyph_unresolved_code.txt`；该操作不访问网络。`--sort-by-code` 是独立的纯排序操作，只整理 `sc_glyph_preferred_code.txt`，不会读取码表、合并缓存或访问网络。

所有简码生成器和 `shortcut_gain.py` 会按 `--weights` 模式名选择字形首选表：模式名包含 `sc` 时使用 `data/sc_glyph_preferred_code.txt`，否则模式名包含 `tc` 时使用 `data/tc_glyph_preferred_code.txt`。例如 `sc_balanced` 仍按 `sc` 大陆字形处理。首选表尚不存在时按空表处理。最终字典仍保留兼容全码，但自动消重码只从过滤后的地区字形视图派生。

## 2. 生成 Wucang5

默认构建参数：

- 二简：上限 `300` 个；默认保护高频 GBK 原生二码位，综合字频门槛 `3000`
- 三简：固定 `800` 个；默认保护高频 GBK 原生三码位，综合字频门槛 `3000`
- 二简、三简候选池按 Rime 默认 `extended_charset=常用` 状态过滤；长码候选也需达到综合字频门槛才可入选
- 四简：默认关闭，可用 `--s4` 开启 `balanced` 模式，给 GB2312 五码字生成四简
- 四简数量：启用后默认上限 `1000` 个；GB2312 二级字需达到综合字频 `1000` 才可进入
- 一简：单独运行 `core/gen_shortcut_1.py` 生成校准表；生产构建只消费 `one_code.txt`，不自动重算
- 普通层权重：一简审阅默认 `sc`；生产构建默认 `--weights sc_daily`，用于二简、三简、全码排序、后缀救援，并在启用四简时用于四简
- 简码总量：builder 口径含 `z_code` 字根码 31 个、一简 25 个、二简 300 个、三简 800 个，默认合计 `1156` 个
- 字根字：未被一简校准表选中的字根字不保留原生一简入口，统一经 `az/azz` 等 `z_code` 字根码输入
- 全码排序：默认不启用普通简码让位；开启 `--fullcode-yield` 后，常用且无普通简码的全码字优先，同组内仍按综合字频排序；`z/x` 救援不触发让位
- 前缀选重：Sicang5/Wucang5 默认共享 `z?/x?`、`z??/x??` 高频前缀短码；所有 `z/x` 前缀均按候选位固定映射，第 2 候选用 `z`，第 3 候选用 `x`；Sicang5 用 `z???/x???` 处理四码第 2/3 候选，Wucang5 用 `z???/x???` 生成四码前缀短码，并预留 `z????/x????` 五码第 2/3 候选救援；二码前缀对标一简用 `sc`，三码及更深层前缀用 `sc_daily`
- 后缀选重：前缀层生成后再兜底；Sicang5/Wucang5 默认第 2 候选补 `z`、第 3 候选补 `x`；Sicang5 处理源码长度 `<= 3`，Wucang5 处理源码长度 `<= 4`

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

# 开启出简让全，并调整全码简码让位的顶位门槛
python scripts/cangjie/gen_wucang5.py --fullcode-yield --fullcode-yield-min-score 1000

# 关闭或开启 z/x 后缀直达
python scripts/cangjie/gen_wucang5.py --no-suffix-z
python scripts/cangjie/gen_sicang5.py --no-suffix-z

# 调整 Sicang5 短码 z/x 后缀：第 2 候选补 z、第 3 候选补 x，且只处理源码长度 <= 3
python scripts/cangjie/gen_sicang5.py --suffix-z-ranks 2:z,3:x --suffix-z-max-source-length 3

# 调整 z/x 后缀候选字集和目标码占用策略
python scripts/cangjie/gen_sicang5.py --suffix-z-charset frequency --suffix-z-occupied-policy ignore-nonfrequency-or-shortcut

# 关闭或开启自动 z/x 前缀层
python scripts/cangjie/gen_sicang5.py --no-dedup-prefix
python scripts/cangjie/gen_wucang5.py --no-dedup-prefix

# 只开启前缀短码或只开启四码前缀选重
python scripts/cangjie/gen_sicang5.py --dedup-prefix --dedup-prefix-short --no-dedup-prefix-full
python scripts/cangjie/gen_sicang5.py --dedup-prefix --no-dedup-prefix-short --dedup-prefix-full

# 显式加载旧 fixed_prefix_code.txt 补丁层
python scripts/cangjie/gen_sicang5.py --fixed-prefix

# 调整 z/x 前缀候选字集和最低综合字频
python scripts/cangjie/gen_sicang5.py --dedup-prefix-charset gbk --dedup-prefix-min-score 1
```

`--protect-native-charset` 支持：

- `gbk`：默认值，保护 GBK 可编码字符，兼顾常见繁简字。
- `gb2312`：仅保护 GB2312 汉字。
- `frequency`：仅保护当前综合字频中出现的字。
- `all`：不限制汉字范围，适合实验。

`z/x` 后缀参数：

- `--suffix-z-ranks`：候选位和后缀映射，格式如 `2:z,3:x`。
- `--suffix-z-max-source-length`：只处理不超过该长度的源码；Sicang5 默认 `3`，Wucang5 默认 `4`。
- `--suffix-z-charset`：候选字集，支持 `frequency`、`gbk`、`gb2312`、`all`。
- `--suffix-z-min-score`：候选最低综合字频。
- `--suffix-z-occupied-policy`：`strict` 为任意占用即跳过；`ignore-nonfrequency-or-shortcut` 会忽略字集外或已有普通简码的目标码占用。

自动 `z/x` 前缀层：

- 前缀短码层先生成：所有 `z/x` 前缀均按全码候选位固定映射，第 2 候选只尝试 `z`，第 3 候选只尝试 `x`，第 4 候选及以后不分配前缀码；二键按首码 > 末码尝试主体键，三键使用原码前两码，四键短前缀使用原码前三码。
- 二键前缀按全局高频重码痛点竞争，不要求节省码长；三键前缀按高频痛点并适度奖励节省码长。
- 前缀短码候选源只看普通简码和全码让位后的自然源，不包含后缀救援码；源长规则按前缀码总长 `L` 取自然源长 `>= L`。
- 共享层只包含二码和三码前缀；四码及以上按方案独立生成。
- Sicang5 四码前缀选重层：四码第 2 候选用 `z前三`，第 3 候选用 `x前三`。
- Wucang5 四码前缀短码层：第 2 候选用 `z前三`，第 3 候选用 `x前三`；Wucang5 五码前缀选重层：五码第 2 候选用 `z前四`，第 3 候选用 `x前四`。
- 已获得更短前缀码的字不再参与后续前缀层。
- 不扫描任意空位，只使用可从原码推导的前缀码。
- 构建时会覆盖生成共享的 `prototypes/prefix_code_2.txt`、`prefix_code_3.txt`，方案专属的 `prefix_code_4_sicang5.txt`、`prefix_code_4_wucang5.txt`、`prefix_code_5_wucang5.txt`，以及后缀审阅文件 `suffix_code_sicang5.txt`、`suffix_code_wucang5.txt`；这些文件不是人工输入源。

`--dedup-prefix-charset` 支持：

- `frequency`：默认值，仅处理当前综合字频中出现的字。
- `gbk`：处理 GBK 可编码字符，兼顾常见繁简字。
- `gb2312`：仅处理 GB2312 汉字。
- `all`：不限制汉字范围，适合实验。

前缀层常用参数：

- `--dedup-prefix-short-levels`：前缀短码层级，默认 `2,3`。
- `--dedup-prefix-full-source-length`：四码前缀选重处理的源码长度，默认 `4`。
- `--dedup-prefix-deep-rank-multiplier`：第 3 候选进入前缀短码层时的痛点倍率，默认 `1.5`。
- `--dedup-prefix-source-max-code-length`：前缀生成使用的投影基线码长，默认 `4`，保证 Sicang5/Wucang5 前缀码一致。
- `--dedup-prefix-level2-weights`：二码前缀权重，默认 `sc`。
- `--dedup-prefix-level3-weights`：三码前缀权重，默认 `sc_daily`。
- `--dedup-prefix-full-weights`：四码及更深层前缀权重，默认 `sc_daily`。

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
