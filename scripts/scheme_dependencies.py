#!/usr/bin/env python3
"""生成并使用 Rime 方案依赖清单。

该脚本扫描仓库中的正式方案，生成 `scheme_dependencies.yaml`。
依赖清单包含 schema、字典、词频文件、语法模型、OpenCC 资源、Lua
组件以及 Rime 外部预设等信息。目录名以 `_` 开头的临时目录会被跳过。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "scheme_dependencies.yaml"


SCALAR_RE_CACHE: dict[str, re.Pattern[str]] = {}


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def skip_path(path: Path) -> bool:
    try:
        parts = path.resolve().relative_to(REPO_ROOT).parts
    except ValueError:
        return True
    return any(part.startswith("_") for part in parts)


def strip_comment(value: str) -> str:
    quote = ""
    escaped = False
    result: list[str] = []
    for char in value:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            continue
        if quote:
            result.append(char)
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            result.append(char)
            continue
        if char == "#":
            break
        result.append(char)
    return "".join(result).strip()


def clean_value(value: str) -> str:
    value = strip_comment(value).strip()
    if value in ("", "[]", "{}"):
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def scalar_pattern(key: str) -> re.Pattern[str]:
    if key not in SCALAR_RE_CACHE:
        SCALAR_RE_CACHE[key] = re.compile(rf"^\s*{re.escape(key)}:\s*(.*)$")
    return SCALAR_RE_CACHE[key]


def scalar_values(lines: Iterable[str], key: str) -> list[str]:
    values: list[str] = []
    pattern = scalar_pattern(key)
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        value = clean_value(match.group(1))
        if value:
            values.append(value)
    return values


def first_scalar(lines: Iterable[str], key: str, default: str = "") -> str:
    values = scalar_values(lines, key)
    return values[0] if values else default


def list_values(lines: list[str], key: str) -> list[str]:
    values: list[str] = []
    pattern = scalar_pattern(key)
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if not match or clean_value(match.group(1)):
            continue
        indent = len(line) - len(line.lstrip())
        for item_line in lines[index + 1 :]:
            stripped = item_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            item_indent = len(item_line) - len(item_line.lstrip())
            if item_indent <= indent:
                break
            if stripped.startswith("- "):
                value = clean_value(stripped[2:])
                if value:
                    values.append(value)
    return values


def existing_sorted(paths: Iterable[Path]) -> list[str]:
    return sorted({rel(path) for path in paths if path.exists()})


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def dump_yaml(data: dict[str, Any]) -> str:
    lines: list[str] = []

    def emit_value(prefix: str, value: Any, indent: int) -> None:
        pad = " " * indent
        if isinstance(value, dict):
            lines.append(f"{pad}{prefix}")
            for key, child in value.items():
                emit_value(f"{key}:", child, indent + 2)
        elif isinstance(value, list):
            lines.append(f"{pad}{prefix}")
            if not value:
                lines[-1] = f"{pad}{prefix} []"
            for item in value:
                if isinstance(item, (dict, list)):
                    lines.append(f"{pad}  -")
                    if isinstance(item, dict):
                        for key, child in item.items():
                            emit_value(f"{key}:", child, indent + 4)
                    else:
                        for child in item:
                            lines.append(f"{pad}    - {yaml_quote(str(child))}")
                else:
                    lines.append(f"{pad}  - {yaml_quote(str(item))}")
        elif value is None:
            lines.append(f"{pad}{prefix} null")
        elif isinstance(value, bool):
            lines.append(f"{pad}{prefix} {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{pad}{prefix} {value}")
        else:
            lines.append(f"{pad}{prefix} {yaml_quote(str(value))}")

    for key, value in data.items():
        emit_value(f"{key}:", value, 0)
    return "\n".join(lines) + "\n"


@dataclass
class SchemaInfo:
    schema_id: str
    name: str
    path: Path
    schema_dependencies: list[str]
    dictionaries: list[str]
    opencc_configs: list[str]
    import_presets: list[str]
    lua_modules: list[str]
    grammar_sections: list[str]
    grammar_languages: list[str]
    custom_patches: list[str]


@dataclass
class DictInfo:
    token: str
    path: Path
    import_tables: list[str]
    vocabulary: str
    use_preset_vocabulary: bool


@dataclass
class SchemeClosure:
    schema_id: str
    name: str
    direct_schema_dependencies: list[str] = field(default_factory=list)
    schema_files: set[Path] = field(default_factory=set)
    custom_files: set[Path] = field(default_factory=set)
    dict_files: set[Path] = field(default_factory=set)
    vocabulary_files: set[Path] = field(default_factory=set)
    grammar_files: set[Path] = field(default_factory=set)
    opencc_files: set[Path] = field(default_factory=set)
    lua_files: set[Path] = field(default_factory=set)
    preset_files: set[Path] = field(default_factory=set)
    external_presets: set[str] = field(default_factory=set)
    external_vocabularies: set[str] = field(default_factory=set)
    missing: set[str] = field(default_factory=set)

    @property
    def files(self) -> list[Path]:
        combined: set[Path] = set()
        for group in (
            self.schema_files,
            self.custom_files,
            self.dict_files,
            self.vocabulary_files,
            self.grammar_files,
            self.opencc_files,
            self.lua_files,
            self.preset_files,
        ):
            combined.update(group)
        return sorted(combined, key=rel)


class DependencyScanner:
    def __init__(self, root: Path = REPO_ROOT) -> None:
        self.root = root
        self.schema_index: dict[str, Path] = {}
        self.dict_index: dict[str, Path] = {}
        self.text_index: dict[str, list[Path]] = defaultdict(list)
        self.yaml_index: dict[str, list[Path]] = defaultdict(list)
        self.gram_index: dict[str, list[Path]] = defaultdict(list)
        self.opencc_index: dict[str, Path] = {}
        self.lua_index: dict[str, Path] = {}
        self.schema_cache: dict[str, SchemaInfo] = {}
        self.dict_cache: dict[str, DictInfo] = {}
        self._index_files()

    def _iter_files(self, suffix: str | None = None) -> Iterable[Path]:
        for path in self.root.rglob("*"):
            if not path.is_file() or skip_path(path):
                continue
            if suffix and not path.name.endswith(suffix):
                continue
            yield path

    def _index_files(self) -> None:
        for path in self._iter_files():
            if path.name.endswith(".schema.yaml"):
                lines = read_lines(path)
                schema_id = first_scalar(lines, "schema_id", path.name[:-12])
                self.schema_index[schema_id] = path
            elif path.name.endswith(".dict.yaml"):
                token = path.name[: -len(".dict.yaml")]
                self.dict_index[token] = path
            elif path.suffix == ".txt":
                self.text_index[path.stem].append(path)
            elif path.suffix == ".yaml":
                self.yaml_index[path.stem].append(path)
            elif path.suffix == ".gram":
                self.gram_index[path.stem].append(path)
            if path.parent.name == "opencc":
                self.opencc_index[path.name] = path
            if path.parent.name == "lua" and path.suffix == ".lua":
                self.lua_index[path.stem] = path

    def parse_schema(self, schema_id: str) -> SchemaInfo | None:
        if schema_id in self.schema_cache:
            return self.schema_cache[schema_id]
        path = self.schema_index.get(schema_id)
        if not path:
            return None
        lines = read_lines(path)
        text = "\n".join(lines)
        custom_refs = {
            f"{match}.custom.yaml"
            for match in re.findall(r"\b([A-Za-z0-9_.-]+)\.custom:/patch\?", text)
        }
        auto_custom = path.with_name(f"{schema_id}.custom.yaml")
        if auto_custom.exists():
            custom_refs.add(auto_custom.name)
        info = SchemaInfo(
            schema_id=schema_id,
            name=first_scalar(lines, "name", schema_id),
            path=path,
            schema_dependencies=list_values(lines, "dependencies"),
            dictionaries=sorted({value for value in scalar_values(lines, "dictionary") if value}),
            opencc_configs=sorted(set(scalar_values(lines, "opencc_config"))),
            import_presets=sorted(set(scalar_values(lines, "import_preset"))),
            lua_modules=sorted(set(re.findall(r"lua_[A-Za-z_]+@\*([A-Za-z0-9_.-]+)\*", text))),
            grammar_sections=sorted(set(re.findall(r"grammar:/([A-Za-z0-9_-]+)\?", text))),
            grammar_languages=sorted(set(scalar_values(lines, "language"))),
            custom_patches=sorted(custom_refs),
        )
        self.schema_cache[schema_id] = info
        return info

    def parse_dict(self, token: str) -> DictInfo | None:
        if token in self.dict_cache:
            return self.dict_cache[token]
        path = self.dict_index.get(token)
        if not path:
            return None
        lines = read_lines(path)
        use_preset_values = [value.lower() for value in scalar_values(lines, "use_preset_vocabulary")]
        info = DictInfo(
            token=token,
            path=path,
            import_tables=list_values(lines, "import_tables"),
            vocabulary=first_scalar(lines, "vocabulary"),
            use_preset_vocabulary=any(value == "true" for value in use_preset_values),
        )
        self.dict_cache[token] = info
        return info

    def _find_yaml(self, name: str, preferred_dir: Path | None = None) -> Path | None:
        candidates = self.yaml_index.get(Path(name).stem, [])
        if preferred_dir:
            for path in candidates:
                if path.parent == preferred_dir and path.name == name:
                    return path
        for path in candidates:
            if path.name == name:
                return path
        return None

    def _find_text(self, name: str, preferred_dir: Path | None = None) -> Path | None:
        filename = f"{name}.txt"
        candidates = self.text_index.get(name, [])
        if preferred_dir:
            for path in candidates:
                if path.parent == preferred_dir and path.name == filename:
                    return path
        for path in candidates:
            if path.name == filename:
                return path
        return None

    def _grammar_languages(self, grammar_file: Path, sections: set[str]) -> set[str]:
        languages: set[str] = set()
        current_section = ""
        for line in read_lines(grammar_file):
            section_match = re.match(r"^([A-Za-z0-9_]+):\s*$", line)
            if section_match:
                current_section = section_match.group(1)
                continue
            if current_section in sections:
                language_match = re.match(r"^\s+language:\s*(.+)$", line)
                if language_match:
                    language = clean_value(language_match.group(1))
                    if language:
                        languages.add(language)
        return languages

    def _add_opencc(self, filename: str, closure: SchemeClosure, seen: set[str]) -> None:
        if filename in seen:
            return
        seen.add(filename)
        path = self.opencc_index.get(filename)
        if not path:
            closure.missing.add(f"opencc/{filename}")
            return
        closure.opencc_files.add(path)
        if path.suffix != ".json":
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            closure.missing.add(f"{rel(path)}: 无法解析 OpenCC JSON")
            return
        for child in self._opencc_file_refs(data):
            self._add_opencc(child, closure, seen)

    def _opencc_file_refs(self, value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "file" and isinstance(child, str):
                    yield child
                else:
                    yield from self._opencc_file_refs(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._opencc_file_refs(child)

    def collect(self, schema_id: str) -> SchemeClosure:
        info = self.parse_schema(schema_id)
        closure = SchemeClosure(
            schema_id=schema_id,
            name=info.name if info else schema_id,
            direct_schema_dependencies=info.schema_dependencies if info else [],
        )
        self._collect_schema(schema_id, closure, set(), set(), set())
        return closure

    def _collect_schema(
        self,
        schema_id: str,
        closure: SchemeClosure,
        seen_schemas: set[str],
        seen_dicts: set[str],
        seen_opencc: set[str],
    ) -> None:
        if schema_id in seen_schemas:
            return
        seen_schemas.add(schema_id)
        info = self.parse_schema(schema_id)
        if not info:
            closure.missing.add(f"{schema_id}.schema.yaml")
            return
        closure.schema_files.add(info.path)

        for custom_name in info.custom_patches:
            custom_file = info.path.with_name(custom_name)
            if custom_file.exists():
                closure.custom_files.add(custom_file)

        for dependency in info.schema_dependencies:
            self._collect_schema(dependency, closure, seen_schemas, seen_dicts, seen_opencc)

        for dictionary in info.dictionaries:
            self._collect_dict(dictionary, closure, seen_dicts)

        for preset in info.import_presets:
            if preset == "symbols":
                symbols = self._find_yaml("symbols.yaml")
                if symbols:
                    closure.preset_files.add(symbols)
                else:
                    closure.missing.add("symbols.yaml")
            else:
                closure.external_presets.add(preset)

        for module in info.lua_modules:
            lua_file = self.lua_index.get(module)
            if lua_file:
                closure.lua_files.add(lua_file)
            else:
                closure.missing.add(f"lua/{module}.lua")

        for config in info.opencc_configs:
            self._add_opencc(config, closure, seen_opencc)

        grammar_sections = set(info.grammar_sections)
        grammar_languages = set(info.grammar_languages)
        if grammar_sections:
            grammar_file = info.path.with_name("grammar.yaml")
            if grammar_file.exists():
                closure.grammar_files.add(grammar_file)
                grammar_languages.update(self._grammar_languages(grammar_file, grammar_sections))
            else:
                closure.missing.add(f"{info.path.parent.name}/grammar.yaml")
        for language in grammar_languages:
            for gram in self.gram_index.get(language, []):
                closure.grammar_files.add(gram)
            if language not in self.gram_index:
                closure.missing.add(f"{language}.gram")

    def _collect_dict(self, token: str, closure: SchemeClosure, seen_dicts: set[str]) -> None:
        if token in seen_dicts:
            return
        seen_dicts.add(token)
        info = self.parse_dict(token)
        if not info:
            closure.missing.add(f"{token}.dict.yaml")
            return
        closure.dict_files.add(info.path)

        for imported in info.import_tables:
            self._collect_dict(imported, closure, seen_dicts)

        vocabulary = info.vocabulary
        if not vocabulary and info.use_preset_vocabulary:
            vocabulary = "essay"
        if vocabulary:
            vocab_file = self._find_text(vocabulary, info.path.parent)
            if vocab_file:
                closure.vocabulary_files.add(vocab_file)
            else:
                closure.external_vocabularies.add(vocabulary)

    def all_scheme_data(self) -> dict[str, Any]:
        schemes: dict[str, Any] = {}
        for schema_id in sorted(self.schema_index):
            closure = self.collect(schema_id)
            schemes[schema_id] = {
                "name": closure.name,
                "schema_dependencies": closure.direct_schema_dependencies,
                "files": [rel(path) for path in closure.files],
                "groups": {
                    "schema": existing_sorted(closure.schema_files),
                    "custom": existing_sorted(closure.custom_files),
                    "dict": existing_sorted(closure.dict_files),
                    "vocabulary": existing_sorted(closure.vocabulary_files),
                    "grammar": existing_sorted(closure.grammar_files),
                    "opencc": existing_sorted(closure.opencc_files),
                    "lua": existing_sorted(closure.lua_files),
                    "preset": existing_sorted(closure.preset_files),
                },
                "external": {
                    "preset": sorted(closure.external_presets),
                    "vocabulary": sorted(closure.external_vocabularies),
                },
                "missing": sorted(closure.missing),
            }
        return {
            "version": 1,
            "generated_by": "scripts/scheme_dependencies.py",
            "schemes": schemes,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="扫描正式方案并生成依赖清单。")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="输出 YAML 文件路径，默认写到仓库根目录 scheme_dependencies.yaml",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scanner = DependencyScanner()
    data = scanner.all_scheme_data()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dump_yaml(data), encoding="utf-8", newline="\n")
    print(f"已生成：{args.output}", file=sys.stderr)
    print(f"方案数量：{len(data['schemes'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
