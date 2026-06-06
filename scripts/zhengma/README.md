# 郑码脚本

本目录保存郑码相关源数据和从各郑码方案提取出的简码原型。

## 数据

- `data/chars.txt`：单字码表
- `data/roots.txt`：字根表
- `data/split.txt`：拆分表
- `data/README.md`：原始数据说明

## 简码原型

原型由 `extract_prototypes.py` 提取。脚本按同一词条的全部编码分组，短于该词条最长编码的入口才视为简码。

| 目录 | 一简 | 二简 | 三简 | 简码词 |
| --- | ---: | ---: | ---: | ---: |

重新生成示例：

```powershell
python scripts/zhengma/extract_prototypes.py --source-dict schemas/zhengma/zmsj/zmsj.dict.yaml --output-dir scripts/zhengma/prototypes_zmsj
```
