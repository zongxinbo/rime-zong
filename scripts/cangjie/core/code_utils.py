from __future__ import annotations

from collections import defaultdict

from .paths import DEFAULT_FULLCODE_YIELD_MIN_SCORE


def project_code(code: str, max_code_length: int) -> str:
    if len(code) <= max_code_length:
        return code
    return code[: max_code_length - 1] + code[-1]


def build_fullcode_yield_order(
    entries: list[tuple[str, str, int]],
    shortcut_chars: set[str],
    min_promote_score: float = DEFAULT_FULLCODE_YIELD_MIN_SCORE,
) -> dict[tuple[str, str], int]:
    """计算全码候选位次：有简码的首选让位给未获简码的常用字。"""

    code_groups: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for entry in entries:
        code_groups[entry[1]].append(entry)

    order: dict[tuple[str, str], int] = {}
    for group in code_groups.values():
        yielded = sorted(group, key=lambda entry: (-entry[2], entry[0]))
        if yielded and yielded[0][0] in shortcut_chars:
            promoted_idx = -1
            for index, entry in enumerate(yielded[1:], start=1):
                if entry[0] not in shortcut_chars and entry[2] >= min_promote_score:
                    promoted_idx = index
                    break
            if promoted_idx > 0:
                promoted = yielded.pop(promoted_idx)
                yielded.insert(0, promoted)

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
