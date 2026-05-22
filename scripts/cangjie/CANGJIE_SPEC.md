# 仓颉方案技术规范

本文档记录 Sicang5/Wucang5 的生成逻辑、简码分层策略与当前默认参数。

## 1. 任务背景

仓颉系列方案的目标是在保留仓颉五代取码直觉的前提下，用现代语料做高频优先排序与简码分配。Wucang5 是五码单字流方案；Sicang5 是四码单字流方案。

## 2. 核心数据源

- **Dialogue 口语语料**：`schemas/common/frequency/char/sc/dialogue_char_freq.txt`，权重 6
- **Subtlex 字幕语料**：`schemas/common/frequency/char/sc/subtlex_char_freq.txt`，权重 5
- **知乎语料**：`schemas/common/frequency/char/sc/zhihu_char_freq.txt`，权重 4
- **北语大语料**：`schemas/common/frequency/char/sc/blcu_char_freq.txt`，权重 2
- **Essay 语料**：`schemas/common/essay-zh-hans.txt`，权重 1

所有构建脚本通过 `cangjie_builder.get_weighted_frequencies()` 共享同一套加权字频，保证简码选择与最终字典排序使用同一份综合分。

## 3. 核心脚本

| 脚本 | 职能 |
| :--- | :--- |
| `core/gen_shortcut_1.py` | 一简方案分析与生成 |
| `core/gen_shortcut_2.py` | 二简生成，支持固定数量、覆盖率、GB2312 保护 |
| `core/gen_shortcut_3.py` | 三简生成，支持固定数量、覆盖率、GB2312 保护 |
| `core/gen_shortcut_4.py` | 四简生成，支持 `safe` / `balanced` / `aggressive` |
| `core/cangjie_builder.py` | 最终字典构建、排序与后缀消重 |
| `gen_wucang5.py` | Wucang5 一键构建入口 |
| `gen_sicang5.py` | Sicang5 一键构建入口 |

## 4. 简码原型文件

- 一简：`scripts/cangjie/prototypes/one_code.txt`
- 二简：`scripts/cangjie/prototypes/two_code.txt`
- 三简：`scripts/cangjie/prototypes/three_code.txt`
- 四简：`scripts/cangjie/prototypes/four_code.txt`（启用 `--s4` 时生成）
- z 补丁：`scripts/cangjie/prototypes/z_code.txt`

## 5. Wucang5 默认构建

默认命令：

```powershell
python scripts/cangjie/gen_wucang5.py
```

当前默认参数：

- `--s2-count 150`
- `--s3-count 300`
- `--s2-coverage 0`
- `--s3-coverage 0`
- `--no-s4`（默认关闭；可用 `--s4` 开启）
- `--s4-mode balanced`
- `--s4-count 1000`
- `--s4-level2-min-score 1000`

含义：

- 二简、三简默认按固定数量生成；只有当 `--s2-count 0` 或 `--s3-count 0` 时，对应覆盖率参数才参与控量。
- 二简默认取全码前两码，三简默认取全码前三码。
- 四简默认关闭；需要实验四简时显式传入 `--s4`。
- 四简启用时只处理 GB2312 一级字和达到频率门槛的 GB2312 二级字，不把全 CJK 字集压入四码层。
- 四简启用时默认上限 1000 个；`--s4-count 0` 表示不做数量截断，由四简模式自身过滤规则决定数量。
- GB2312 二级字启用四简时默认需要综合字频达到 1000；`--s4-level2-min-score 0` 表示不过滤二级字。

常用命令：

```powershell
# 开启四简
python scripts/cangjie/gen_wucang5.py --s4

# 四简安全版
python scripts/cangjie/gen_wucang5.py --s4 --s4-mode safe

# 四简平衡版，启用四简时默认
python scripts/cangjie/gen_wucang5.py --s4 --s4-mode balanced

# 四简激进版
python scripts/cangjie/gen_wucang5.py --s4 --s4-mode aggressive

# 固定四简数量
python scripts/cangjie/gen_wucang5.py --s4 --s4-count 1000

# 调整 GB2312 二级字进入四简的门槛
python scripts/cangjie/gen_wucang5.py --s4 --s4-level2-min-score 1000

# 覆盖率控量
python scripts/cangjie/gen_wucang5.py --s2-count 0 --s2-coverage 0.85 --s3-count 0 --s3-coverage 0.90
```

## 6. 简码分层策略

### 6.1 一简与 z 补丁

一简和 z 补丁由原型文件直接提供，构建时作为最高优先级简码层参与排序。

### 6.2 二简

二简候选来自全码长度大于 2 的字：

- 默认取码：`full_code[:2]`
- 可选取码：首尾码
- 默认模式：保护高频 GB2312 原生二码位，长码字可与其他原生二码位竞争
- 保护门槛：`--s2-protect-native-min-score`，默认综合字频 `100000`
- `--no-protect-native`：允许长码字与原生二码字竞争，长码字频次需超过原主 `1.5x`
- `--gb-only` 模式：仅 GB2312 字有资格，且 GB2312 原生二码位绝对保护

### 6.3 三简

三简候选来自全码长度大于 3、且未获得更短简码的字：

- 默认取码：`full_code[:3]`
- 可选取码：前两码 + 末码
- 默认模式：保护原生三码位，长码字只占空槽，不抢已有三码全码字
- `--no-protect-native`：允许长码字与原生三码字竞争，长码字频次需超过原主 `1.2x`
- `--gb-only` 模式：仅 GB2312 字有资格，且 GB2312 原生三码位绝对保护

