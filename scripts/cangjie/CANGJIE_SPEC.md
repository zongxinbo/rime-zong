# 仓颉方案技术规范 (CANGJIE_SPEC)

本文档记录了仓颉系列方案的设计逻辑、自动化调优算法以及核心架构原则。

## 1. 任务背景
优化仓颉系列方案（Sicang5/Wucang5）的简码分配方案，目标是利用现代语料库实现"高频优先"与"编码直觉"的平衡。

## 2. 核心数据源
- **Dialogue 口语语料 (`schemas/frequency/char/dialogue_char_freq.txt`)**：核心口语字频（源自北语大语料库加工），确保高频对话词汇优先。
- **Subtlex 影视字幕语料 (`schemas/frequency/char/subtlex_char_freq.txt`)**：基于影视字幕的日常频次，反映口语视听习惯，覆盖常用生活用语。
- **知乎语料 (`schemas/frequency/char/zhihu_char_freq.txt`)**：现代网络常用语料，提供更具时代感的频次分布。
- **北语大语料 (`schemas/frequency/char/blcu_char_freq.txt`)**：超大规模平衡语料库，提供基础字频基底。
- **Essay 语料 (`schemas/frequency/word/essay-zh-hans.txt`)**：传统 Rime 基础语料库。

## 3. 自动化分析工具
| 脚本名称 | 职能 | 位置 |
| :--- | :--- | :--- |
| **gen_shortcut_1.py** | 一简方案分析与生成 | `scripts/cangjie/core/` |
| **gen_shortcut_2.py** | 二简方案生成（空槽全占，GB2312 保护） | `scripts/cangjie/core/` |
| **gen_shortcut_3.py** | 三简方案生成（空槽全占，GB2312 保护） | `scripts/cangjie/core/` |
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

### 6.1 核心原则
- **顺位前缀**：所有简码必须是全码的绝对前缀（`code[:N]`）
- **GB2312 绝对保护**：任何码长上，如果原生编码恰好为该长度的 GB2312 字（原主），禁止被抢占
- **GB2312 资格门槛**：只有 GB2312 字才有资格获得简码
- **繁体字/生僻字透传**：非 GB2312 字保持原始仓颉五代编码，不生成简码
- **层级排他**：已在更短简码层获得分配的字，不参与更长层级的竞争

### 6.2 四层简码架构

| 层级 | 码长 | 数量 | 策略 |
| :--- | :--- | :--- | :--- |
| **一简 (S1)** | 1 码 | 25 字 | 手动精选最高频字，静态文件 |
| **二简 (S2)** | 2 码 | ~286 字 | 空槽全占（GB2312 原主保护） |
| **三简 (S3)** | 3 码 | ~2,376 字 | 空槽全占（GB2312 原主保护） |
| **四简 (S4)** | 4 码 | ~1,332 字 | 强制截断 5 码 GB2312 字 |

### 6.3 位置降权（Positional Demotion）
字典文件使用纯 `字\t码` 格式（无 weight 列），通过文件内条目排列顺序实现"降权退避"。

同一编码下的候选排序规则：
1. **简码条目**（该编码是某字的简码）→ 排最前，按 Z > S1 > S2 > S3 > S4 优先级
2. **原生全码**（该编码是某字的全码，且该字无更短简码）→ 排中间，按字频降序
3. **退避条目**（该编码是某字的全码，但该字已有更短简码）→ 排最后，按字频降序

### 6.4 GB2312 码长分布（优化后）

| 最短编码长度 | 字数 |
| :--- | :--- |
| 1 码 | 51 字 |
| 2 码 | 608 字 |
| 3 码 | 3,550 字 |
| 4 码 | 2,554 字 |
| **合计** | **6,763 字** |

所有 GB2312 汉字最短编码 ≤ 4 码（已验证）。

### 6.5 动态重码率
- 原版仓颉五代：0.3051%
- 优化后 Wucang5：0.5685%（+0.26%）

动态重码率仅增加 0.26 个百分点，代价极小。绝大多数新增重码发生在低频字上。

## 7. Schema 文件说明
- `wucang5.schema.yaml`：纯单字流方案（推荐）
- `wucang5_fluency.schema.yaml`：语句流方案（使用八股文模型）
- `sicang5.schema.yaml`：四码单字流方案
- `sicang5_fluency.schema.yaml`：四码语句流方案

## 8. 环境提示
- 所有脚本均在项目根目录运行。
- 核心引擎：`scripts/cangjie/core/cangjie_builder.py`
