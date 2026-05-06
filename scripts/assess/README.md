# Rime Schema Assessment Scripts

本项目提供了一套用于评估 Rime 输入法方案性能的脚本，参考并复刻了 [yuhao-assess](https://github.com/forfudan/yuhao-assess) 的核心评估指标。

## 核心评估指标

### 1. 重码分析 (Duplicate Analysis)
- **静态重码 (Static Duplicate)**: 统计编码冲突的字符数和组数。
- **动态选重率 (Dynamic Rate)**: 结合字频，评估用户遇到重码并需要选择的概率。

### 2. 简码效率 (Efficiency)
- **加权平均码长 (Avg Code Length)**: 考虑字频后的平均击键数。
- **理论速度 (Theoretical WPM)**: 在固定 KPS（每秒按键数）下的理论打字速度。

### 3. 速度当量 (Speed Equivalent)
- **按键组合流程度**: 使用“当量表”（Equiv Table）对相邻按键进行加权，评估手指移动的难度。越接近 1.0 表示越流畅（多为双手互击），数值越高表示难度越大（如同指连击、跨排等）。

### 4. 候选数分析 (Candidate Analysis)
- **翻页频率评估**: 统计单个编码对应的最大和平均候选项数。

### 5. 键位热力 (Heatmap Analysis)
- **左右手平衡**: 评估负载分配。
- **按排分布**: 数字排、上排、中排、下排的利用率。
- **手指负担**: 各个手指的加权使用频率。

## 脚本列表

- `duplicate_analysis.py`: 重码指标计算。
- `short_code_efficiency.py`: 码长效率计算。
- `speed_equivalent.py`: 组合流畅度评估。
- `maximum_candidates.py`: 候选数分析。
- `keyboard_heatmap.py`: 键位热力与手感分析。
- `summary.py`: 全指标汇总报告。

## 使用方法

在项目根目录下运行：

```bash
python scripts/assess/summary.py --dict schemas/cangjie/wucang5/wucang5.dict.yaml
```

## 注意事项

- 默认使用 GB2312 字符集进行评估。
- 字频数据来源于 `schemas/common/essay-zh-hans.txt`。