### 6.4 四简

四简候选来自 GB2312、五码、且未获得 z/一简/二简/三简的字：

- 取码：`full_code[:4]`
- 启用后默认模式：`balanced`
- 默认关闭；开启方式：`--s4`
- 字集门槛：GB2312 一级字直接参与；GB2312 二级字需达到 `--s4-level2-min-score`

四简模式：

- `safe`：不压原生四码位，只接受没有原生四码冲突的候选。
- `balanced`：默认模式。若冲突原主已经有更短简码则放行；否则候选综合频次需超过活跃原主 `3.0x`。
- `aggressive`：GB 五码字全量截四码，保留内部重复，覆盖最大但候选压力也最大。

在 `safe` 与 `balanced` 下，四简会做码位去重与同字去重：每个四码位只保留一个最高价值字，同一个字也只保留一个四简。

## 7. 字典排序

最终字典使用纯 `字\t码` 格式，不写 weight。候选优先级依赖文件内排序：

1. 简码条目：`z` / 一简 / 二简 / 三简 / 四简（启用时）
2. 全码条目：同码内按综合字频降序
3. 后缀消重条目：自动追加的 `z` 后缀码

这个排序保证简码在自身码位上拥有绝对首选，同时不再因为某字已有简码而降低它的全码候选位置。

## 8. 后缀消重

`cangjie_builder.py` 会在构建末尾为第二候选生成 `z` 后缀退路：

- 第二候选：`原码 + z`
- 总码长不超过当前方案最大码长时才生成
- 若后缀码已被简码占用则跳过
- 原始 `z*` 符号和兼容汉字分区默认不纳入 Sicang5/Wucang5；常用字根入口由 `z_code` 明确维护

这层逻辑主要降低全码模式下的选重压力，不改变简码优先级。

## 9. 当前默认构建样例

基于 2026-05-22 当前默认命令：

```powershell
python scripts/cangjie/gen_wucang5.py
```

生成日志样例：

| 项目 | 数量 |
| :--- | ---: |
| z 字根码 | 31 |
| 一简 | 25 |
| 二简 | 150 |
| 三简 | 300 |
| 四简 | 0 |
| 最终简码条目 | 506 |
| 最终全码条目 | 107263 |
| 后缀消重条目 | 11347 |
| 总条目 | 119116 |

`最终简码条目` 使用 builder 口径，包含 `z_code` 字根码、一简、二简、三简：`31 + 25 + 150 + 300 = 506`。

当前 `summary.py` 摘要：

| 语料 | 频率降序-全码 | 频率降序-简码 | 原始码表-全码 | 原始码表-简码 | 简全联用-实际 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 知乎简体 | 6.84‱ | 294.63‱ | 7.21‱ | 308.99‱ | 7.21‱ |
| 北语简体 | 5.60‱ | 345.41‱ | 5.64‱ | 357.92‱ | 5.64‱ |
| 台标繁体 | 2.28‱ | 235.24‱ | 22.90‱ | 491.43‱ | 21.71‱ |
| 古籍繁体 | 4.97‱ | 237.63‱ | 21.65‱ | 688.17‱ | 20.43‱ |
| 繁简联合 | 10.13‱ | 310.21‱ | 19.05‱ | 376.47‱ | 18.23‱ |

注意：默认保护原生码位且不再全码退避后，`原始码表-全码` 已接近全码理论水平；真实打字体验仍优先看 `简全联用-实际`。

## 10. Sicang5

Sicang5 使用与 Wucang5 相同的二简/三简生成参数，但不包含四简层：

```powershell
python scripts/cangjie/gen_sicang5.py
```

当前默认日志样例：

| 项目 | 数量 |
| :--- | ---: |
| 最终简码条目 | 506 |
| 最终全码条目 | 106214 |
| 后缀消重条目 | 3024 |
| 总条目 | 109744 |

当前 `summary.py` 实际选重率：

| 语料 | 简全联用-实际 |
| :--- | ---: |
| 知乎简体 | 25.55‱ |
| 北语简体 | 27.85‱ |
| 台标繁体 | 170.24‱ |
| 古籍繁体 | 211.89‱ |
| 繁简联合 | 127.90‱ |

## 11. 词组取码动态配额

Sicang5 语句流采用动态配额算法，根据单字码长分配 4 码位。

| 词长 | 结构配额 | 取码明细 | 示例 |
| :--- | :--- | :--- | :--- |
| 二字词 | 2 + 2 | A首+A尾 + B首+B尾 | 实际 -> pmnf |
| 二字词 | 1 + 3 | A首 + B首+B次+B尾 | 中国 -> lwim |
| 二字词 | 2 + 1 | A首+A尾 + B首 | 某个 -> mwg |
| 三字词 | 2 + 1 + 1 | A首+A尾 + B首 + C尾 | 实际上 -> pmnm |
| 三字词 | 1 + 2 + 1 | A首 + B首+B尾 + C尾 | 输入法 -> johy |
| 三字词 | 1 + 1 + 2 | A首 + B首 + C首+C尾 | 这种人 -> yhoo |
| 四字词+ | 1 + 1 + 1 + 1 | A首 + B首 + C首 + Z首 | 社会保障 -> ioof |

原则：遵循仓颉五代顺位，动态消除同字内冗余码，首字不超过 2 码。

## 12. 评估命令

```powershell
python scripts/assess/summary.py --dict schemas/cangjie/wucang5/wucang5.dict.yaml
```

项目根目录运行脚本，确保 `REPO_ROOT` 能正确定位源表、原型文件与频率数据。
