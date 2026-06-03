from __future__ import annotations

from collections import defaultdict

from .charset import is_gb2312, is_gbk


DictEntry = tuple[str, int | float, int, int, str]
PrefixEntry = tuple[int, DictEntry]
RankSuffix = tuple[int, str]
PrefixCandidate = tuple[float, int, str, str, str]
ONE_CODE_BODY_LETTERS = set("abcdefghijklmnopqrstuvwxyz")
ONE_CODE_RADICALS = {
    "a": "日", "b": "月", "c": "金", "d": "木", "e": "水", "f": "火", "g": "土",
    "h": "竹", "i": "戈", "j": "十", "k": "大", "l": "中", "m": "一", "n": "弓",
    "o": "人", "p": "心", "q": "手", "r": "口", "s": "尸", "t": "廿", "u": "山",
    "v": "女", "w": "田", "y": "卜",
}


def unique_seen_entries(entries: list[DictEntry]) -> list[DictEntry]:
    """按现有排序返回同一码位下首次出现的各个字。"""
    seen_entries = []
    seen_chars = set()
    for entry in entries:
        char = entry[4]
        if char not in seen_chars:
            seen_entries.append(entry)
            seen_chars.add(char)
    return seen_entries


def charset_allows(
    char: str,
    charset: str,
    *,
    score: int,
) -> bool:
    """判断字符是否属于指定自动消重字集。"""
    if charset == "all":
        return True
    if charset == "frequency":
        return score > 0
    if charset == "gbk":
        return is_gbk(char)
    if charset == "gb2312":
        return is_gb2312(char)
    raise ValueError("字集只能是 all、frequency、gbk 或 gb2312")


def parse_rank_suffixes(text: str) -> tuple[RankSuffix, ...]:
    """解析 ``2:z,3:x`` 形式的候选位后缀规则。"""
    rank_suffixes: list[RankSuffix] = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":", 1)
        if len(parts) != 2:
            raise ValueError("--suffix-z-ranks 必须形如 2:z,3:x")
        rank_text, suffix = parts[0].strip(), parts[1].strip()
        if not rank_text.isdigit():
            raise ValueError("--suffix-z-ranks 的候选位必须是正整数")
        rank = int(rank_text)
        if rank < 2:
            raise ValueError("--suffix-z-ranks 只能处理第 2 候选及以后")
        if len(suffix) != 1 or not suffix.isascii() or not suffix.islower():
            raise ValueError("--suffix-z-ranks 的后缀必须是单个小写 ASCII 字母")
        rank_suffixes.append((rank, suffix))
    if not rank_suffixes:
        raise ValueError("--suffix-z-ranks 至少需要一个候选位后缀规则")
    return tuple(rank_suffixes)


def build_z_suffix_entries(
    all_entries: list[DictEntry],
    *,
    occupied_entries: list[DictEntry] | None = None,
    used_text_code: set[tuple[str, str]],
    shortcut_leader_chars: set[str],
    char_freqs: dict[str, int],
    max_code_length: int,
    charset: str = "all",
    min_score: float = 0,
    rank_suffixes: tuple[RankSuffix, ...] = ((2, "z"),),
    max_source_length: int | None = None,
    occupied_policy: str = "strict",
) -> list[DictEntry]:
    """为尚可追加一键的候选生成直觉式 ``原码 + 后缀`` 入口。"""
    if min_score < 0:
        raise ValueError("--suffix-z-min-score 不能为负数")
    if max_source_length is None:
        max_source_length = max_code_length - 1
    if max_source_length < 1:
        raise ValueError("--suffix-z-max-source-length 必须为正整数")
    if occupied_policy not in {"strict", "ignore-nonfrequency-or-shortcut"}:
        raise ValueError("--suffix-z-occupied-policy 只能是 strict 或 ignore-nonfrequency-or-shortcut")

    code_groups: dict[str, list[DictEntry]] = defaultdict(list)
    for entry in all_entries:
        code_groups[entry[0]].append(entry)

    occupied_source = all_entries if occupied_entries is None else occupied_entries
    occupied_by_code: dict[str, list[DictEntry]] = defaultdict(list)
    for entry in occupied_source:
        occupied_by_code[entry[0]].append(entry)

    def is_blocked(new_code: str) -> bool:
        entries = occupied_by_code.get(new_code, [])
        if not entries:
            return False
        if occupied_policy == "strict":
            return True
        return any(
            entry[4] not in shortcut_leader_chars
            and charset_allows(entry[4], charset, score=char_freqs.get(entry[4], 0))
            for entry in entries
        )

    proposals: list[tuple[int, int, str, str, str]] = []
    for code, entries in code_groups.items():
        if code.startswith(("z", "x")) or len(code) > max_source_length or len(code) >= max_code_length:
            continue

        seen_entries = unique_seen_entries(entries)
        for rank, suffix in rank_suffixes:
            if len(seen_entries) < rank:
                continue
            char = seen_entries[rank - 1][4]
            score = char_freqs.get(char, 0)
            if char in shortcut_leader_chars or score < min_score:
                continue
            if not charset_allows(char, charset, score=score):
                continue
            proposals.append((score, rank, code, code + suffix, char))

    proposals.sort(key=lambda item: (-item[0], item[1], item[2], item[4]))
    suffix_entries: list[DictEntry] = []
    allocated_codes: set[str] = set()
    allocated_chars: set[str] = set()
    for score, _, _, new_code, char in proposals:
        if char in allocated_chars or new_code in allocated_codes:
            continue
        if is_blocked(new_code) or (char, new_code) in used_text_code:
            continue
        suffix_entries.append((new_code, 1, 0, -score, char))
        used_text_code.add((char, new_code))
        allocated_codes.add(new_code)
        allocated_chars.add(char)

    return suffix_entries


