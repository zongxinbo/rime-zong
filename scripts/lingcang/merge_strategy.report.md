# 灵仓 A 区字根合并策略报告

## 脚本区别

`search_a_mapping.py` 是早期的全映射枚举脚本，现已删除，原因是功能被 `search_merge_strategy.py` 覆盖。

- 固定假设：五个被 B 区占用的元音仓颉根 `a/e/i/o/u` 中，恰好一个落到私有码 `z`。
- 其余四个元音根分别合并到 `--targets` 给定的 A 区键。
- 每个候选都直接对样本重新编码、分桶、计算损失。
- 优点是口径直接；缺点是候选多时慢，默认参数在 5000 高频样本上容易超时。

`search_merge_strategy.py` 是新的两阶段策略搜索脚本。

- 第一步：复用 `analyze_merge_pairs.py` 的二根合并损失矩阵，为每个元音根筛出低损失候选目标。
- 第二步：组合成完整五根策略，先用二根损失做近似排序。
- 第三步：只对近似最优的前 `--exact-candidates` 个完整策略做真实编码分桶评分。
- 默认允许多个元音根同时落到 `z`，但不允许多个元音根同时合并到同一个已有 A 键。
- 优点是速度可控，适合扩大候选空间后搜索完整策略。

## 指标口径

`loss` / `proxy_permyriad` 都是代理选重损失的万分比，单位是 `‱`，不是百分比。

例如 `115.95‱` 表示约 `1.1595%` 的加权选重损失，不是 `115.95%`。

这个值不是 `scripts/assess/summary.py` 里的“知乎简体 频率降序-全码”或“北语简体 频率降序-全码”。它来自 `scripts.cangjie.core.cangjie_builder.get_weighted_frequencies()` 的综合字频：

| 来源 | 权重 |
| :--- | ---: |
| Dialogue | 6 |
| Subtlex | 5 |
| Zhihu | 4 |
| BLCU | 2 |
| Essay | 1 |

计算方式：

1. 按编码分组。
2. 每组按综合字频降序排序。
3. 每组首字视为不选重，其余字的字频权重计入损失。
4. `loss = collision_weight / total_weight * 10000`。

## 当前推荐

样本搜索第一名：

```text
a->n e->z i->x o->c u->w
```

对应字根关系：

| 原仓颉根 | 字根 | A 区目标 | 关系 |
| :--- | :--- | :--- | :--- |
| `a` | 日 | `n` | 日 / 弓合并 |
| `e` | 水 | `z` | 水独占私有码 |
| `i` | 戈 | `x` | 戈 / 難合并 |
| `o` | 人 | `c` | 人 / 金合并 |
| `u` | 山 | `w` | 山 / 田合并 |

完整码表评估：

| 方案 | 条目 | 唯一码位 | 重码组 | 重码字 | GB 最大候选 | GB 平均候选 | 代理选重损失 | 跳过未知根 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `rank1_a-n_e-z_i-x_o-c_u-w` | 106160 | 55445 | 23345 | 74060 | 4 | 1.094 | 115.95‱ | 21 |
| `current` | 106181 | 54546 | 23185 | 74820 | 7 | 1.119 | 193.79‱ | 21 |

结论：按当前代理指标，推荐策略相比当前映射把代理选重损失从 `193.79‱` 降到 `115.95‱`，GB 最大候选从 `7` 降到 `4`。

## 运行命令

样本策略搜索：

```powershell
python scripts\lingcang\search_merge_strategy.py --sample 5000 --per-vowel 14 --exact-candidates 5000 --top 80
```

完整码表候选评估使用 `scripts.lingcang.core.evaluator.evaluate_mapping`，对样本前几名和当前方案做全表比较。

## 样本策略搜索结果

