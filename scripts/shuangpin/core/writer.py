from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from pathlib import Path

from .frequency import FrequencyScores, load_default_frequency_scores
from .models import CharEntry, DictEntry, WordEntry


CHAR_TWO_CODE_SECOND_MIN_WEIGHT = 50_000
CHAR_THREE_CODE_SECOND_MIN_WEIGHT = 10_000


def is_primary_char_entry(entry: CharEntry, primary_weights: dict[str, int]) -> bool:
    """判断单字读音是否为当前字的主读音。

    单字源表会给多音字保留多条读音。短码只允许主读音参与，异读一律
    只留四码全码，避免“区 ou”“她 j”这类低概率读音挤占短码。
    """

    return entry.source == "chars" and entry.weight > 0 and entry.weight == primary_weights.get(entry.text, 0)


def build_char_short_ranks(
    entries: list[CharEntry],
    primary_weights: dict[str, int],
    frequencies: FrequencyScores,
) -> tuple[dict[CharEntry, int], dict[CharEntry, int], dict[CharEntry, int]]:
    """为一、二、三码短码计算分组排名。

    排名策略参考 Openfly 的“显式短码层”思想：一简只取每个首键首选；
    二码保证每个双拼音节有首选，少量高频次选进入；三码按“完整双拼
    + 首辅码”继续分流，也只收首选和高频次选。这样可以避免纯字频
    阈值造成 `sb` 这类音节空码。
    """

    one_groups: dict[str, list[CharEntry]] = defaultdict(list)
    two_groups: dict[str, list[CharEntry]] = defaultdict(list)
    three_groups: dict[str, list[CharEntry]] = defaultdict(list)

    for entry in entries:
        if not is_primary_char_entry(entry, primary_weights):
            continue
        one_groups[entry.sp[:1]].append(entry)
        two_groups[entry.sp].append(entry)
        three_groups[entry.sp + entry.aux[:1]].append(entry)

    def sort_key(entry: CharEntry) -> tuple[object, ...]:
        return (-frequencies.score_text(entry.text), -entry.weight, entry.text, entry.code)

    def rank(groups: dict[str, list[CharEntry]]) -> dict[CharEntry, int]:
        ranks: dict[CharEntry, int] = {}
        for group in groups.values():
            for index, entry in enumerate(sorted(group, key=sort_key), start=1):
                ranks[entry] = index
        return ranks

    return rank(one_groups), rank(two_groups), rank(three_groups)


def iter_char_dict_entries(
    entry: CharEntry,
    primary_weights: dict[str, int],
    one_code_ranks: dict[CharEntry, int],
    two_code_ranks: dict[CharEntry, int],
    three_code_ranks: dict[CharEntry, int],
) -> list[DictEntry]:
    """把单字原型展开成最终码表中的显式多编码条目。

    最终码表需要迁移到其他平台，所以不能依赖 Rime 的前缀补全。
    主读音按分组排名生成一、二、三码短码；异读只保留四码全码。
    """

    tier = 10 if entry.source == "radicals" else 20
    if entry.source == "radicals":
        return [DictEntry(entry.text, entry.code, entry.weight, tier, entry.source)]

    is_primary = is_primary_char_entry(entry, primary_weights)
    codes = [entry.code]
    if is_primary:
        codes = []
        if one_code_ranks.get(entry) == 1:
            codes.append(entry.sp[:1])
        two_rank = two_code_ranks.get(entry)
        if two_rank == 1 or (two_rank == 2 and entry.weight >= CHAR_TWO_CODE_SECOND_MIN_WEIGHT):
            codes.append(entry.sp)
        three_rank = three_code_ranks.get(entry)
        if three_rank == 1 or (three_rank == 2 and entry.weight >= CHAR_THREE_CODE_SECOND_MIN_WEIGHT):
            codes.append(entry.sp + entry.aux[:1])
        codes.append(entry.code)
    return [
        DictEntry(entry.text, code, entry.weight, tier, entry.source)
        for code in dict.fromkeys(codes)
        if code
    ]


def iter_word_dict_entries(entry: WordEntry) -> list[DictEntry]:
    """把词语原型展开成短码路线和全码路线。

    `WordEntry.code` 保存当前词条的主码：高频词是逐字首码，低频词是全双拼码；
    `aliases` 保存同一路线的辅码定重码，以及另一条路线的全码或短码。
    这里不再从单一六码原型截前缀，避免二字、三字、四字词规则不一致。
    """

    codes = [entry.code, *entry.aliases]
    return [
        DictEntry(entry.text, code, entry.weight, 30, "words")
        for code in dict.fromkeys(codes)
        if code
    ]