def dedup_prefix_charset_allows(
    char: str,
    charset: str,
    *,
    score: int,
) -> bool:
    """判断字符是否允许获得自然 z/x 前缀直达码。"""
    return charset_allows(char, charset, score=score)


def natural_dedup_prefix_codes(code: str) -> tuple[str, ...]:
    """返回可由原码直接推导的 z/x 前缀码，优先使用较短路径。"""
    return (
        "z" + code[:2],
        "x" + code[:2],
        "z" + code[:3],
        "x" + code[:3],
    )


def parse_prefix_levels(text: str) -> tuple[int, ...]:
    """解析 ``2,3`` 形式的 z/x 前缀短码层级。"""
    levels = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if not item.isdigit():
            raise ValueError("--dedup-prefix-short-levels 必须形如 2,3")
        level = int(item)
        if level not in {2, 3, 4}:
            raise ValueError("--dedup-prefix-short-levels 目前只支持 2、3 和 4")
        levels.append(level)
    if not levels:
        raise ValueError("--dedup-prefix-short-levels 至少需要一个层级")
    return tuple(dict.fromkeys(levels))


def short_prefix_codes(code: str, level: int) -> tuple[str, ...]:
    """返回自动 z/x 前缀短码候选，保持可由原码推导。"""
    if level == 2:
        return (
            "z" + code[0],
            "x" + code[0],
        )
    if level == 3:
        return (
            "z" + code[:2],
            "x" + code[:2],
        )
    if level == 4:
        return (
            "z" + code[:3],
            "x" + code[:3],
        )
    raise ValueError("前缀短码层级只能是 2、3 或 4")


def one_code_anchor_keys(code: str, char: str, ranks: dict[str, int]) -> list[tuple[str, float]]:
    """按普通一简锚点规则返回可用主体键和倍率。"""
    anchors: dict[str, float] = {}
    if not code:
        return []

    first = code[0]
    last = code[-1]
    if first in ONE_CODE_BODY_LETTERS:
        anchors[first] = max(anchors.get(first, 0), 1.15)
    if last in ONE_CODE_BODY_LETTERS:
        anchors[last] = max(anchors.get(last, 0), 1.05)
    if ranks.get(char, 999999) <= 120:
        for letter in code:
            if letter in ONE_CODE_BODY_LETTERS:
                anchors[letter] = max(anchors.get(letter, 0), 0.72)
    for letter, radical in ONE_CODE_RADICALS.items():
        if char == radical:
            anchors[letter] = max(anchors.get(letter, 0), 1.30)

    return sorted(anchors.items(), key=lambda item: (-item[1], item[0]))


def build_occupied_blocker(
    occupied_entries: list[DictEntry],
    *,
    shortcut_leader_chars: set[str],
    charset: str,
):
    occupied_by_code: dict[str, list[DictEntry]] = defaultdict(list)
    for entry in occupied_entries:
        occupied_by_code[entry[0]].append(entry)

    def is_blocked(code: str, char_freqs: dict[str, int]) -> bool:
        entries = occupied_by_code.get(code, [])
        if not entries:
            return False
        if any(entry[1] < 5 for entry in entries):
            return True
        return any(
            entry[4] not in shortcut_leader_chars
            and charset_allows(entry[4], charset, score=char_freqs.get(entry[4], 0))
            for entry in entries
        )

    return is_blocked


