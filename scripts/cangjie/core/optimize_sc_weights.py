#!/usr/bin/env python3
"""搜索适合现代简体日用场景的字频混合权重。

目标语料默认使用 Dialogue、Subtlex、Zhihu、BLCU。每个来源先独立归一化，
再最小化候选混合分布到各目标来源的平均 Jensen-Shannon 距离。这样可避免
大语料仅凭规模压过其他来源，同时让口语、字幕、网络文本和通用文本等权投票。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.frequency import parse_frequency_file
from core.paths import FREQ_PATHS, SC_FREQ_WEIGHTS


DEFAULT_SOURCES = ("Dialogue", "Subtlex", "Zhihu", "BLCU", "Essay")
DEFAULT_TARGETS = ("Dialogue", "Subtlex", "Zhihu", "BLCU")


def normalize_weights(weights: dict[str, float], sources: tuple[str, ...]) -> tuple[float, ...]:
    values = tuple(max(float(weights.get(source, 0.0)), 0.0) for source in sources)
    total = sum(values)
    if total <= 0:
        return tuple(1.0 / len(sources) for _ in sources)
    return tuple(value / total for value in values)


def load_distributions(sources: tuple[str, ...]) -> tuple[tuple[str, ...], dict[str, tuple[float, ...]]]:
    raw_distributions: dict[str, dict[str, float]] = {}
    chars: set[str] = set()
    for source in sources:
        path = FREQ_PATHS.get(source)
        if path is None or not path.is_file():
            raise ValueError(f"找不到字频来源 {source}: {path}")
        frequencies, _ = parse_frequency_file(path)
        total = sum(frequencies.values())
        if total <= 0:
            raise ValueError(f"字频来源为空: {source}: {path}")
        distribution = {char: value / total for char, value in frequencies.items()}
        raw_distributions[source] = distribution
        chars.update(distribution)

    ordered_chars = tuple(sorted(chars))
    return ordered_chars, {
        source: tuple(raw_distributions[source].get(char, 0.0) for char in ordered_chars)
        for source in sources
    }


def mix_distributions(
    weights: tuple[float, ...],
    sources: tuple[str, ...],
    distributions: dict[str, tuple[float, ...]],
) -> tuple[float, ...]:
    return tuple(
        sum(weight * distributions[source][index] for weight, source in zip(weights, sources))
        for index in range(len(next(iter(distributions.values()))))
    )


def jensen_shannon_divergence(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    divergence = 0.0
    for left_value, right_value in zip(left, right):
        middle = (left_value + right_value) / 2.0
        if left_value > 0:
            divergence += 0.5 * left_value * math.log(left_value / middle, 2)
        if right_value > 0:
            divergence += 0.5 * right_value * math.log(right_value / middle, 2)
    return divergence


def score_weights(
    weights: tuple[float, ...],
    sources: tuple[str, ...],
    targets: tuple[str, ...],
    distributions: dict[str, tuple[float, ...]],
) -> float:
    mixed = mix_distributions(weights, sources, distributions)
    return sum(
        jensen_shannon_divergence(mixed, distributions[target])
        for target in targets
    ) / len(targets)


def score_and_gradient(
    weights: tuple[float, ...],
    sources: tuple[str, ...],
    targets: tuple[str, ...],
    distributions: dict[str, tuple[float, ...]],
) -> tuple[float, tuple[float, ...]]:
    source_vectors = tuple(distributions[source] for source in sources)
    target_vectors = tuple(distributions[target] for target in targets)
    gradient = [0.0] * len(sources)
    score = 0.0
    target_count = len(targets)
    for index in range(len(source_vectors[0])):
        mixed = sum(weight * vector[index] for weight, vector in zip(weights, source_vectors))
        derivative = 0.0
        for target_vector in target_vectors:
            target = target_vector[index]
            middle = (mixed + target) / 2.0
            if mixed > 0:
                score += 0.5 * mixed * math.log(mixed / middle, 2)
                derivative += 0.5 * math.log(mixed / middle, 2)
            if target > 0:
                score += 0.5 * target * math.log(target / middle, 2)
        derivative /= target_count
        for source_index, vector in enumerate(source_vectors):
            gradient[source_index] += vector[index] * derivative
    return score / target_count, tuple(gradient)


def optimize_weights(
    sources: tuple[str, ...],
    targets: tuple[str, ...],
    distributions: dict[str, tuple[float, ...]],
    *,
    learning_rate: float,
    max_iterations: int,
    tolerance: float,
) -> tuple[tuple[float, ...], float]:
    weights = tuple(1.0 / len(sources) for _ in sources)
    score, gradient = score_and_gradient(weights, sources, targets, distributions)
    rate = learning_rate
    for _ in range(max_iterations):
        weighted_gradient = sum(weight * value for weight, value in zip(weights, gradient))
        centered = tuple(value - weighted_gradient for value in gradient)
        while True:
            moved = tuple(
                weight * math.exp(-rate * value)
                for weight, value in zip(weights, centered)
            )
            total = sum(moved)
            candidate = tuple(value / total for value in moved)
            candidate_score, candidate_gradient = score_and_gradient(
                candidate, sources, targets, distributions
            )
            if candidate_score <= score or rate <= 1e-9:
                break
            rate /= 2.0

        if score - candidate_score <= tolerance:
            return candidate, candidate_score
        weights = candidate
        score = candidate_score
        gradient = candidate_gradient
        rate = min(rate * 1.05, learning_rate)
    return weights, score


def optimize_and_prune_weights(
    sources: tuple[str, ...],
    targets: tuple[str, ...],
    distributions: dict[str, tuple[float, ...]],
    *,
    learning_rate: float,
    max_iterations: int,
    tolerance: float,
    prune_threshold: float,
) -> tuple[tuple[float, ...], float, tuple[str, ...]]:
    current = normalize_weights(SC_FREQ_WEIGHTS, sources)
    current_score = score_weights(current, sources, targets, distributions)
    optimized, optimized_score = optimize_weights(
        sources,
        targets,
        distributions,
        learning_rate=learning_rate,
        max_iterations=max_iterations,
        tolerance=tolerance,
    )
    if current_score < optimized_score:
        optimized, optimized_score = current, current_score
    pruned_sources = tuple(
        source
        for source, weight in zip(sources, optimized)
        if source not in targets and weight < prune_threshold
    )
    if not pruned_sources:
        return optimized, optimized_score, ()

    active_sources = tuple(source for source in sources if source not in pruned_sources)
    active_distributions = {source: distributions[source] for source in active_sources}
    current_active = normalize_weights(SC_FREQ_WEIGHTS, active_sources)
    current_active_score = score_weights(current_active, active_sources, targets, active_distributions)
    active_weights, active_score = optimize_weights(
        active_sources,
        targets,
        active_distributions,
        learning_rate=learning_rate,
        max_iterations=max_iterations,
        tolerance=tolerance,
    )
    if current_active_score < active_score:
        active_weights, active_score = current_active, current_active_score
    weights_by_source = dict(zip(active_sources, active_weights))
    return (
        tuple(weights_by_source.get(source, 0.0) for source in sources),
        active_score,
        pruned_sources,
    )


def weight_dict(sources: tuple[str, ...], weights: tuple[float, ...]) -> dict[str, float]:
    return {
        source: round(weight, 6)
        for source, weight in zip(sources, weights)
        if weight > 1e-12
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="搜索现代简体日用字频的最佳混合权重")
    parser.add_argument("--sources", nargs="+", default=DEFAULT_SOURCES,
                        help="允许参与混合的来源")
    parser.add_argument("--targets", nargs="+", default=DEFAULT_TARGETS,
                        help="用于定义日用共识的现代简体目标来源")
    parser.add_argument("--learning-rate", type=float, default=8.0, help="指数梯度下降初始学习率")
    parser.add_argument("--max-iterations", type=int, default=300, help="每轮最大优化次数")
    parser.add_argument("--tolerance", type=float, default=1e-12, help="目标值收敛阈值")
    parser.add_argument("--prune-threshold", type=float, default=0.002,
                        help="自动剔除低于该比例的非目标来源并在边界上复算")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = tuple(dict.fromkeys(args.sources))
    targets = tuple(dict.fromkeys(args.targets))
    if not sources or not targets:
        raise ValueError("--sources 和 --targets 不能为空")
    if any(target not in sources for target in targets):
        raise ValueError("--targets 必须包含在 --sources 中")
    if args.learning_rate <= 0 or args.max_iterations <= 0 or args.tolerance < 0 or args.prune_threshold < 0:
        raise ValueError("优化参数必须为正数，--tolerance 和 --prune-threshold 可为 0")

    _, distributions = load_distributions(sources)
    current = normalize_weights(SC_FREQ_WEIGHTS, sources)
    current_score = score_weights(current, sources, targets, distributions)
    optimized, optimized_score, pruned_sources = optimize_and_prune_weights(
        sources,
        targets,
        distributions,
        learning_rate=args.learning_rate,
        max_iterations=args.max_iterations,
        tolerance=args.tolerance,
        prune_threshold=args.prune_threshold,
    )
    result = {
        "objective": "mean Jensen-Shannon divergence to equal-vote modern SC targets",
        "sources": sources,
        "targets": targets,
        "learning_rate": args.learning_rate,
        "max_iterations": args.max_iterations,
        "tolerance": args.tolerance,
        "prune_threshold": args.prune_threshold,
        "pruned_sources": pruned_sources,
        "current_weights": weight_dict(sources, current),
        "current_score": current_score,
        "optimized_weights": weight_dict(sources, optimized),
        "optimized_score": optimized_score,
        "improvement_percent": (current_score - optimized_score) / current_score * 100,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"目标来源: {', '.join(targets)}")
        print(f"候选来源: {', '.join(sources)}")
        print(f"当前比例: {result['current_weights']}")
        print(f"当前目标值: {current_score:.12f}")
        if pruned_sources:
            print(f"边界剔除: {', '.join(pruned_sources)}")
        print(f"最优比例: {result['optimized_weights']}")
        print(f"最优目标值: {optimized_score:.12f}")
        print(f"目标值改善: {result['improvement_percent']:.4f}%")
        print(f"SC_FREQ_WEIGHTS = {result['optimized_weights']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
