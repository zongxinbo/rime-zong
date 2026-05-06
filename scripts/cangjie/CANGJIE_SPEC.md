# 仓颉方案技术规范 (CANGJIE_SPEC)

本文档记录了仓颉系列方案的设计逻辑、自动化调优算法以及核心架构原则。

## 1. 任务背景
优化仓颉系列方案（Sicang5/Wucang5）的简码分配方案，目标是利用现代语料库实现"高频优先"与"编码直觉"的平衡。

## 2. 核心数据源
- **Dialogue 口语语料 (`schemas/common/frequency/char/sc/dialogue_char_freq.txt`)**：核心口语字频（权重: 6）。
- **Subtlex 影视字幕语料 (`schemas/common/frequency/char/sc/subtlex_char_freq.txt`)**：日常频次（权重: 5）。
- **知乎语料 (`schemas/common/frequency/char/sc/zhihu_char_freq.txt`)**：现代网络常用语料（权重: 4）。
- **北语大语料 (`schemas/common/frequency/char/sc/blcu_char_freq.txt`)**：基础字频基底（权重: 2）。
- **Essay 语料 (`schemas/common/essay-zh-hans.txt`)**：传统 Rime 基础语料（权重: 1）。

所有构建脚本通过 `cangjie_builder.get_weighted_frequencies()` 共享同一套加权算法，确保简码分配与最终字典排序的逻辑一致性。

## 3. 自动化分析工具
| 脚本名称 | 职能 | 位置 |
| :--- | :--- | :--- |
| **gen_shortcut_1.py** | 一简方案分析与生成 | `scripts/cangjie/core/` |
| **gen_shortcut_2.py** | 二简方案生成（支持竞争与 GB2312 保护两种模式） | `scripts/cangjie/core/` |
| **gen_shortcut_3.py** | 三简方案生成（支持竞争与 GB2312 保护两种模式） | `scripts/cangjie/core/` |
| **gen_shortcut_4.py** | 强制四简生成（GB2312 五码字截断） | `scripts/cangjie/core/` |
| **cangjie_builder.py** | 核心构建引擎（位置降权排序） | `scripts/cangjie/core/` |

## 4. 简码设计稿位置
- **一简**：`scripts/cangjie/prototypes/one_code.txt`
- **二简**：`scripts/cangjie/prototypes/two_code.txt`
- **三简**：`scripts/cangjie/prototypes/three_code.txt`
- **四简**：`scripts/cangjie/prototypes/four_code.txt`
- **z 补丁**：`scripts/cangjie/prototypes/z_code.txt`

## 5. 词组取码动态配额规则 (Dynamic Quota Logic)
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

## 6. Wucang5 简码分层策略

### 6.1 生成策略双模说明

Wucang5 支持两种简码生成策略，可通过参数切换：

#### 策略 A：全字符竞争模式 (Default)
- **运行命令**：`python scripts/cangjie/gen_wucang5.py`
- **逻辑**：允许所有汉字参与简码分配。长码字可以与“原主字”（全码长度=N的字）竞争。
- **竞争规则**：长码字频次需超过原主频次一定倍数（二简 1.5x，三简 1.2x）才能抢占位置。
- **默认结果**：二简 ≈ 275 字，三简 ≈ 324 字。默认不生成四简。
- **四简控制**：如需在此模式下开启四简，请添加 `--s4` 参数。

#### 策略 B：GB2312 绝对保护模式
- **运行命令**：`python scripts/cangjie/gen_wucang5.py --gb-only --s2-coverage 1.0 --s3-coverage 1.0`
- **逻辑**：只有 GB2312 汉字有资格获得简码。
- **保护规则**：任何 GB2312 原主位置绝对禁止被抢占（即便对方频次极高）。简码仅占据“空槽”（无 GB2312 原主的编码）。
- **设计目标**：强制所有 GB2312 汉字最短编码 ≤ 4 码。
- **优化结果**：二简 ≈ 286 字，三简 ≈ 2,376 字，四简 ≈ 1,332 字。默认自动开启四简。

