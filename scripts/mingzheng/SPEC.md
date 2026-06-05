# 明郑规格草案

本文记录明郑的目标规则。当前阶段优先固定取码原则，后续脚本实现以本文为准。

## 1. 设计目标

### 1.1 简全一致

单字简码应尽量成为该字全码的前缀，避免“简码一套、全码一套”的割裂。

### 1.2 字词一致

词组编码应使用 Rime encoder 规则从单字编码派生，避免人工词码和单字码体系不一致。

### 1.3 简繁分流

简体、繁体字形不同且对应字根不同的，应尽量拆成不同字根或不同根码，避免因字根归并导致简繁互相重码。

## 2. 单字取码

明郑单字码长固定为 4。每个字根提供 2 位根码。设一个字拆为若干字根，每个字根记为：

- `A`, `B`, `C`, `D`, `Z`：第 1、2、3、4、末字根
- `a`, `b`, `c`, `d`, `z`：对应字根的第 2 位根码
- `v`：补码

### 2.1 字根字

规则：取字根完整 2 位根码，补 `vv`。

说明记法：`Aavv`

示例：

```text
大 [大 hd] -> hdvv
```

### 2.2 两根字

规则：取第 1 根第 1 位、第 2 根完整 2 位、第 1 根第 2 位。

说明记法：`ABba`

示例：

```text
码 [石 hu 马 xh] -> hxhu
```

### 2.3 三根字

规则：取第 1 根第 1 位、第 2 根第 1 位、第 3 根完整 2 位。

说明记法：`ABCc`

示例：

```text
郑 [䒑 ug 大 hd 阝 ye] -> uhye
```

### 2.4 四根字

规则：取第 1、2、3、末根的第 1 位。四根字的末根即第 4 根。

说明记法：`ABCD`

示例：

```text
题 [日 kr 一 gy 龰 ii 页 he] -> kgih
```

### 2.5 多根字

规则：取第 1、2、3、末根的第 1 位。

说明记法：`ABCZ`

示例：

```text
彟 [彐 xb 寸 du 艹 ei 隹 nf 又 xu] -> xdex
```

## 3. 词组取码

词组编码由 Rime encoder 根据单字编码自动派生。规则目标如下。

### 3.1 两字词

规则：取两字各自前 2 码。

说明记法：`ABAB`

示例：

```text
无涯 -> ghvh
```

Rime 规则：

```yaml
- length_equal: 2
  formula: "AaAbBaBb"
```

### 3.2 三字词

规则：取第 1 字首码、第 2 字前 2 码、第 3 字首码。

说明记法：`ABCc`

示例：

```text
我爱你 -> mpnr
```

Rime 规则：

```yaml
- length_equal: 3
  formula: "AaBaBbCa"
```

### 3.3 四字词

规则：取前 4 字各自首码。

说明记法：`ABCD`

示例：

```text
别来无恙 -> jbgu
```

Rime 规则：

```yaml
- length_in_range: [4, 50]
  formula: "AaBaCaDa"
```

### 3.4 多字词

规则：取第 1、2、3、末字各自首码。

说明记法：`ABCZ`

示例：

```text
中华人民共和国 -> jnoj
```

Rime 规则：

```yaml
- length_in_range: [4, 50]
  formula: "AaBaCaDa"
```

说明：Rime encoder 的 `length_in_range: [4, 50]` 对四字词和多字词统一使用 `AaBaCaDa`；其中 `D` 在多字词中指末字。

## 4. Rime Encoder 规则

明郑词组造词规则应写入字典头部：

```yaml
encoder:
  rules:
    - length_equal: 2
      formula: "AaAbBaBb"
    - length_equal: 3
      formula: "AaBaBbCa"
    - length_in_range: [4, 50]
      formula: "AaBaCaDa"
```

这些公式是正式实现规则；上文的 `ABAB`、`ABCZ` 等只是便于讨论的说明记法。
