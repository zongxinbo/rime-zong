# 仓颉方案技术规范 (CANGJIE_SPEC)

本文档记录了仓颉系列方案的设计逻辑、自动化调优算法以及核心架构原则。

## 1. 任务背景
优化仓颉系列方案（Sicang5/Wucang5）的简码分配方案，目标是利用现代语料库实现“高频优先”与“编码直觉”的平衡。

## 2. 核心数据源
- **Dialogue 口语语料 (`frequency/char/dialogue_char_freq.txt`)**：核心口语字频（源自北语大语料库加工），确保高频对话词汇优先。
- **Subtlex 影视字幕语料 (`frequency/char/subtlex_char_freq.txt`)**：基于影视字幕的日常频次，反映口语视听习惯，覆盖常用生活用语。
- **知乎语料 (`frequency/char/zhihu_char_freq.txt`)**：现代网络常用语料，提供更具时代感的频次分布。
- **北语大语料 (`frequency/char/blcu_char_freq.txt`)**：超大规模平衡语料库，提供基础字频基底。
- **Essay 语料 (`frequency/word/essay-zh-hans.txt`)**：传统 Rime 基础语料库。

## 3. 自动化分析工具
| 脚本名称 | 职能 | 位置 |
| :--- | :--- | :--- |
| **gen_shortcut_1.py** | 一简方案分析与生成 | `scripts/cangjie/core/` |
| **gen_shortcut_2.py** | 二简方案设计稿生成 | `scripts/cangjie/core/` |
| **gen_shortcut_3.py** | 三简方案设计稿生成 | `scripts/cangjie/core/` |
| **cangjie_builder.py** | 核心构建引擎 | `scripts/cangjie/core/` |

## 3. 简码设计稿位置
- **一简**：`scripts/cangjie/prototypes/one_code.txt`
- **二简**：`scripts/cangjie/prototypes/two_code.txt`
- **三简**：`scripts/cangjie/prototypes/three_code.txt`
- **z 补丁**：`scripts/cangjie/prototypes/z_code.txt`

## 4. 词组取码动态配额规则 (Dynamic Quota Logic)
Sicang5 采用动态配额算法，根据单字码长动态分配 4 码位。

| 词长 | 结构配额 | 取码明细 | 典型示例 |
| :--- | :--- | :--- | :--- |
| **二字词** | 2 + 2 | A首+A尾 + B首+B尾 | 实际 (pkhm + nlf) -> pmnf |
| | 1 + 3 | A首 + B首+B次+B尾 | 中国 (l + wirm) -> lwim |
| | 2 + 1 | A首+A尾 + B首 | 某个 (mow + g) -> mwg |
| **三字词** | 2 + 1 + 1 | A首+A尾 + B首 + C尾 | 实际上 (pkhm + nlf + ym) -> pmnm |
| | 1 + 2 + 1 | A首 + B首+B尾 + C尾 | 输入法 (jokon + oh + eiy) -> johy |
| | 1 + 1 + 2 | A首 + B首 + C首+C尾 | 这种人 (ypt + hdyj + o) -> yhoo |
| **四字词+** | 1+1+1+1 | A首 + B首 + C首 + Z首 | 社会保障 (if+omr+ord+fylj) -> ioof |

*原则：遵循仓颉5顺位，动态消除同字内冗余码，首字不超过2码（不反自身）。*

## 5. 环境提示
- 所有脚本均在项目根目录运行。
- 核心引擎：`scripts/cangjie/core/cangjie_builder.py`
