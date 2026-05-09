from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

from .frequency import FrequencyScores, load_default_frequency_scores
from .models import CharEntry, DictEntry, WordEntry


def iter_char_dict_entries(entry: CharEntry, primary_weights: dict[str, int]) -> list[DictEntry]:
    """把单字原型展开成最终码表中的显式多编码条目。

    最终码表需要迁移到其他平台，所以不能依赖 Rime 的前缀补全。
    主读音单字会展开为一、二、三、四码；异读只保留四码全码，
    避免“她 j”这类异读短码污染高频短码空间。
    """

    tier = 10 if entry.source == "radicals" else 20
    if entry.source == "radicals":
        return [DictEntry(entry.text, entry.code, entry.weight, tier, entry.source)]

    is_primary = entry.weight > 0 and entry.weight == primary_weights.get(entry.text, 0)
    codes = [entry.code]
    if is_primary:
        codes = [
            entry.sp[:1],
            entry.sp,
            entry.sp + entry.aux[:1],
            entry.code,
        ]
    return [
        DictEntry(entry.text, code, entry.weight, tier, entry.source)
        for code in dict.fromkeys(codes)
        if code
    ]


def iter_word_dict_entries(entry: WordEntry) -> list[DictEntry]:
    """把词语六码原型展开成 0/1/2 位辅助码三档词码。"""

    codes = [entry.code]
    if len(entry.code) == 6:
        codes = [
            entry.code[:4],
            entry.code[:5],
            entry.code,
        ]
    return [
        DictEntry(entry.text, code, entry.weight, 30, "words")
        for code in dict.fromkeys(codes)
        if code
    ]


def merge_entries(
    char_entries: list[CharEntry],
    word_entries: list[WordEntry],
    cangjie_entries: list[DictEntry],
    frequency_scores: FrequencyScores | None = None,
) -> list[DictEntry]:
    frequencies = frequency_scores or load_default_frequency_scores()
    merged: dict[tuple[str, str], DictEntry] = {}
    primary_weights: dict[str, int] = {}
    for entry in char_entries:
        if entry.source == "chars":
            primary_weights[entry.text] = max(primary_weights.get(entry.text, 0), entry.weight)

    def put(entry: DictEntry) -> None:
        key = (entry.text, entry.code)
        old = merged.get(key)
        if old is None or (entry.tier, -entry.weight, entry.source) < (old.tier, -old.weight, old.source):
            merged[key] = entry

    for entry in char_entries:
        for dict_entry in iter_char_dict_entries(entry, primary_weights):
            put(dict_entry)
    for entry in word_entries:
        for dict_entry in iter_word_dict_entries(entry):
            put(dict_entry)
    for entry in cangjie_entries:
        put(entry)

    # 最终码表不写词频列，候选顺序完全由文件顺序决定。同码候选先看
    # 源码表权重：单字权重来自单字原型，词语权重来自 pinyin_ice.base；
    # 这能保住“支付宝”这类现代高权重词。外部字词频率作为补充信号，
    # 主要用于源表权重相近或为 0 的条目。
    return sorted(
        merged.values(),
        key=lambda e: (
            e.source == "cangjie",
            e.code,
            -max(e.weight, 0),
            -frequencies.score_entry(e),
            -e.weight,
            e.tier,
            e.text,
        ),
    )


def write_cangjie_prototype(entries: list[DictEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# 字符\t编码\t权重\t来源\n")
        for entry in sorted(entries, key=lambda e: (e.code, e.text)):
            f.write(f"{entry.text}\t{entry.code}\t{entry.weight}\t{entry.source}\n")


def write_dict(schema: str, entries: list[DictEntry], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Rime 词典\n")
        f.write("# 编码：UTF-8\n")
        f.write("# 自动生成，请勿手动修改。\n\n")
        f.write("---\n")
        f.write(f"name: {schema}\n")
        f.write(f'version: "{today}"\n')
        f.write("sort: original\n")
        f.write("use_preset_vocabulary: false\n")
        f.write("...\n\n")
        for entry in entries:
            f.write(f"{entry.text}\t{entry.code}\n")


def write_schema(schema: str, output_path: Path) -> None:
    names = {"zrm": "自然码·仓颉", "flypy": "小鹤·仓颉"}
    name = names.get(schema, schema)
    today = dt.date.today().isoformat()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(
            f"""# Rime 方案配置
# 编码：UTF-8
# 自动生成，请勿手动修改。

schema:
  schema_id: {schema}
  name: {name}
  version: "{today}"
  author:
    - rime-zong
  description: |
    {name}
    单字：显式生成双拼首码、双拼全码、双拼加一位辅码、双拼加两位辅码。
    词语：显式生成无辅码、一位辅码、两位辅码词码。
    仓颉：输入 o + 仓颉五代码，候选排在普通条目之后。
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
  delimiter: " ;"
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
  max_phrase_length: 8

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
        f.write(f"# {schema} 构建报告\n\n")
        f.write(f"- 最终条目数：{len(entries)}\n")
        f.write(f"- 单字原型条目数：{char_count}\n")
        f.write(f"- 词语原型条目数：{word_count}\n")
        f.write(f"- o 前缀仓颉条目数：{cangjie_count}\n")
        f.write(f"- 丢弃单字数：{dropped_chars}\n")
        f.write(f"- 丢弃词语数：{dropped_words}\n")
        f.write(f"- 有重码的编码数：{len(collisions)}\n\n")
        f.write("## 来源统计\n\n")
        for source, count in sorted(source_counts.items()):
            f.write(f"- {source}: {count}\n")
        f.write("\n## 最大重码组\n\n")
        for code, group in largest:
            sample = " ".join(entry.text for entry in group[:20])
            f.write(f"- {code}: {len(group)} 个候选；{sample}\n")
