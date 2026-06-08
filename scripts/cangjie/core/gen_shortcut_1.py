"""
一简（One-Code）方案设计脚本。

本脚本只生成设计报告，不自动覆盖 `one_code.txt`。一简属于人工定稿层：
算法负责给出候选、收益和替换理由，最终是否采用由人工确认。

当前策略：
1. 权重可通过 `--weights` 选择；一简默认使用日常简体优先 `sc`。
2. 普通位先出，`x/z` 只有带参数时才追加到报告末尾：
   - 字根字/首码匹配优先，高频且全码包含该键时允许作为跨位候选；
   - `a-z` 一简只按日常字频和记忆锚点评分，主推荐目标可用 `--objective` 切换；
   - `x/z` 没有普通仓颉锚点，普通位定案后重新生成全局候选，并按真实净收益分配。
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
from core.glyph_codes import filter_glyph_preferred_entries
from core.shortcut_gain import ShortcutGainAnalyzer
from core.weight_profiles import describe_weight_profile, get_weight_profile


DEFAULT_LETTERS = "abcdefghijklmnopqrstuvwy"
SPECIAL_LETTERS = "xz"
TOP_CANDIDATES_PER_KEY = 8
GAIN_CANDIDATES_PER_KEY = 8
DEFAULT_S2_COUNT = 300
DEFAULT_S3_COUNT = 1300
MNEMONIC_GAIN_BREAKTHROUGH_MIN = 2_000_000
OBJECTIVES = ("mnemonic", "hybrid", "gain")

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


ANCHOR_PRIORITIES = {
    "字根": 3,
    "首码": 2,
    "末码": 1,
    "包含": 0,
    "全局": -1,
}

OBJECTIVE_DESCRIPTIONS = {
    "mnemonic": "记忆锚点优先：锚点等级 > 显著净收益突破 > 当前方案稳定性 > 日常频率 > 实际净收益",
    "hybrid": "混合模式：锚点等级 > 实际净收益 > 日常频率",
    "gain": "净收益优先：实际净收益 > 锚点等级 > 日常频率",
}


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


def build_code_maps(weights: str = "sc") -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    char_codes: dict[str, list[str]] = defaultdict(list)
    code_chars: dict[str, list[str]] = defaultdict(list)
    entries = filter_glyph_preferred_entries(
        parse_cangjie_dict(CANGJIE5_DICT_PATH),
        weights,
    )
    for entry in entries:
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


def prefix_blockage_note(
    text: str,
    code: str,
    code_chars: dict[str, list[str]],
    scores: dict[str, float],
) -> str:
    """基于 Cangjie5 源码表判断普通二三简是否容易被原生字占据。"""
    blocks: list[str] = []

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
        # 一简不把这个因素混入静态评分，只在报告中展示供人工判断。
        if native_score > 0:
            blocks.append(f"{prefix}:{native}")

    return "；".join(blocks)


def build_rank(scores: dict[str, float]) -> dict[str, int]:
    return {
        text: rank
        for rank, text in enumerate(sorted(scores, key=scores.get, reverse=True), start=1)
    }


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
        if is_radical:
            kind = "字根"
            anchor_factor = 1.30
            note = "键名字根"
        elif starts:
            kind = "首码"
            anchor_factor = 1.15
            note = "全码首/末键匹配"
        elif ends:
            kind = "末码"
            anchor_factor = 1.05
            note = "全码首/末键匹配"
        elif contains and ranks.get(text, 999999) <= 120:
            kind = "包含"
            anchor_factor = 0.72
            note = "高频跨位，编码含该键"
        else:
            continue

        if is_current:
            note = f"当前人工定稿；{note}"

        blockage = prefix_blockage_note(text, code, code_chars, scores)
        candidates.append(
            Candidate(
                text=text,
                code=code,
                score=base * anchor_factor,
                base_score=base,
                saved_keys=saved,
                kind=kind,
                note=note,
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


def global_frequency_candidates(
    char_codes: dict[str, list[str]],
    code_chars: dict[str, list[str]],
    scores: dict[str, float],
    excluded_chars: set[str],
    current_text: str = "",
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for text in char_codes:
        if text in excluded_chars and text != current_text:
            continue
        base = scores.get(text, 0.0)
        if base <= 0:
            continue
        code = shortest_code(char_codes, text)
        if not code:
            continue
        saved = max(len(code) - 1, 0)
        blockage = prefix_blockage_note(text, code, code_chars, scores)
        candidates.append(
            Candidate(
                text=text,
                code=code,
                score=base,
                base_score=base,
                saved_keys=saved,
                kind="全局",
                note="无普通仓颉锚点，按日常频率",
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
) -> tuple[dict[str, Candidate], dict[str, list[Candidate]]]:
    ranks = build_rank(scores)
    used_chars: set[str] = set()
    proposal: dict[str, Candidate] = {}
    candidates_by_key: dict[str, list[Candidate]] = {}

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


def actual_gain(candidate: Candidate) -> int | float:
    return candidate.actual_gain or 0


def proposal_sort_key(
    letter: str,
    candidate: Candidate,
    objective: str,
    *,
    current_text: str | None = None,
) -> tuple:
    anchor_priority = ANCHOR_PRIORITIES.get(candidate.kind, -2)
    gain = actual_gain(candidate)
    if objective == "gain":
        return (-gain, -anchor_priority, -candidate.base_score, -candidate.score, letter, candidate.text)
    if objective == "hybrid":
        return (-anchor_priority, -gain, -candidate.base_score, -candidate.score, letter, candidate.text)
    breakthrough = gain >= MNEMONIC_GAIN_BREAKTHROUGH_MIN
    incumbent = current_text is not None and candidate.text == current_text
    return (
        -anchor_priority,
        not breakthrough,
        not incumbent if not breakthrough else False,
        -candidate.saved_keys if breakthrough else 0,
        -gain if breakthrough else 0,
        -candidate.base_score,
        -candidate.score,
        letter,
        candidate.text,
    )


def select_gain_proposal(
    current_one: dict[str, str],
    candidates_by_key: dict[str, list[Candidate]],
    *,
    objective: str,
) -> dict[str, Candidate]:
    """跨键分配唯一主推荐，避免同一个字同时占据多个 Rank 1。"""
    proposal: dict[str, Candidate] = {}
    used_keys: set[str] = set()
    used_chars: set[str] = set()
    placements = [
        (letter, item)
        for letter, candidates in candidates_by_key.items()
        for item in candidates
        if (
                item.text == current_one.get(letter, "")
                or actual_gain(item) > 0
        )
    ]
    placements.sort(
        key=lambda placement: proposal_sort_key(
            placement[0],
            placement[1],
            objective,
            current_text=current_one.get(placement[0]),
        )
    )

    for letter, item in placements:
        if letter in used_keys or item.text in used_chars:
            continue
        proposal[letter] = item
        used_keys.add(letter)
        used_chars.add(item.text)

    # 某些键的高分候选可能已在更合理的键位被占用；为这些键补上剩余最佳候选。
    for letter, candidates in candidates_by_key.items():
        if letter in used_keys:
            continue
        eligible = [
            item
            for item in candidates
            if (
                item.text not in used_chars
                and (
                    item.text == current_one.get(letter, "")
                    or actual_gain(item) > 0
                )
            )
        ]
        selected = min(
            eligible,
            key=lambda item: proposal_sort_key(
                letter,
                item,
                objective,
                current_text=current_one.get(letter),
            ),
            default=None,
        )
        if selected is not None:
            proposal[letter] = selected
            used_keys.add(letter)
            used_chars.add(selected.text)
    return proposal


def rank_report_candidates(
    candidates_by_key: dict[str, list[Candidate]],
    proposal: dict[str, Candidate],
) -> dict[str, list[Candidate]]:
    """把全局唯一主推荐移动到 Rank 1，其余候选保留原有相对顺序。"""
    ranked: dict[str, list[Candidate]] = {}
    for letter, candidates in candidates_by_key.items():
        selected = proposal.get(letter)
        if selected is None:
            ranked[letter] = candidates
            continue
        ranked[letter] = [selected] + [item for item in candidates if item.text != selected.text]
    return ranked


def write_report(
    current_one: dict[str, str],
    proposal: dict[str, Candidate],
    candidates_by_key: dict[str, list[Candidate]],
    *,
    append_special_xz: bool,
    weights: str,
    blind: bool,
    objective: str,
    s2_count: int,
    s3_count: int,
    output_path: Path,
) -> None:
    lines = [
        "# 一简方案分配对比表",
        "",
        "本表只输出算法建议，不自动覆盖 `one_code.txt`。",
        "",
        "## 策略",
        "",
        f"- 权重模式：`{weights}`。{describe_weight_profile(weights)}。",
        f"- 决策模式：`{'blind replacement audit' if blind else 'calibration'}`。"
        + ("当前正式版不参与候选保底；若凭自身频率和锚点自然进入短名单，则以收益 `0` 的基线正常参与主推荐排序。"
           if blind else "当前正式版作为收益基线，并保留校准候选资格。"),
        f"- 主推荐目标：`{objective}`。{OBJECTIVE_DESCRIPTIONS[objective]}。",
        f"- 每键先按静态规则保留 {GAIN_CANDIDATES_PER_KEY} 个候选，再调用 `shortcut_gain.py` 重放真实 S2/S3（S2={s2_count}，S3={s3_count}），按实际净收益排序输出前 {TOP_CANDIDATES_PER_KEY} 个。",
        "- 总览建议采用一简专用决策层：跨键全局分配唯一主推荐；当前正式版以收益 `0` 作为基线参与比较。锚点等级为 `字根 > 首码 > 尾码 > 包含码 > 全局`。",
        f"- `mnemonic` 的显著净收益突破门槛为 {MNEMONIC_GAIN_BREAKTHROUGH_MIN:,}；只在同锚点等级内生效，并优先考虑省键数更大的候选。",
        "- 同一个字只能在最合理的键位占据一次 `Rank 1`；它仍可保留在其他键位的 `Rank 2+`，供人工比较。",
        "- 默认先出普通位，`x/z` 仅在追加模式下放到报告末尾。",
        "- `a-z` 一简只按日常字频和按键记忆锚点评分，不加入码长、重码或前缀占位救援权重。",
        "- 字根字/首码匹配优先；高频包含键位可跨位。真实 S2/S3 重放仍用于展示副作用和排除负收益替换。",
        "- `x/z` 没有普通仓颉锚点，追加时在普通位定案后重新生成全局候选，并固定按实际净收益优先分配；普通二三四简和自动消重层不受影响。",
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
        if blind and cand is None:
            change = "无正收益替换"
        else:
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
        rank_start = 1 if letter in proposal else 2
        for rank, candidate in enumerate(candidates_by_key.get(letter, []), start=rank_start):
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
            if blind and cand is None:
                change = "无正收益替换"
            else:
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
            rank_start = 1 if letter in proposal else 2
            for rank, candidate in enumerate(candidates_by_key.get(letter, []), start=rank_start):
                lines.append(
                    f"| {rank} | {candidate.text} | `{candidate.code}` | "
                    f"{candidate.actual_gain or 0:+g} | {candidate.score:.8g} | {candidate.base_score:.8g} | "
                    f"{candidate.saved_keys} | {candidate.kind} | {candidate.blockage} | {candidate.note} |"
                )
            lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="生成一简设计报告")
    parser.add_argument("--append-xz", action="store_true", help="将 x/z 追加到报告末尾")
    parser.add_argument("--weights", choices=("sc", "sc_daily", "sc_balanced"), default="sc",
                        help="权重模式：sc=现代简体日用优化，sc_daily=简繁日常通用，sc_balanced=简繁平衡；默认 sc")
    parser.add_argument("--gain-candidates-per-key", type=int, default=8,
                        help="每键进入真实 S2/S3 重放的静态候选数；默认 8，调大可深扫但耗时线性增加")
    parser.add_argument("--objective", choices=OBJECTIVES, default="mnemonic",
                        help="主推荐目标：mnemonic=记忆锚点优先，hybrid=锚点内净收益优先，gain=净收益优先；默认 mnemonic")
    parser.add_argument("--s2-count", type=int, default=DEFAULT_S2_COUNT,
                        help=f"真实重放二简数量；默认 {DEFAULT_S2_COUNT}，与生产构建一致")
    parser.add_argument("--s3-count", type=int, default=DEFAULT_S3_COUNT,
                        help=f"真实重放三简数量；默认 {DEFAULT_S3_COUNT}，与生产构建一致")
    parser.add_argument("--blind", action="store_true",
                        help="盲测模式：当前正式版仅作为收益基线和报告对照，不参与候选保底或主推荐排序")
    parser.add_argument("--output", type=Path, default=ONE_CODE_REPORT_PATH,
                        help=f"报告输出路径；默认 {ONE_CODE_REPORT_PATH}")
    args = parser.parse_args()
    if args.gain_candidates_per_key <= 0:
        parser.error("--gain-candidates-per-key 必须大于 0")
    if args.s2_count <= 0:
        parser.error("--s2-count 必须大于 0")
    if args.s3_count <= 0:
        parser.error("--s3-count 必须大于 0")
    global GAIN_CANDIDATES_PER_KEY
    GAIN_CANDIDATES_PER_KEY = args.gain_candidates_per_key

    current_one = load_current_one_codes()
    decision_current = {} if args.blind else current_one
    scores, _ = load_scores(args.weights)
    char_codes, code_chars = build_code_maps(args.weights)
    _, candidates_by_key = choose_proposal(
        char_codes,
        code_chars,
        scores,
        decision_current,
    )
    analyzer = ShortcutGainAnalyzer(weights=args.weights, s2_count=args.s2_count, s3_count=args.s3_count)
    candidates_by_key = add_actual_gains(candidates_by_key, analyzer, current_one)
    proposal = select_gain_proposal(
        current_one,
        {
            letter: candidates_by_key[letter]
            for letter in DEFAULT_LETTERS
            if letter in candidates_by_key
        },
        objective=args.objective,
    )
    if args.append_xz:
        used_chars = {candidate.text for candidate in proposal.values()}
        special_candidates = {
            letter: global_frequency_candidates(
                char_codes,
                code_chars,
                scores,
                used_chars,
                current_one.get(letter, ""),
            )
            for letter in SPECIAL_LETTERS
        }
        special_candidates = add_actual_gains(special_candidates, analyzer, current_one)
        candidates_by_key.update(special_candidates)
        proposal.update(select_gain_proposal(current_one, special_candidates, objective="gain"))
    candidates_by_key = rank_report_candidates(candidates_by_key, proposal)
    write_report(
        current_one,
        proposal,
        candidates_by_key,
        append_special_xz=args.append_xz,
        weights=args.weights,
        blind=args.blind,
        objective=args.objective,
        s2_count=args.s2_count,
        s3_count=args.s3_count,
        output_path=args.output,
    )
    print(f"一简设计报告已保存: {args.output}")
    print("一简方案原型不自动更新；如需定稿，请人工修改 one_code.txt")


if __name__ == "__main__":
    main()