```text
sample=5000 approximate=164516 exact=5000
rank	loss	max	collision_chars	assignment
1	104.01	3	536	a->n e->z i->x o->c u->w
2	104.15	3	542	a->n e->x i->z o->c u->w
3	104.54	3	500	a->n e->c i->x o->z u->w
4	104.65	3	501	a->n e->c i->z o->x u->w
5	105.30	3	557	a->n e->z i->x o->c u->t
6	105.32	3	546	a->n e->w i->x o->z u->t
7	105.42	3	547	a->n e->w i->z o->x u->t
8	105.44	3	563	a->n e->x i->z o->c u->t
9	105.63	3	522	a->n e->c i->x o->z u->t
10	105.73	3	523	a->n e->c i->z o->x u->t
11	105.89	4	603	a->n e->t i->x o->z u->w
12	106.00	4	604	a->n e->t i->z o->x u->w
13	106.10	3	520	a->v e->c i->x o->z u->w
14	106.26	3	558	a->v e->z i->x o->c u->w
15	106.26	4	555	a->z e->x i->z o->c u->w
16	106.29	3	560	a->v e->x i->z o->c u->w
17	106.31	3	562	a->n e->w i->x o->c u->z
18	106.32	3	554	a->z e->w i->x o->c u->t
19	106.33	3	554	a->x e->w i->z o->c u->t
20	106.54	3	568	a->n e->w i->z o->c u->x
21	106.64	4	566	a->n e->z i->x o->c u->y
22	106.71	3	524	a->v e->c i->z o->x u->w
23	106.74	3	557	a->v e->w i->x o->z u->t
24	106.77	4	551	a->n e->w i->x o->z u->y
25	106.79	4	572	a->n e->x i->z o->c u->y
26	106.88	4	552	a->n e->w i->z o->x u->y
27	107.07	4	574	a->z e->x i->z o->c u->t
28	107.08	4	558	a->z e->w i->z o->x u->t
29	107.08	4	527	a->n e->c i->x o->z u->y
30	107.14	3	537	a->v e->c i->x o->z u->t
31	107.15	4	516	a->z e->c i->z o->x u->w
32	107.19	4	528	a->n e->c i->z o->x u->y
33	107.35	3	561	a->v e->w i->z o->x u->t
34	107.39	4	577	a->n e->w i->x o->z u->d
35	107.43	4	575	a->n e->z i->x o->c u->v
36	107.44	4	617	a->v e->t i->x o->z u->w
37	107.50	3	574	a->v e->z i->x o->c u->t
38	107.53	3	576	a->v e->x i->z o->c u->t
39	107.57	4	581	a->n e->x i->z o->c u->v
40	107.61	4	580	a->n e->w i->z o->x u->d
41	107.68	4	565	a->z e->w i->x o->c u->y
42	107.70	4	565	a->x e->w i->z o->c u->y
43	107.74	4	555	a->n e->c i->x o->z u->d
44	107.75	3	541	a->v e->c i->z o->x u->t
45	107.75	4	536	a->z e->c i->z o->x u->t
46	107.77	4	567	a->n e->w i->x o->z u->v
47	107.88	4	568	a->n e->w i->z o->x u->v
48	107.88	4	585	a->n e->z i->b o->x u->w
49	107.94	4	574	a->n e->l i->x o->z u->w
50	107.95	4	539	a->n e->c i->x o->z u->v
51	107.96	4	573	a->n e->l i->z o->x u->w
52	107.96	4	558	a->n e->c i->z o->x u->d
53	107.98	4	591	a->n e->x i->b o->z u->w
54	108.04	4	575	a->z e->w i->x o->c u->v
55	108.05	4	621	a->v e->t i->z o->x u->w
56	108.05	4	540	a->n e->c i->z o->x u->v
57	108.07	4	577	a->x e->w i->z o->c u->v
58	108.09	3	555	a->z e->w i->x o->c u->z
59	108.19	4	579	a->z e->w i->z o->c u->x
60	108.22	4	564	a->v e->w i->x o->z u->y
61	108.33	4	597	a->n e->z i->x o->c u->d
62	108.34	4	626	a->n e->t i->x o->z u->y
63	108.43	4	585	a->z e->x i->z o->c u->y
64	108.44	3	577	a->v e->w i->x o->c u->z
65	108.44	4	627	a->n e->t i->z o->x u->y
66	108.48	4	603	a->n e->x i->z o->c u->d
67	108.51	4	576	a->n e->w i->x o->z u->h
68	108.55	4	565	a->z e->w i->z o->x u->y
69	108.59	4	585	a->z e->l i->x o->c u->w
70	108.60	4	585	a->x e->l i->z o->c u->w
71	108.61	4	577	a->n e->w i->z o->x u->h
72	108.62	4	544	a->v e->c i->x o->z u->y
73	108.65	3	536	a->n e->w i->x o->z u->c
74	108.67	3	547	a->l e->x i->z o->c u->w
75	108.67	3	583	a->v e->w i->z o->c u->x
76	108.70	3	570	a->w e->z i->x o->c u->t
77	108.73	3	572	a->w e->x i->z o->c u->t
78	108.75	3	590	a->v e->w i->x o->z u->d
79	108.76	3	537	a->n e->w i->z o->x u->c
80	108.79	3	554	a->f e->z i->x o->c u->w
```

## 完整码表候选评估

```text
name	entries	unique	collision_groups	collision_chars	gb_max	gb_avg	proxy_permyriad	skipped
rank1_a-n_e-z_i-x_o-c_u-w	106160	55445	23345	74060	4	1.094	115.95	21
rank2_a-n_e-x_i-z_o-c_u-w	106160	55501	23315	73974	4	1.095	116.08	21
rank3_a-n_e-c_i-x_o-z_u-w	106195	56239	23472	73428	4	1.090	116.21	21
rank4_a-n_e-c_i-z_o-x_u-w	106195	56199	23442	73438	4	1.090	116.30	21
rank13_a-v_e-c_i-x_o-z_u-w	106194	56600	23732	73326	4	1.091	117.34	21
rank6_a-n_e-w_i-x_o-z_u-t	106191	56060	23241	73372	5	1.101	118.29	21
rank5_a-n_e-z_i-x_o-c_u-t	106160	53895	23175	75440	5	1.102	118.58	21
current	106181	54546	23185	74820	7	1.119	193.79	21
old_avoid_t_current	106181	54546	23185	74820	7	1.119	193.79	21
old_edge_pairs	106181	53042	22989	76128	7	1.126	195.05	21
```
