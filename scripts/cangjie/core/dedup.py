from __future__ import annotations

from collections import defaultdict

from .charset import is_gb2312, is_gbk


DictEntry = tuple[str, int | float, int, int, str]
RankSuffix = tuple[int, str]


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
) -> list[DictEntry]:
    """为满码长重码字分配自然可推导的 z/x 前缀直达码。"""
    if min_score < 0:
        raise ValueError("--dedup-prefix-min-score 不能为负数")
    if charset not in {"all", "frequency", "gbk", "gb2312"}:
        raise ValueError("--dedup-prefix-charset 只能是 all、frequency、gbk 或 gb2312")

    code_groups: dict[str, list[DictEntry]] = defaultdict(list)
    for entry in all_entries:
        code_groups[entry[0]].append(entry)

    candidates = []
    for code, entries in code_groups.items():
        if code.startswith(("z", "x")) or len(code) < max_code_length:
            continue

        for rank, entry in enumerate(unique_seen_entries(entries)[1:], start=2):
            char = entry[4]
            score = char_freqs.get(char, 0)
            if char in shortcut_leader_chars or score < min_score:
                continue
            if not dedup_prefix_charset_allows(char, charset, score=score):
                continue
            candidates.append((score, rank, code, char))

    # 高频字优先占用有限的自然前缀码；同分时优先解决候选位次更靠前的字。
    candidates.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))

    prefix_entries: list[DictEntry] = []
    occupied_source = all_entries if occupied_entries is None else occupied_entries
    occupied_codes = {entry[0] for entry in occupied_source}
    allocated_chars = set()
    for score, _, source_code, char in candidates:
        if char in allocated_chars:
            continue
        for new_code in natural_dedup_prefix_codes(source_code):
            if new_code in occupied_codes or (char, new_code) in used_text_code:
                continue
            prefix_entries.append((new_code, 1, 0, -score, char))
            used_text_code.add((char, new_code))
            occupied_codes.add(new_code)
            allocated_chars.add(char)
            break

    return prefix_entries
