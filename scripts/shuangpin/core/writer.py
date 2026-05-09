from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

from .models import CharEntry, DictEntry, WordEntry


def merge_entries(
    char_entries: list[CharEntry],
    word_entries: list[WordEntry],
    cangjie_entries: list[DictEntry],
) -> list[DictEntry]:
    merged: dict[tuple[str, str], DictEntry] = {}

    def put(entry: DictEntry) -> None:
        key = (entry.text, entry.code)
        old = merged.get(key)
        if old is None or (entry.tier, -entry.weight, entry.source) < (old.tier, -old.weight, old.source):
            merged[key] = entry

    for entry in char_entries:
        tier = 10 if entry.source == "radicals" else 20
        put(DictEntry(entry.text, entry.code, entry.weight, tier, entry.source))
    for entry in word_entries:
        put(DictEntry(entry.text, entry.code, entry.weight, 30, "words"))
    for entry in cangjie_entries:
        put(entry)

    return sorted(merged.values(), key=lambda e: (e.tier, e.code, -e.weight, e.text))


def write_cangjie_prototype(entries: list[DictEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# text\tcode\tweight\tsource\n")
        for entry in sorted(entries, key=lambda e: (e.code, e.text)):
            f.write(f"{entry.text}\t{entry.code}\t{entry.weight}\t{entry.source}\n")


def write_dict(schema: str, entries: list[DictEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime dictionary\n")
        f.write("# encoding: utf-8\n")
        f.write("# AUTO-GENERATED. DO NOT EDIT.\n\n")
        f.write("---\n")
        f.write(f"name: {schema}\n")
        f.write(f'version: "{today}"\n')
        f.write("sort: by_weight\n")
        f.write("use_preset_vocabulary: false\n")
        f.write("...\n\n")
        for entry in entries:
            f.write(f"{entry.text}\t{entry.code}\t{entry.weight}\n")


def write_schema(schema: str, output_path: Path) -> None:
    names = {"zrm": "自然码双拼音形", "flypy": "小鹤双拼音形"}
    name = names.get(schema, schema)
    today = dt.date.today().isoformat()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(
            f"""# Rime schema settings
# encoding: utf-8
# AUTO-GENERATED. DO NOT EDIT.

schema:
  schema_id: {schema}
  name: {name}
  version: "{today}"
  author:
    - rime-zong
  description: |
    {name}
    单字：双拼两码 + 仓颉五代首尾辅助码，共四码。
    词语：按固定规则生成六码词码。
    仓颉：输入 o + 仓颉五代码，候选降权到最后。
  dependencies:
    - pinyin_simp

switches:
  - name: ascii_mode
    reset: 0
    states: [ 中文, 西文 ]
  - name: full_shape
    states: [ 半角, 全角 ]
  - name: extended_charset
    states: [ 常用, 增廣 ]
  - name: ascii_punct
    states: [ 。，, ．， ]
  - options: [ noop, traditionalization, simplification ]
    reset: 0
    states: [ 默认汉字, 繁體漢字, 简体汉字 ]

engine:
  processors:
    - ascii_composer
    - recognizer
    - key_binder
    - speller
    - punctuator
    - selector
    - navigator
    - express_editor
  segmentors:
    - ascii_segmentor
    - matcher
    - abc_segmentor
    - punct_segmentor
    - fallback_segmentor
  translators:
    - punct_translator
    - reverse_lookup_translator
    - table_translator
  filters:
    - simplifier
    - simplifier@traditionalization
    - uniquifier

speller:
  alphabet: zyxwvutsrqponmlkjihgfedcba
  max_code_length: 6
  auto_select: false
  auto_select_unique_candidate: false

translator:
  dictionary: {schema}
  enable_charset_filter: true
  encode_commit_history: false
  enable_encoder: false
  enable_completion: false
  enable_user_dict: false
  enable_sentence: false

abc_segmentor:
  extra_tags:

reverse_lookup:
  dictionary: pinyin_simp
  prism: pinyin_simp
  prefix: "`"
  suffix: "'"
  tips: 〔拼音〕
  preedit_format:
    - xform/([nl])v/$1ü/
    - xform/([nl])ue/$1üe/
    - xform/([jqxy])v/$1u/

simplifier:
  tips: all

traditionalization:
  opencc_config: s2t.json
  option_name: traditionalization
  tips: all

punctuator:
  import_preset: symbols

key_binder:
  import_preset: default
  bindings:
    - {{ when: has_menu, accept: space, send: space }}
    - {{ when: has_menu, accept: Tab, send: Escape }}
    - {{ when: composing, accept: space, send: Escape }}
    - {{ when: composing, accept: Tab, send: Escape }}

ascii_composer:
  switch_key:
    Caps_Lock: clear
    Shift_L: commit_code
    Shift_R: commit_text

recognizer:
  import_preset: default
  patterns:
    punct: "^/([0-9]0?|[a-z]+)$"
    reverse_lookup: "`[a-z]*'?$|[a-z]*'$"
"""
        )


def write_report(
    path: Path,
    schema: str,
    entries: list[DictEntry],
    char_count: int,
    word_count: int,
    cangjie_count: int,
    dropped_chars: int,
    dropped_words: int,
) -> None:
    source_counts = Counter(entry.source for entry in entries)
    code_groups: dict[str, list[DictEntry]] = defaultdict(list)
    for entry in entries:
        code_groups[entry.code].append(entry)
    collisions = {code: group for code, group in code_groups.items() if len(group) > 1}
    largest = sorted(collisions.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:20]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"# {schema} build report\n\n")
        f.write(f"- total entries: {len(entries)}\n")
        f.write(f"- char prototype entries: {char_count}\n")
        f.write(f"- word prototype entries: {word_count}\n")
        f.write(f"- prefixed cangjie entries: {cangjie_count}\n")
        f.write(f"- dropped chars: {dropped_chars}\n")
        f.write(f"- dropped words: {dropped_words}\n")
        f.write(f"- collision codes: {len(collisions)}\n\n")
        f.write("## Source counts\n\n")
        for source, count in sorted(source_counts.items()):
            f.write(f"- {source}: {count}\n")
        f.write("\n## Largest collision groups\n\n")
        for code, group in largest:
            sample = " ".join(entry.text for entry in group[:20])
            f.write(f"- {code}: {len(group)} candidates; {sample}\n")