def add_cangjie_direct_aliases(merged: dict[tuple[str, str], DictEntry]) -> None:
    """只给被普通候选挡住的仓颉短码补 `z` 直达码。

    例如 `oo`、`ou` 这类编码前面有拼音/双拼候选，仓颉候选会被排到
    后面，于是补 `ooz`、`ouz`。补出来的直达码在自己的码位优先于
    普通候选；如果原码已经 6 码，补 `z` 会超过方案最长码长，就不再生成。
    """

    normal_codes = {entry.code for entry in merged.values() if entry.source != "cangjie"}
    for entry in list(merged.values()):
        if entry.source != "cangjie" or entry.code not in normal_codes or len(entry.code) >= 6:
            continue
        alias = entry.code + "z"
        key = (entry.text, alias)
        if key in merged:
            continue
        merged[key] = DictEntry(
            text=entry.text,
            code=alias,
            weight=entry.weight,
            tier=5,
            source="cangjie_direct",
            order=entry.order,
        )


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
    one_code_ranks, two_code_ranks, three_code_ranks = build_char_short_ranks(
        char_entries,
        primary_weights,
        frequencies,
    )

    def put(entry: DictEntry) -> None:
        key = (entry.text, entry.code)
        old = merged.get(key)
        if old is None or (entry.tier, -entry.weight, entry.source) < (old.tier, -old.weight, old.source):
            merged[key] = entry

    for entry in char_entries:
        for dict_entry in iter_char_dict_entries(
            entry,
            primary_weights,
            one_code_ranks,
            two_code_ranks,
            three_code_ranks,
        ):
            put(dict_entry)
    for entry in word_entries:
        for dict_entry in iter_word_dict_entries(entry):
            put(dict_entry)
    for entry in cangjie_entries:
        put(entry)
    add_cangjie_direct_aliases(merged)

    def sort_key(entry: DictEntry) -> tuple[object, ...]:
        """生成最终码表排序键。

        最终码表不写词频列，候选顺序完全由文件顺序决定。三码及以内先
        保单字手感，单字内部按外部字频排；四码及以上让词语源表权重
        更有话语权，保住“支付宝”这类现代高权重词。仓颉兜底候选整体
        放在最后，同码时按仓颉五代原表顺序排列。
        """

        if entry.source == "cangjie_direct":
            return (0, entry.code, -1, entry.order, 0, entry.tier, entry.text)
        if entry.source == "cangjie":
            return (1, entry.code, entry.order, 0, 0, entry.text)

        short_tier = entry.tier if len(entry.code) <= 3 else 0
        if entry.source == "words":
            primary = -max(entry.weight, 0)
            secondary = -frequencies.score_entry(entry)
        elif entry.source == "chars":
            primary = -frequencies.score_entry(entry)
            secondary = -max(entry.weight, 0)
        else:
            primary = -max(entry.weight, 0)
            secondary = -frequencies.score_entry(entry)

        return (0, entry.code, short_tier, primary, secondary, entry.tier, entry.text)

    return sorted(merged.values(), key=sort_key)


def write_cangjie_prototype(entries: list[DictEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# 字符\t编码\t权重\t来源\n")
        for entry in sorted(entries, key=lambda e: (e.code, e.order, e.text)):
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


def write_schema(
    schema: str,
    output_path: Path,
    *,
    include_words: bool = True,
    max_code_length: int = 10,
    max_phrase_length: int = 8,
) -> None:
    names = {
        "zrm": "自然码·仓颉",
        "zrm_single": "自然码·仓颉·单字",
        "flypy": "小鹤·仓颉",
        "flypy_single": "小鹤·仓颉·单字",
    }
    name = names.get(schema, schema)
    today = dt.date.today().isoformat()
    if include_words:
        word_description = "词语：高频词显式生成短码；所有入库词保留全双拼码及其辅码定重码。"
    else:
        word_description = "词语：不收词，不造词，只保留静态单字和仓颉兜底。"
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
    单字：一位辅助码末尾补 z；短码按分组首选和高频次选生成，异读不占短码。
    {word_description}
    仓颉：输入 o + 仓颉五代码，同字多码全部保留；必要时补 z 直达仓颉候选。
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
  max_code_length: {max_code_length}
  auto_select: false
  auto_select_unique_candidate: false

translator:
  dictionary: {schema}
  enable_charset_filter: true
  encode_commit_history: false
  enable_encoder: false
  enable_completion: true
  enable_user_dict: false
  enable_sentence: false
  max_phrase_length: {max_phrase_length}

abc_segmentor:
  extra_tags:

reverse_lookup:
  dictionary: pinyin_simp
  prism: pinyin_simp
  prefix: "`"
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
    - {{ when: has_menu, accept: semicolon, send: 2 }}
    - {{ when: has_menu, accept: apostrophe, send: 3 }}
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
    reverse_lookup: "`[a-z]*$"
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
        f.write(f"- 仓颉兜底条目数（含 z 直达）：{cangjie_count}\n")
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
