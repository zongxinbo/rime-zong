# scripts

本目录放置维护和打包 Rime 方案用的 Python 脚本。以下命令默认在仓库根目录执行；在 `scripts` 目录下执行也可以，但路径参数要按当前位置调整。

## 生成三码仓颉五代

从 `cangjie5/cangjie5.dict.yaml` 生成 `sancang5/sancang5.dict.yaml`：

```powershell
python scripts\gen_sancang5.py
```

常用选项：

```powershell
python scripts\gen_sancang5.py --include-phrases
python scripts\gen_sancang5.py --include-phrases --no-vocabulary
python scripts\gen_sancang5.py --include-phrases --generated-phrase-min-weight 100
```

说明：

- 默认只生成单字，按 `sancang5/essay-zh-hans.txt` 的单字频率排序同码候选。
- `--include-phrases` 会读取 `essay-zh-hans.txt` 中的多字词，逐字取三码并拼接成词语编码。
- `--no-vocabulary` 不写入 Rime 的 `vocabulary`、`max_phrase_length`、`min_phrase_weight` 字段，适合生成更便携的码表。
- `--generated-phrase-min-weight` 只影响脚本实际生成的词语，不影响 YAML 头部的 `min_phrase_weight` 字段。

脚本写正式 dict 时会先写临时文件，再替换目标文件，不会先删除原文件。

## 生成依赖清单

扫描正式方案并生成仓库根目录的 `scheme_dependencies.yaml`：

```powershell
python scripts\scheme_dependencies.py
```

可指定输出路径：

```powershell
python scripts\scheme_dependencies.py --output scheme_dependencies.yaml
```

说明：

- 输出格式使用 YAML，和 Rime 配置保持一致，便于人工查看。
- 扫描时会跳过目录名以 `_` 开头的临时目录。
- 清单会记录 schema、dict、词频文件、grammar/gram、OpenCC、Lua、符号预设，以及 Rime 内置或外部预设。

## 拷贝方案依赖

把一个或多个方案及其依赖拷贝到输出目录：

```powershell
python scripts\copy_scheme_dependencies.py sancang5
python scripts\copy_scheme_dependencies.py sancang5 cangjie5_ice
```

默认输出到 `_output`。可指定目录并在拷贝前清空：

```powershell
python scripts\copy_scheme_dependencies.py sancang5 --output _output_sancang5 --clean
```

说明：

- schema、dict、txt、gram、custom、symbols 等文件会拷贝到输出目录根部。
- `opencc/` 和 `lua/` 会保留子目录结构。
- `--clean` 只允许清空仓库内且目录名以 `_` 开头的目录，避免误删。
- 输出目录默认以 `_` 开头，已通过 `.gitignore` 排除。
