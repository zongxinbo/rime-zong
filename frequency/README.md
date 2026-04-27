# 语料频次数据说明 (Frequency Data)

此目录包含用于 Rime 输入法方案优化的各领域语料字频与词频数据。

## 目录结构

- `_original/`: 原始语料文件（包含原始编码与复杂表头）。
- `char/`: 转换后的单字频次文件（格式：`字[Tab]频次`，UTF-8 编码）。
- `word/`: 转换后的词组频次文件（格式：`词[Tab]频次`，UTF-8 编码）。

## 语料来源

### 1. 知乎语料 (Zhihu)
- **文件**: `char/zhihu_char_freq.txt`
- **来源**: [chinese-characters-frequency](https://github.com/forfudan/chinese-characters-frequency)
- **说明**: 来源于约 6 亿字的知乎回答，代表现代网络用语、口语及生活化表达。

### 2. 北京语言大学 BCC 语料库 (BCC)
BCC 语料库总规模约 25 亿字。本项目使用了以下三个子集：

#### 2a. 通用字频 (blcu_char_freq)
- **文件**: `char/blcu_char_freq.txt` (14,975 字)
- **来源**: [邢红兵教授主页](https://faculty.blcu.edu.cn/xinghb/zh_CN/article/167473/content/1437.htm)
- **说明**: 基于 BCC 全量语料的通用字频统计，覆盖面最广。

#### 2b. 口语字频 (dialogue)
- **文件**: `char/dialogue_char_freq.txt`, `word/dialogue_word_freq.txt` (5,823 字)
- **来源**: [BCC 下载页](https://bcc.blcu.edu.cn/download)
- **说明**: 仅包含口语对话子集，最能反映日常对话中的用字习惯。

#### 2c. 多领域综合 (multi_domain)
- **文件**: `char/multi_domain_char_freq.txt`, `word/multi_domain_word_freq.txt` (7,902 字)
- **来源**: [BCC 下载页](https://bcc.blcu.edu.cn/download)
- **说明**: 包含口语、新闻、文学、近代汉语、古代汉语等多个领域的综合统计。因含有古代/近代汉语，字频分布与现代日常用字存在偏差，保留供未来词频优化使用。

### 3. SUBTLEX-CH (电影字幕)
- **文件**: `char/subtlex_char_freq.txt`, `word/subtlex_word_freq.txt`
- **来源**: [SUBTLEX-CH](https://openlexicon.fr/datasets-info/SUBTLEX-CH/README-subtlex-ch.html)
- **说明**: 基于电影和电视剧字幕的语料库，极具口语化参考价值。

### 4. Rime Essay
- **文件**: `word/essay-zh-hans.txt`
- **说明**: Rime 默认内置的传统语料数据。

## 维护脚本

- `scripts/freq_utils/convert_frequencies.py`: 用于处理知乎 (CSV) 和北语大 (XLSX) 原始数据。
- `scripts/freq_utils/convert_bcc_subtlex.py`: 用于处理 BCC 文本文件和 SUBTLEX GBK 编码文件。
