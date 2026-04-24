# rime-zong

Rime 方案集合，包含拼音、仓颉、三码仓颉、郑码、四角号码和日语罗马字输入。

当前默认启用：

| Schema | 名称 |
| --- | --- |
| [`pinyin_ice_cangjie5`](pinyin_ice/pinyin_ice_cangjie5.schema.yaml) | 雾凇拼音·倉頡 |
| [`cangjie5_ice`](cangjie5/cangjie5_ice.schema.yaml) | 倉頡五代·雾凇 |
| [`jaroomaji`](jaroomaji/jaroomaji.schema.yaml) | 日本語 |

## 方案说明

依赖列主要对应各 schema 中的 `dependencies`；若方案还调用 Lua 组件，也一并列出。它们主要用于反查、混合输入或辅助码过滤。完整文件级依赖见 [`scheme_dependencies.yaml`](scheme_dependencies.yaml)。

| Schema | 名称 | 依赖 | 特点与操作 |
| --- | --- | --- | --- |
| [`pinyin_simp`](pinyin_simp/pinyin_simp.schema.yaml) | 拼音 | `cangjie5` | [袖珍简化字拼音](https://github.com/rime/rime-pinyin-simp)，轻量拼音方案。正常拼音输入，输入 `` `仓颉码 `` 可用仓颉五代反查。 |
| [`pinyin_ice`](pinyin_ice/pinyin_ice.schema.yaml) | 雾凇拼音 | `cangjie5` | [雾凇拼音](https://github.com/iDvel/rime-ice) 精简版，保留雾凇词库、用户短语、简繁转换。正常拼音输入，输入 `` `仓颉码 `` 可用仓颉五代反查。 |
| [`pinyin_ice_cangjie5`](pinyin_ice/pinyin_ice_cangjie5.schema.yaml) | 雾凇拼音·倉頡 | `cangjie5`、[`lua/aux_code_filter.lua`](lua/aux_code_filter.lua) | 默认启用。雾凇拼音主输入，仓颉五代作辅助码。拼音后输入 `;` 或 `,` 接仓颉辅码过滤候选，例如 `ni;ab`；单字取仓颉首尾码，词语取首字首码 + 末字首码；输入 `` `仓颉码 `` 使用完整仓颉反查。 |
| [`cangjie5`](cangjie5/cangjie5.schema.yaml) | 倉頡五代 | `pinyin_simp` | [倉頡五代](https://github.com/Jackchows/Cangjie5) 单字方案，简化字优先。不造词、不学习，五码不自动上屏；空格有候选时上屏、无匹配时清码；`Tab` 清码；输入 `` `拼音 `` 可拼音反查。 |
| [`sancang5`](sancang5/sancang5.schema.yaml) | 三码仓颉·五代 | `pinyin_simp` | 仓颉五代码表投影生成的三码仓颉。单字一至三码保留原码，四码及以上取首码、次码、末码；支持拼音反查、扩展字符集、简繁转换和八股文简化字语法模型；输入 `` `拼音 `` 可拼音反查。 |
| [`cangjie5_pinyin`](cangjie5/cangjie5_pinyin.schema.yaml) | 倉頡五代·拼音 | `pinyin_simp` | 仓颉五代 + 袖珍简化字拼音混合输入。仓颉候选保持单字，拼音候选可出词；输入 `` `拼音 `` 可拼音反查。 |
| [`cangjie5_ice`](cangjie5/cangjie5_ice.schema.yaml) | 倉頡五代·雾凇 | `pinyin_ice` | 默认启用。仓颉五代 + 雾凇拼音混合输入。仓颉码和雾凇拼音都可参与候选，适合以仓颉为主、雾凇拼音补词；输入 `` `拼音 `` 使用雾凇拼音反查。 |
| [`jaroomaji`](jaroomaji/jaroomaji.schema.yaml) | 日本語 | `cangjie5`, `pinyin_simp` | 默认启用。[日本語罗马字](https://github.com/lazyfoxchan/rime-jaroomaji) 输入，支持平假名、片假名、日文符号。`-`、`l`、`L` 输入长音符号「ー」；按住 `Shift` 输出片假名；输入 `` `仓颉码 `` 可仓颉反查，输入 `` `P拼音 `` 可拼音反查。 |
| [`zmcdzc`](zmcdzc/zmcdzc.schema.yaml) | 郑码 | `pinyin_simp` | 郑码超大字词。四码自动上屏，支持拼音反查、扩展字符集和简繁转换；`;` / `'` 可选第 2 / 第 3 候选；输入 `` `拼音 `` 可拼音反查。 |
| [`lyzm`](lyzm/lyzm.schema.yaml) | 龙渊郑码 | `pinyin_simp` | 龙渊郑码。四码自动上屏，关闭用户词典和自动造句；输入 `` `拼音 `` 可拼音反查。 |
| [`sijiao`](sijiao/sijiao.schema.yaml) | 四角号码 | `pinyin_simp` | 四角号码 27585 字。输入 5 位数字编码，支持小键盘数字；候选键为 `Space` / `a` / `s` / `d` / `f`，翻页为 `w` / `e`；输入 `` `拼音 `` 可拼音反查。 |

## 依赖清单

完整、可机器读取的文件级依赖由 [`scheme_dependencies.yaml`](scheme_dependencies.yaml) 生成并维护，包含 schema、dict、词频文件、语法模型、OpenCC、Lua、符号预设和外部预设。下面是人工阅读用摘要：

| Schema | 文件级依赖摘要 |
| --- | --- |
| `pinyin_simp` | `pinyin_simp` schema/dict；`cangjie5` schema/dict/custom；`symbols.yaml`；OpenCC `s2t.json` 及 `STPhrases.ocd2`、`STCharacters.ocd2`；外部预设 `default`、词语模型 `essay`。 |
| `pinyin_ice` | `pinyin_ice` schema/custom 和 `pinyin_ice.*.dict.yaml`；`cangjie5`、`pinyin_simp` 相关 schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `pinyin_ice_cangjie5` | `pinyin_ice_cangjie5` schema；`pinyin_ice` dict；`cangjie5`、`pinyin_simp` 相关 schema/dict；[`lua/aux_code_filter.lua`](lua/aux_code_filter.lua)；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `cangjie5` | `cangjie5` schema/dict/custom；`pinyin_simp` schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `cangjie5_pinyin` | `cangjie5_pinyin` schema；`cangjie5` schema/dict/custom；`pinyin_simp` schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `cangjie5_ice` | `cangjie5_ice` schema；`cangjie5` schema/dict/custom；`pinyin_ice` schema/custom/dict；`pinyin_simp` schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `sancang5` | `sancang5` schema/dict；`pinyin_simp` 与 `cangjie5` 反查相关 schema/dict；`sancang5/essay-zh-hans.txt`；`sancang5/grammar.yaml`；`sancang5/zh-hans-t-essay-bgw.gram`；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `jaroomaji` | `jaroomaji` schema 和 `jaroomaji.*.dict.yaml`；`cangjie5`、`pinyin_simp` 反查相关 schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `zmcdzc` | `zmcdzc` schema/dict；`pinyin_simp` 与 `cangjie5` 反查相关 schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `lyzm` | `lyzm` schema/dict/custom；`pinyin_simp` 与 `cangjie5` 反查相关 schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |
| `sijiao` | `sijiao` schema/dict；`pinyin_simp` 与 `cangjie5` 反查相关 schema/dict；`symbols.yaml`；OpenCC `s2t.json` 及简繁词典；外部预设 `default`、词语模型 `essay`。 |

说明：`default` 和未随仓库提供的 `essay` 是 Rime 平台或发行包常见资源；仓库内可拷贝文件以 `scheme_dependencies.yaml` 的 `files` 为准。

## 共用资源

| 资源 | 用途 |
| --- | --- |
| [`opencc`](opencc) | 简繁转换配置和词典。 |
| [`symbols.yaml`](symbols.yaml) | 符号输入预设。 |
| [`lua/aux_code_filter.lua`](lua/aux_code_filter.lua) | 通用辅助码过滤器，目前用于 `pinyin_ice_cangjie5`。 |

## 平台配置

| 文件 | 用途 |
| --- | --- |
| [`default.yaml`](default.yaml) | 桌面/通用默认配置。 |
| [`default.custom.yaml`](default.custom.yaml) | 移动端覆盖配置，目前用于移动端软键盘通过 `backslash` 快速切换到下一个方案。 |

## 脚本

| 脚本 | 用途 |
| --- | --- |
| [`scripts/gen_sancang5.py`](scripts/gen_sancang5.py) | 从仓颉五代码表生成三码仓颉五代码表，可选生成带词语的便携码表。 |
| [`scripts/scheme_dependencies.py`](scripts/scheme_dependencies.py) | 扫描正式方案并生成 [`scheme_dependencies.yaml`](scheme_dependencies.yaml)。 |
| [`scripts/copy_scheme_dependencies.py`](scripts/copy_scheme_dependencies.py) | 按一个或多个 `schema_id` 拷贝依赖到 `_output` 或指定下划线目录。 |

详细参数见 [`scripts/README.md`](scripts/README.md)。

## 通用按键

以下按键来自 `default.yaml` 引入的 Rime 默认按键预设。个别 schema 会覆盖局部行为，以上方“方案说明”为准。

| 按键 | 功能 |
| --- | --- |
| `F4` | 打开方案选单。 |
| `Control+Shift+Space` / `Control+Shift+1` | 切换到下一个方案。 |
| `backslash` | 在移动端配置中切换到下一个方案。 |
| `Shift+Space` / `Control+Shift+2` | 切换中西文模式。 |
| `Control+comma` / `Control+Shift+3` | 切换全角/半角。 |
| `Control+period` | 切换中西文标点。 |
| `Control+slash` / `Control+Shift+4` | 切换简繁相关选项。 |
| `Control+backslash` / `Control+Shift+5` | 切换扩展字符集。 |
| `minus` / `equal` | 候选翻页。 |
| `comma` / `period` | 候选翻页。 |
| `Control+p` / `Control+n` | 上下移动候选或光标。 |
| `Control+b` / `Control+f` | 左右移动光标。 |
| `Control+a` / `Control+e` | 移动到编码开头/结尾。 |
| `Control+d` / `Control+h` | 删除或退格。 |
| `Control+g` / `Control+bracketleft` | 取消当前输入。 |
| `Left Shift` | 提交当前编码并切换到西文模式。 |
| `Right Shift` | 提交当前文字并切换到西文模式。 |
| `Caps Lock` | 清码并切换到西文模式。 |
