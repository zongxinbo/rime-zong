#!/usr/bin/env python3
"""按真实后续分层评估固定简码的净码长收益。

本模块用于人工定稿层，不直接写入任何原型文件。它会按生产顺序重建：

    root_code -> one_code -> fixed_prefix_code -> S2 -> S3 -> 全码

因此既能评估一码替换，也能复用于后续 z?/x? 固定二码的新增或替换。
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.charset import is_common_han_char, shortcut_charset_allows
from core.frequency import get_weighted_frequencies
from core.glyph_codes import filter_glyph_preferred_entries
from core.io import parse_cangjie_dict
from core.paths import (
    CANGJIE5_DICT_PATH,
    FIXED_PREFIX_CODE_PATH,
    ONE_CODE_PATH,
    ROOT_CODE_PATH,
)
from core.weight_profiles import get_weight_profile


@dataclass(frozen=True)
class ShortcutLayers:
    one_codes: dict[str, str]
    fixed_prefix_codes: dict[str, str]
    two_codes: dict[str, str]
    three_codes: dict[str, str]


@dataclass(frozen=True)
class GainChange:
    text: str
    score: int | float
    before: str
    after: str
    gain: int | float


@dataclass(frozen=True)
class GainResult:
    code: str
    text: str
    replaced_text: str
    total_gain: int | float
    direct_gain: int | float
    indirect_gain: int | float
    changes: tuple[GainChange, ...]


def load_code_text_map(path: Path) -> dict[str, str]:
    """读取原型文件，返回 code -> text。"""
    entries: dict[str, str] = {}
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 2 and parts[0] and not parts[0].startswith("#"):
            text, code = parts
            entries[code] = text
    return entries


class ShortcutGainAnalyzer:
    """重建普通二三码层，并计算固定简码变更后的实际净收益。"""

    def __init__(
        self,
        *,
        char_scores: dict[str, int | float] | None = None,
        weights: str = "sc_daily",
        protect_native: bool = True,
        protect_native_charset: str = "gbk",
        protect_native_min_score: int | float = 3000,
        shortcut_candidate_min_score: int | float = 3000,
        s2_count: int = 300,
        s3_count: int = 1300,
    ) -> None:
        self.weights = weights
        self.char_scores = char_scores or get_weighted_frequencies(get_weight_profile(weights))
        self.protect_native = protect_native
        self.protect_native_charset = protect_native_charset
        self.protect_native_min_score = protect_native_min_score
        self.shortcut_candidate_min_score = shortcut_candidate_min_score
        self.s2_count = s2_count
        self.s3_count = s3_count

        self.root_codes = load_code_text_map(ROOT_CODE_PATH)
        self.base_one_codes = load_code_text_map(ONE_CODE_PATH)
        self.base_fixed_prefix_codes = load_code_text_map(FIXED_PREFIX_CODE_PATH)

        self.shortest_full_codes: dict[str, str] = {}
        self.full_code_chars: dict[str, list[str]] = defaultdict(list)
        entries = filter_glyph_preferred_entries(
            parse_cangjie_dict(CANGJIE5_DICT_PATH),
            weights,
        )
        for entry in entries:
            if not is_common_han_char(entry.text) or entry.code.startswith(("x", "z")):
                continue
            if entry.text not in self.full_code_chars[entry.code]:
                self.full_code_chars[entry.code].append(entry.text)
            if entry.text in self.root_codes.values() and len(entry.code) == 1:
                continue
            current = self.shortest_full_codes.get(entry.text)
            if current is None or len(entry.code) < len(current):
                self.shortest_full_codes[entry.text] = entry.code

        self.char_depths: dict[str, int] = {}
        for chars in self.full_code_chars.values():
            sorted_chars = sorted(chars, key=lambda text: self.char_scores.get(text, 0), reverse=True)
            for index, text in enumerate(sorted_chars, start=1):
                self.char_depths[text] = index

        self.base_layers = self.build_layers(self.base_one_codes, self.base_fixed_prefix_codes)
        self.universe = (
            set(self.char_scores)
            | set(self.shortest_full_codes)
            | set(self.root_codes.values())
            | set(self.base_one_codes.values())
            | set(self.base_fixed_prefix_codes.values())
        )
        self.base_shortest_paths = self.build_shortest_paths(self.base_layers)

    def _native_is_protected(self, text: str, score: int | float) -> bool:
        return (
            self.protect_native
            and shortcut_charset_allows(text, self.protect_native_charset, score=score)
            and score >= self.protect_native_min_score
        )

    def _generate_shortcuts(
        self,
        *,
        length: int,
        excluded_chars: set[str],
        occupied_codes: set[str],
        count: int,
    ) -> dict[str, str]:
        native_penalty_ratio = 1.5 if length == 2 else 1.2
        groups: dict[str, dict[str, object]] = defaultdict(lambda: {"native": None, "long": []})

        for text, full_code in self.shortest_full_codes.items():
            score = self.char_scores.get(text, 0)
            if len(full_code) == length:
                native = groups[full_code]["native"]
                if native is None or score > native[1]:
                    groups[full_code]["native"] = (text, score)
            elif len(full_code) > length and score >= self.shortcut_candidate_min_score:
                if text in excluded_chars:
                    continue
                groups[full_code[:length]]["long"].append((text, score, len(full_code)))

        valid: list[tuple[str, str, int | float]] = []
        for code, group in groups.items():
            long_items = group["long"]
            if code in occupied_codes or not long_items:
                continue

            native_penalty = 0
            native = group["native"]
            if native is not None:
                native_text, native_score = native
                if self._native_is_protected(native_text, native_score):
                    continue
                native_penalty = native_score * native_penalty_ratio

            best: tuple[str, str, int | float] | None = None
            for text, score, full_length in long_items:
                saved_keys = full_length - length
                net_gain = score * saved_keys - native_penalty
                if net_gain > 0 and (best is None or net_gain > best[2]):
                    best = (text, code, net_gain)
            if best is not None:
                valid.append(best)

        valid.sort(key=lambda item: item[2], reverse=True)
        if count > 0:
            valid = valid[:count]
        return {code: text for text, code, _ in valid}

    def build_layers(
        self,
        one_codes: dict[str, str],
        fixed_prefix_codes: dict[str, str],
    ) -> ShortcutLayers:
        early_maps = (self.root_codes, one_codes, fixed_prefix_codes)
        excluded_chars = {text for entries in early_maps for text in entries.values()}
        occupied_two_codes = {
            code
            for entries in early_maps
            for code in entries
            if len(code) == 2
        }
        two_codes = self._generate_shortcuts(
            length=2,
            excluded_chars=excluded_chars,
            occupied_codes=occupied_two_codes,
            count=self.s2_count,
        )

        excluded_chars.update(two_codes.values())
        occupied_three_codes = {
            code
            for entries in (*early_maps, two_codes)
            for code in entries
            if len(code) == 3
        }
        three_codes = self._generate_shortcuts(
            length=3,
            excluded_chars=excluded_chars,
            occupied_codes=occupied_three_codes,
            count=self.s3_count,
        )
        return ShortcutLayers(dict(one_codes), dict(fixed_prefix_codes), two_codes, three_codes)

    def shortest_path(self, text: str, layers: ShortcutLayers) -> str:
        codes: list[str] = []
        for entries in (
            self.root_codes,
            layers.one_codes,
            layers.fixed_prefix_codes,
            layers.two_codes,
            layers.three_codes,
        ):
            codes.extend(code for code, entry_text in entries.items() if entry_text == text)
        full_code = self.shortest_full_codes.get(text)
        if full_code:
            codes.append(full_code)
        return min(codes, key=lambda code: (len(code), code)) if codes else ""

    def build_shortest_paths(self, layers: ShortcutLayers) -> dict[str, str]:
        """一次性构建 text -> 最短可用路径，供批量收益差分快速查询。"""
        paths = dict(self.shortest_full_codes)
        for entries in (
            self.root_codes,
            layers.one_codes,
            layers.fixed_prefix_codes,
            layers.two_codes,
            layers.three_codes,
        ):
            for code, text in entries.items():
                current = paths.get(text)
                if current is None or (len(code), code) < (len(current), current):
                    paths[text] = code
        return paths

    def evaluate_assignment(self, *, code: str, text: str, layer: str) -> GainResult:
        """评估固定码位新增或替换。

        layer 取 `one` 或 `fixed-prefix`。已有目标码位会被替换；空码位会新增。
        """
        if layer not in {"one", "fixed-prefix"}:
            raise ValueError("layer 只能是 one 或 fixed-prefix")
        if layer == "one" and len(code) != 1:
            raise ValueError("one 层只能评估一码")
        if layer == "fixed-prefix" and len(code) != 2:
            raise ValueError("fixed-prefix 层只能评估二码")

        one_codes = dict(self.base_one_codes)
        fixed_prefix_codes = dict(self.base_fixed_prefix_codes)
        target = one_codes if layer == "one" else fixed_prefix_codes
        replaced_text = target.get(code, "")
        if layer == "fixed-prefix" and text in one_codes.values():
            raise ValueError(f"{text} 已在 one 层占用，不能重复写入 fixed-prefix")
        for existing_code, existing_text in list(target.items()):
            if existing_code != code and existing_text == text:
                del target[existing_code]
        if layer == "one":
            for existing_code, existing_text in list(fixed_prefix_codes.items()):
                if existing_text == text:
                    del fixed_prefix_codes[existing_code]
        target[code] = text
        changed_layers = self.build_layers(one_codes, fixed_prefix_codes)
        changed_paths = self.build_shortest_paths(changed_layers)

        changes: list[GainChange] = []
        total_gain: int | float = 0
        universe = self.universe | {text}
        for current_text in universe:
            before = self.base_shortest_paths.get(current_text, "")
            after = changed_paths.get(current_text, "")
            gain = self.char_scores.get(current_text, 0) * (len(before) - len(after))
            if gain:
                changes.append(GainChange(current_text, self.char_scores.get(current_text, 0), before, after, gain))
                total_gain += gain

        direct_chars = {text}
        if replaced_text:
            direct_chars.add(replaced_text)
        direct_gain = sum(change.gain for change in changes if change.text in direct_chars)
        changes.sort(key=lambda change: abs(change.gain), reverse=True)
        return GainResult(
            code=code,
            text=text,
            replaced_text=replaced_text,
            total_gain=total_gain,
            direct_gain=direct_gain,
            indirect_gain=total_gain - direct_gain,
            changes=tuple(changes),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="评估固定简码新增或替换后的真实净码长收益")
    parser.add_argument("--layer", choices=("one", "fixed-prefix"), required=True)
    parser.add_argument("--code", required=True, help="目标简码，例如 t、za、xp")
    parser.add_argument("--char", required=True, help="拟写入目标码位的单字")
    parser.add_argument("--top-changes", type=int, default=10, help="输出影响最大的逐字变化数量")
    parser.add_argument("--weights", choices=("sc", "sc_daily", "sc_balanced"), default=None,
                        help="权重模式；默认 one=sc，fixed-prefix=sc_daily")
    parser.add_argument("--protect-native-charset", choices=("all", "frequency", "gbk", "gb2312"), default="gbk")
    parser.add_argument("--protect-native-min-score", type=float, default=3000)
    parser.add_argument("--shortcut-candidate-min-score", type=float, default=3000)
    parser.add_argument("--s2-count", type=int, default=300, help="重放二简数量；默认 300，与生产构建默认一致")
    parser.add_argument("--s3-count", type=int, default=1300, help="重放三简数量；默认 1300，与生产构建默认一致")
    args = parser.parse_args()
    if args.s2_count <= 0:
        parser.error("--s2-count 必须大于 0")
    if args.s3_count <= 0:
        parser.error("--s3-count 必须大于 0")

    weights = args.weights or ("sc" if args.layer == "one" else "sc_daily")
    analyzer = ShortcutGainAnalyzer(
        weights=weights,
        protect_native_charset=args.protect_native_charset,
        protect_native_min_score=args.protect_native_min_score,
        shortcut_candidate_min_score=args.shortcut_candidate_min_score,
        s2_count=args.s2_count,
        s3_count=args.s3_count,
    )
    result = analyzer.evaluate_assignment(code=args.code, text=args.char, layer=args.layer)
    replaced = result.replaced_text or "空位"
    print(f"权重模式: {weights}")
    print(f"{args.code}: {replaced} -> {args.char}")
    print(f"总净收益: {result.total_gain:+g}")
    print(f"直接收益: {result.direct_gain:+g}")
    print(f"S2/S3 联动: {result.indirect_gain:+g}")
    for change in result.changes[: args.top_changes]:
        print(f"  {change.text}: {change.before or '-'} -> {change.after or '-'}  {change.gain:+g}")


if __name__ == "__main__":
    main()
