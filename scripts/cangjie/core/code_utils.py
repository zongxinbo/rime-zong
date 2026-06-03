from __future__ import annotations

from collections import defaultdict

from .charset import is_common_han_char
from .paths import DEFAULT_FULLCODE_YIELD_MIN_SCORE


def project_code(code: str, max_code_length: int) -> str:
    if len(code) <= max_code_length:
        return code
    return code[: max_code_length - 1] + code[-1]


def build_fullcode_yield_order(
    entries: list[tuple[str, str, int]],
    shortcut_entries: list[tuple[str, str, int | float]],
    min_promote_score: float = DEFAULT_FULLCODE_YIELD_MIN_SCORE,
) -> dict[tuple[str, str], int]:
    """计算全码候选位次：有简码的首选让位给未获简码的常用字。"""

    code_groups: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for entry in entries:
        code_groups[entry[1]].append(entry)

    yielding_shortcuts: dict[str, list[str]] = defaultdict(list)
    for char, shortcut_code, priority in shortcut_entries:
        # fixed_prefix(z?/x?) 是重码救援层，不影响原全码候选顺序。
        if priority >= 1 and priority != 1.5:
            yielding_shortcuts[char].append(shortcut_code)

    def has_related_shortcut(char: str, full_code: str) -> bool:
        for shortcut_code in yielding_shortcuts.get(char, []):
            if len(shortcut_code) >= len(full_code):
                continue
            if len(shortcut_code) == 1:
                return True
            if full_code.startswith(shortcut_code):
                return True
        return False

    order: dict[tuple[str, str], int] = {}
    for group in code_groups.values():
        yielded = sorted(group, key=lambda entry: (-entry[2], entry[0]))
        if any(has_related_shortcut(char, code) for char, code, _ in yielded):
            yielded = sorted(
                yielded,
                key=lambda entry: (
                    not is_common_han_char(entry[0]),
                    has_related_shortcut(entry[0], entry[1]),
                    -entry[2],
                    entry[0],
                ),
            )

        for rank, (char, code, _) in enumerate(yielded):
            order[(char, code)] = rank
    return order


def build_shortcut_leader_chars(entries: list[tuple[str, int, int, int, str]]) -> set[str]:
    """返回已经拥有首选简码入口的字。"""

    leaders: set[str] = set()
    code_groups: dict[str, list[tuple[str, int, int, int, str]]] = defaultdict(list)
    for entry in entries:
        code_groups[entry[0]].append(entry)

    for group in code_groups.values():
        first = group[0]
        if first[1] < 5:
            leaders.add(first[4])
    return leaders