### 6.2 核心算法原则 (GB2312 模式)
- **顺位前缀**：所有简码必须是全码的绝对前缀（`code[:N]`）
- **资格门槛**：仅 GB2312 汉字参与
- **繁体字透传**：非 GB2312 字保持原始仓颉五代编码
- **层级排他**：已在短简码层分配的字不参与长简码竞争

### 6.3 后缀消重与候选分配 (Suffix Disambiguation)
Wucang5 引入了自动后缀逻辑来解决高频重码组的选重问题，充分利用空闲的 `z` 和 `x` 键：

1. **第一候选**：保持原码，作为默认首选。
2. **第二候选**：自动生成 `原码 + z`。
3. **第三候选**：自动生成 `原码 + x`。

**规则约束**：
- 仅当添加后缀后的总码长不超过 5 码时生效。
- 若 `原码 + z/x` 已被简码字（如 z_code 字根）占用，则跳过该后缀。
- 该逻辑在 `cangjie_builder.py` 的构建末尾动态执行。

**优化成果**：
- **GB2312 全码冲突**：从原始 425 组下降至 **25 组**。
- **动态选重率 (全码模式)**：降至 **5.05‱** (Zhihu 语料)，实现了接近“盲打”的全码体验。

### 6.4 位置降权 (Positional Demotion)
字典文件使用纯 `字\t码` 格式（无 weight 列），通过文件内条目排列顺序实现"降权退避"。

同一编码下的候选排序规则：
1. **简码条目**（该编码是某字的简码）→ 排最前，按 Z > S1 > S2 > S3 > S4 优先级
2. **原生全码**（该编码是某字的全码，且该字无更短简码）→ 排中间，按字频降序
3. **退避条目**（该编码是某字的全码，但该字已有更短简码）→ 排最后，按字频降序

### 6.5 GB2312 码长分布 (优化后)

| 最短编码长度 | 字数 |
| :--- | :--- |
| 1 码 | 51 字 |
| 2 码 | 608 字 |
| 3 码 | 3,550 字 |
| 4 码 | 2,554 字 |
| **合计** | **6,763 字** |

所有 GB2312 汉字最短编码 ≤ 4 码（已验证）。

### 6.6 动态重码率
- 原版仓颉五代：0.3051%
- 优化后 Wucang5：0.5685%（+0.26%）

动态重码率仅增加 0.26 个百分点，代价极小。绝大多数新增重码发生在低频字上。

## 7. Schema 文件说明
- `wucang5.schema.yaml`：纯单字流方案（推荐）
- `wucang5_fluency.schema.yaml`：语句流方案（使用八股文模型）
- `sicang5.schema.yaml`：四码单字流方案
- `sicang5_fluency.schema.yaml`：四码语句流方案

## 8. 性能指标 (Performance Metrics)
基于 2026-05-06 构建版本 (Suffix z/x Enable) 的动态选重率测试结果：

| 语料来源 | 频率降序-全码 | 频率降序-简码 | 原始码表-全码 | 原始码表-简码 |
| :--- | :--- | :--- | :--- | :--- |
| **知乎简体** | **5.05‱** | 535.24‱ | 738.58‱ | 683.85‱ |
| **北语简体** | **3.22‱** | 583.13‱ | 748.23‱ | 746.56‱ |
| **繁简联合** | **7.15‱** | 508.08‱ | 686.22‱ | 1073.67‱ |

*注：简码模式下的高选重率是由于简码密度极大（常用字大量挤占 1-3 码空间）导致的预期现象。全码模式下的选重率已通过 z/x 后缀逻辑得到本质改善。*

## 9. 环境与路径
- **项目根目录**：所有脚本需在项目根目录运行以正确识别 `REPO_ROOT`。
- **核心引擎**：[cangjie_builder.py](file:///c:/dev/repos/github/IME/rime-zong/scripts/cangjie/core/cangjie_builder.py)
- **数据路径**：字频文件位于 `schemas/common/frequency/char/sc/`。