def build_dedup_prefix_entries(
    all_entries: list[DictEntry],
    *,
    occupied_entries: list[DictEntry] | None = None,
    used_text_code: set[tuple[str, str]],
    shortcut_leader_chars: set[str],
    char_freqs: dict[str, int],
    max_code_length: int,
    charset: str,
    min_score: float,
    short_level_char_freqs: dict[int, dict[str, int]] | None = None,
    full_char_freqs: dict[str, int] | None = None,
    short: bool = True,
    full: bool = True,
    short_levels: tuple[int, ...] = (2, 3),
    full_source_length: int = 4,
    deep_rank_multiplier: float = 1.5,
) -> list[PrefixEntry]:
    """自动生成 z/x 前缀短码和四码前缀选重码。"""
    if min_score < 0:
        raise ValueError("--dedup-prefix-min-score 不能为负数")
    if deep_rank_multiplier < 1:
        raise ValueError("--dedup-prefix-deep-rank-multiplier 不能小于 1")
    if charset not in {"all", "frequency", "gbk", "gb2312"}:
        raise ValueError("--dedup-prefix-charset 只能是 all、frequency、gbk 或 gb2312")
    if not short and not full:
        return []

    code_groups: dict[str, list[DictEntry]] = defaultdict(list)
    for entry in all_entries:
        code_groups[entry[0]].append(entry)

    occupied_source = all_entries if occupied_entries is None else occupied_entries
    is_blocked = build_occupied_blocker(
        occupied_source,
        shortcut_leader_chars=shortcut_leader_chars,
        charset=charset,
    )
    short_level_char_freqs = short_level_char_freqs or {}
    full_char_freqs = full_char_freqs or char_freqs
    level2_freqs = short_level_char_freqs.get(2, char_freqs)
    level2_ranks = {
        char: rank
        for rank, char in enumerate(sorted(level2_freqs, key=level2_freqs.get, reverse=True), start=1)
    }

    short_candidates_by_level: dict[int, list[PrefixCandidate]] = defaultdict(list)
    full_candidates: list[PrefixCandidate] = []
    for code, entries in code_groups.items():
        if code.startswith(("z", "x")):
            continue

        for rank, entry in enumerate(unique_seen_entries(entries), start=1):
            if rank == 1:
                continue
            if entry[1] != 5:
                continue
            char = entry[4]
            if char in shortcut_leader_chars:
                continue
            rank_multiplier = deep_rank_multiplier if rank >= 3 else 1.0
            if short:
                for level in short_levels:
                    level_freqs = short_level_char_freqs.get(level, char_freqs)
                    level_score = level_freqs.get(char, 0)
                    if level_score < min_score:
                        continue
                    if not dedup_prefix_charset_allows(char, charset, score=level_score):
                        continue
                    if level == 2:
                        anchor_keys = one_code_anchor_keys(code, char, level2_ranks)
                        for anchor_key, anchor_factor in anchor_keys:
                            priority_score = level_score * anchor_factor * rank_multiplier
                            short_candidates_by_level[level].append((priority_score, rank, anchor_key, char, ""))
                        fallback_score = level_score * 0.01 * rank_multiplier
                        short_candidates_by_level[level].append((fallback_score, rank, "", char, "zx"))
                        short_candidates_by_level[level].append((fallback_score, rank, "", char, "xx"))
                        continue
                    if len(code) < level:
                        continue
                    saved_keys = max(len(code) - level, 0)
                    saved_multiplier = saved_keys + 1
                    priority_score = level_score * saved_multiplier * rank_multiplier
                    short_candidates_by_level[level].append((priority_score, rank, code, char, ""))
            if full and len(code) == full_source_length and rank in {2, 3}:
                prefix = "z" if rank == 2 else "x"
                target_code = prefix + code[: full_source_length - 1]
                full_score = full_char_freqs.get(char, 0)
                if full_score < min_score:
                    continue
                if not dedup_prefix_charset_allows(char, charset, score=full_score):
                    continue
                priority_score = full_score * rank_multiplier
                full_candidates.append((priority_score, rank, code, char, target_code))

    prefix_entries: list[PrefixEntry] = []
    allocated_chars = set()
    allocated_codes = set()

    def allocate(candidates: list[PrefixCandidate], *, short_level: int | None = None) -> None:
        candidates.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))
        for priority_score, _, source_code, char, fixed_code in candidates:
            if char in allocated_chars:
                continue
            target_codes = (fixed_code,) if fixed_code else short_prefix_codes(source_code, short_level)
            for new_code in target_codes:
                if new_code in allocated_codes or (char, new_code) in used_text_code:
                    continue
                blocker_freqs = (
                    full_char_freqs
                    if fixed_code and short_level is None
                    else short_level_char_freqs.get(short_level, char_freqs)
                )
                if is_blocked(new_code, blocker_freqs):
                    continue
                prefix_entries.append((len(new_code), (new_code, 1, 0, -int(priority_score), char)))
                used_text_code.add((char, new_code))
                allocated_codes.add(new_code)
                allocated_chars.add(char)
                break

    for level in sorted(short_candidates_by_level):
        allocate(short_candidates_by_level[level], short_level=level)
    allocate(full_candidates)

    return prefix_entries
