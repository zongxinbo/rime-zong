"""
一简（One-Code）方案设计脚本。

本脚本只生成设计报告，不自动覆盖 `one_code.txt`。一简属于人工定稿层：
算法负责给出候选、收益和替换理由，最终是否采用由人工确认。

当前策略：
1. 权重可通过 `--weights` 选择；一简默认使用日常简体优先 `sc`。
2. 普通位先出，`x/z` 只有带参数时才追加到报告末尾：
   - 字根字/首码匹配优先，高频且全码包含该键时允许作为跨位候选；
   - 普通简码难覆盖的长码字会加权；
   - 当前码长为 2、同码候选数 >= 3、且不是首选的字会加权。
3. 简码可得性只看 Cangjie5 源码表：
   - 如果候选字的二码/三码前缀被源码表中的高频原生字占据，说明普通简码更难抢到；
   - 这类字在同频率、同省键收益下优先级更高。
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.cangjie_builder import (
    CANGJIE5_DICT_PATH,
    ONE_CODE_PATH,
    ONE_CODE_REPORT_PATH,
    get_weighted_frequencies,
    is_han_char,
    parse_cangjie_dict,
)
from core.frequency import FREQUENCY_SCORE_SCALE
from core.shortcut_gain import ShortcutGainAnalyzer
from core.weight_profiles import describe_weight_profile, get_weight_profile


DEFAULT_LETTERS = "abcdefghijklmnopqrstuvwy"
SPECIAL_LETTERS = "xz"
TOP_CANDIDATES_PER_KEY = 8
GAIN_CANDIDATES_PER_KEY = 8

ORIGINAL_RADICALS = {
    "a": "日", "b": "月", "c": "金", "d": "木", "e": "水", "f": "火", "g": "土",
    "h": "竹", "i": "戈", "j": "十", "k": "大", "l": "中", "m": "一", "n": "弓",
    "o": "人", "p": "心", "q": "手", "r": "口", "s": "尸", "t": "廿", "u": "山",
    "v": "女", "w": "田", "x": "难", "y": "卜", "z": "重",
}

@dataclass(frozen=True)
class Candidate:
    text: str
    code: str
    score: float
    base_score: float
    saved_keys: int
    kind: str
    note: str
    blockage: str
    actual_gain: int | float | None = None


def load_current_one_codes() -> dict[str, str]:
    current: dict[str, str] = {}
    if not ONE_CODE_PATH.exists():
        return current
    for line in ONE_CODE_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 2:
            current[parts[1]] = parts[0]
    return current


def load_scores(weights: str = "sc") -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    scores = get_weighted_frequencies(get_weight_profile(weights))
    return {
        text: score / FREQUENCY_SCORE_SCALE
        for text, score in scores.items()
    }, {}


def build_code_maps() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    char_codes: dict[str, list[str]] = defaultdict(list)
    code_chars: dict[str, list[str]] = defaultdict(list)
    for entry in parse_cangjie_dict(CANGJIE5_DICT_PATH):
        if not is_han_char(entry.text) or entry.code.startswith(("x", "z")):
            continue
        char_codes[entry.text].append(entry.code)
        if entry.text not in code_chars[entry.code]:
            code_chars[entry.code].append(entry.text)
    return char_codes, code_chars


def shortest_code(char_codes: dict[str, list[str]], text: str) -> str:
    codes = char_codes.get(text, [])
    if not codes:
        return ""
    return min(codes, key=lambda code: (len(code), code))


def code_position(code_chars: dict[str, list[str]], text: str, code: str) -> int:
    chars = code_chars.get(code, [])
    if text not in chars:
        return 0
    return chars.index(text) + 1


def prefix_blockage(
    text: str,
    code: str,
    code_chars: dict[str, list[str]],
    scores: dict[str, float],
) -> tuple[float, str]:
    """基于 Cangjie5 源码表判断普通二三简是否容易被原生字占据。"""
    blocks: list[str] = []
    factor = 1.0
    text_score = scores.get(text, 0.0)

    for prefix_len in (2, 3):
        if len(code) <= prefix_len:
            continue
        prefix = code[:prefix_len]
        chars = code_chars.get(prefix, [])
        if not chars:
            continue
        native = chars[0]
        if native == text:
            continue
        native_score = scores.get(native, 0.0)
        # 源码表中的原生字只要有实际频率，就会增加普通简码抢位难度；
        # 放大强度再按相对频率缩放，避免冷字占位过度影响排序。
        if native_score > 0:
            blocks.append(f"{prefix}:{native}")
            relative = min(max(native_score / max(text_score, 1e-12), 0.20), 1.50)
            base = 0.28 if prefix_len == 2 else 0.18
            factor += base * relative

    return factor, "；".join(blocks)


def build_rank(scores: dict[str, float]) -> dict[str, int]:
    return {
        text: rank
        for rank, text in enumerate(sorted(scores, key=scores.get, reverse=True), start=1)
    }


def shortcut_pressure(
    text: str,
    code: str,
    code_chars: dict[str, list[str]],
) -> tuple[float, str]:
    if len(code) > 3:
        return 1.18, "长码普通简码压力"
    if len(code) == 2:
        group = code_chars.get(code, [])
        pos = code_position(code_chars, text, code)
        if len(group) >= 3 and pos >= 2:
            factor = 1.14 if pos >= 3 else 1.08
            return factor, f"{code} 第 {pos}/{len(group)} 候选"
    return 1.0, ""


def one_key_candidates(
    letter: str,
    char_codes: dict[str, list[str]],
    scores: dict[str, float],
    used_chars: set[str],
    excluded_chars: set[str],
    ranks: dict[str, int],
    current_text: str,
    code_chars: dict[str, list[str]],
    *,
    allow_current: bool,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    radical = ORIGINAL_RADICALS.get(letter)

    for text, codes in char_codes.items():
        if text in excluded_chars or (text in used_chars and text != current_text):
            continue
        base = scores.get(text, 0.0)
        if base <= 0:
            continue

        code = shortest_code(char_codes, text)
        if not code:
            continue

        starts = any(item.startswith(letter) for item in codes)
        ends = any(item.endswith(letter) for item in codes)
        contains = any(letter in item for item in codes)
        is_radical = text == radical
        is_current = allow_current and text == current_text
        saved = max(len(code) - 1, 0)
        pressure_factor, pressure_note = shortcut_pressure(text, code, code_chars)
        if is_current:
            kind = "当前"
            anchor_factor = 1.12
            note = "当前人工定稿"
        elif is_radical:
            kind = "字根"
            anchor_factor = 1.30
            note = "键名字根"
        elif starts or ends:
            kind = "首码" if starts else "末码"
            anchor_factor = 1.15
            note = "全码首/末键匹配"
        elif contains and ranks.get(text, 999999) <= 120:
            kind = "包含"
            anchor_factor = 0.72
            note = "高频跨位，编码含该键"
        else:
            continue

        saved_factor = max(saved, 1)
        blockage_factor, blockage = prefix_blockage(text, code, code_chars, scores)
        note_parts = [note]
        if pressure_note:
            note_parts.append(pressure_note)
        candidates.append(
            Candidate(
                text=text,
                code=code,
                score=base * saved_factor * anchor_factor * blockage_factor * pressure_factor,
                base_score=base,
                saved_keys=saved,
                kind=kind,
                note="；".join(note_parts),
                blockage=blockage,
            )
        )

    candidates.sort(key=lambda item: (-item.score, item.code, item.text))
    top = candidates[:GAIN_CANDIDATES_PER_KEY]
    if current_text and all(item.text != current_text for item in top):
        current = next((item for item in candidates if item.text == current_text), None)
        if current is not None:
            top = top[:-1] + [current]
    return top


def global_key_candidates(
    char_codes: dict[str, list[str]],
    code_chars: dict[str, list[str]],
    scores: dict[str, float],
    excluded_chars: set[str],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for text in char_codes:
        if text in excluded_chars:
            continue
        base = scores.get(text, 0.0)
        if base <= 0:
            continue
        code = shortest_code(char_codes, text)
        if not code:
            continue
        pressure_factor, pressure_note = shortcut_pressure(text, code, code_chars)
        if not pressure_note:
            continue
        saved = max(len(code) - 1, 1)
        blockage_factor, blockage = prefix_blockage(text, code, code_chars, scores)
        candidates.append(
            Candidate(
                text=text,
                code=code,
                score=base * saved * 0.90 * blockage_factor * pressure_factor,
                base_score=base,
                saved_keys=saved,
                kind="全局",
                note=pressure_note,
                blockage=blockage,
            )
        )
    candidates.sort(key=lambda item: (-item.score, item.code, item.text))
    return candidates[:TOP_CANDIDATES_PER_KEY]


def select_one_key_candidate(candidates: list[Candidate], current_text: str) -> Candidate | None:
    if not candidates:
        return None
    if current_text:
        current = next((item for item in candidates if item.text == current_text), None)
        if current is not None:
            return current

    anchors = [item for item in candidates if item.kind in {"字根", "首码"}]
    contains = [item for item in candidates if item.kind == "包含"]

    selected = anchors[0] if anchors else candidates[0]
    if anchors and anchors[0].score > selected.score * 1.15:
        selected = anchors[0]
    if contains and contains[0].score > selected.score * 2.20:
        selected = contains[0]
    return selected


def choose_proposal(
    char_codes: dict[str, list[str]],
    code_chars: dict[str, list[str]],
    scores: dict[str, float],
    current_one: dict[str, str],
    *,
    append_special_xz: bool,
) -> tuple[dict[str, Candidate], dict[str, list[Candidate]]]:
    ranks = build_rank(scores)
    used_chars: set[str] = set()
    proposal: dict[str, Candidate] = {}
    candidates_by_key: dict[str, list[Candidate]] = {}
    default_excluded_chars = {
        current_one.get(letter, "")
        for letter in DEFAULT_LETTERS
        if current_one.get(letter, "")
    }

    for letter in DEFAULT_LETTERS:
        candidates = one_key_candidates(
            letter,
            char_codes,
            scores,
            used_chars,
            set(),
            ranks,
            current_one.get(letter, ""),
            code_chars,
            allow_current=True,
        )
        candidates_by_key[letter] = candidates
        selected = select_one_key_candidate(candidates, current_one.get(letter, ""))
        if selected:
            proposal[letter] = selected
            used_chars.add(selected.text)

    if append_special_xz:
        for letter in SPECIAL_LETTERS:
            candidates = global_key_candidates(
                char_codes,
                code_chars,
                scores,
                default_excluded_chars | used_chars,
            )
            candidates_by_key[letter] = candidates
            selected = select_one_key_candidate(candidates, current_one.get(letter, ""))
            if selected:
                proposal[letter] = selected
                used_chars.add(selected.text)

    return proposal, candidates_by_key


def format_candidate(candidate: Candidate | None) -> str:
    if candidate is None:
        return ""
    return f"{candidate.text} `{candidate.code}` {candidate.kind}"


def add_actual_gains(
    candidates_by_key: dict[str, list[Candidate]],
    analyzer: ShortcutGainAnalyzer,
    current_one: dict[str, str],
) -> dict[str, list[Candidate]]:
    """对静态候选短名单重放真实 S2/S3，并按实际净收益重排。"""
    result: dict[str, list[Candidate]] = {}
    for letter, candidates in candidates_by_key.items():
        evaluated = []
        for candidate in candidates:
            if candidate.text == current_one.get(letter, ""):
                evaluated.append(replace(candidate, actual_gain=0))
                continue
            evaluated.append(
                replace(
                    candidate,
                    actual_gain=analyzer.evaluate_assignment(
                        code=letter,
                        text=candidate.text,
                        layer="one",
                    ).total_gain,
                )
            )
        evaluated.sort(key=lambda item: (-(item.actual_gain or 0), -item.score, item.code, item.text))
        result[letter] = evaluated[:TOP_CANDIDATES_PER_KEY]
    return result


def select_gain_proposal(
    current_one: dict[str, str],
    candidates_by_key: dict[str, list[Candidate]],
) -> dict[str, Candidate]:
    """优先建议真实净收益为正的候选，否则保留当前人工定稿。"""
    proposal: dict[str, Candidate] = {}
    used_chars: set[str] = set()
    for letter, candidates in candidates_by_key.items():
        positive = next(
            (item for item in candidates if (item.actual_gain or 0) > 0 and item.text not in used_chars),
            None,
        )
        current = next(
            (item for item in candidates if item.text == current_one.get(letter, "") and item.text not in used_chars),
            None,
        )
        fallback = next((item for item in candidates if item.text not in used_chars), None)
        selected = positive or current or fallback
        if selected is not None:
            proposal[letter] = selected
            used_chars.add(selected.text)
    return proposal


def write_report(
    current_one: dict[str, str],
    proposal: dict[str, Candidate],
    candidates_by_key: dict[str, list[Candidate]],
    *,
    append_special_xz: bool,
    weights: str,
) -> None:
    lines = [
        "# 一简方案分配对比表",
        "",
        "本表只输出算法建议，不自动覆盖 `one_code.txt`。",
        "",
        "## 策略",
        "",
        f"- 权重模式：`{weights}`。{describe_weight_profile(weights)}。",
        f"- 每键先按静态规则保留 {GAIN_CANDIDATES_PER_KEY} 个候选，再调用 `shortcut_gain.py` 重放真实 S2/S3，按实际净收益排序输出前 {TOP_CANDIDATES_PER_KEY} 个。",
        "- 默认先出普通位，`x/z` 仅在追加模式下放到报告末尾。",
        "- 普通位统一按简繁混合频率、省键收益、按键记忆锚点、源码表前缀占位和多候选二码压力评分。",
        "- 字根字/首码匹配优先；高频包含键位可跨位；普通简码难覆盖的字获得加权。",
        "- 简码可得性：只看 `cangjie5.dict.yaml` 源码表；二码/三码前缀若被高频原生字占据，则提高候选优先级。",
        "- 当前正式版来自 `one_code.txt`，最终是否采用建议仍需人工定稿。",
        "",
        "## 总览",
        "",
        "| 键位 | 字根 | 当前正式版 | 建议 | 变化 |",
        "|---|---|---|---|---|",
    ]

    for letter in DEFAULT_LETTERS:
        current = current_one.get(letter, "")
        cand = proposal.get(letter)
        suggested = cand.text if cand else ""
        change = "" if current == suggested else f"{current or '-'} -> {suggested or '-'}"
        lines.append(
            f"| {letter} | {ORIGINAL_RADICALS.get(letter, '')} | {current} | "
            f"{format_candidate(cand)} | {change} |"
        )

    lines.extend(["", "## 候选明细", ""])

    for letter in DEFAULT_LETTERS:
        lines.extend([
            f"### {letter}",
            "",
            "| Rank | 字 | 当前码 | 实际净收益 | 静态 Score | 频率分 | 省键 | 类型 | 前缀占位 | 说明 |",
            "|---:|---|---|---:|---:|---:|---:|---|---|---|",
        ])
        for rank, candidate in enumerate(candidates_by_key.get(letter, []), start=1):
            lines.append(
                f"| {rank} | {candidate.text} | `{candidate.code}` | "
                f"{candidate.actual_gain or 0:+g} | {candidate.score:.8g} | {candidate.base_score:.8g} | "
                f"{candidate.saved_keys} | {candidate.kind} | {candidate.blockage} | {candidate.note} |"
            )
        lines.append("")

    if append_special_xz:
        lines.extend([
            "",
            "## 追加位",
            "",
            "| 键位 | 字根 | 当前正式版 | 建议 | 变化 |",
            "|---|---|---|---|---|",
        ])
        for letter in SPECIAL_LETTERS:
            current = current_one.get(letter, "")
            cand = proposal.get(letter)
            suggested = cand.text if cand else ""
            change = "" if current == suggested else f"{current or '-'} -> {suggested or '-'}"
            lines.append(
                f"| {letter} | {ORIGINAL_RADICALS.get(letter, '')} | {current} | "
                f"{format_candidate(cand)} | {change} |"
            )
        lines.append("")
        for letter in SPECIAL_LETTERS:
            lines.extend([
                f"### {letter}",
                "",
                "| Rank | 字 | 当前码 | 实际净收益 | 静态 Score | 频率分 | 省键 | 类型 | 前缀占位 | 说明 |",
                "|---:|---|---|---:|---:|---:|---:|---|---|---|",
            ])
            for rank, candidate in enumerate(candidates_by_key.get(letter, []), start=1):
                lines.append(
                    f"| {rank} | {candidate.text} | `{candidate.code}` | "
                    f"{candidate.actual_gain or 0:+g} | {candidate.score:.8g} | {candidate.base_score:.8g} | "
                    f"{candidate.saved_keys} | {candidate.kind} | {candidate.blockage} | {candidate.note} |"
                )
            lines.append("")

    ONE_CODE_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="生成一简设计报告")
    parser.add_argument("--append-xz", action="store_true", help="将 x/z 追加到报告末尾")
    parser.add_argument("--weights", choices=("sc", "sc_balanced"), default="sc",
                        help="权重模式：sc=日常简体优先，sc_balanced=简繁平衡；默认 sc")
    parser.add_argument("--gain-candidates-per-key", type=int, default=8,
                        help="每键进入真实 S2/S3 重放的静态候选数；默认 8，调大可深扫但耗时线性增加")
    args = parser.parse_args()
    if args.gain_candidates_per_key <= 0:
        parser.error("--gain-candidates-per-key 必须大于 0")
    global GAIN_CANDIDATES_PER_KEY
    GAIN_CANDIDATES_PER_KEY = args.gain_candidates_per_key

    current_one = load_current_one_codes()
    scores, _ = load_scores(args.weights)
    char_codes, code_chars = build_code_maps()
    _, candidates_by_key = choose_proposal(
        char_codes,
        code_chars,
        scores,
        current_one,
        append_special_xz=args.append_xz,
    )
    analyzer = ShortcutGainAnalyzer(weights=args.weights)
    candidates_by_key = add_actual_gains(candidates_by_key, analyzer, current_one)
    proposal = select_gain_proposal(current_one, candidates_by_key)
    write_report(
        current_one,
        proposal,
        candidates_by_key,
        append_special_xz=args.append_xz,
        weights=args.weights,
    )
    print(f"一简设计报告已保存: {ONE_CODE_REPORT_PATH}")
    print("一简方案原型不自动更新；如需定稿，请人工修改 one_code.txt")


if __name__ == "__main__":
    main()
