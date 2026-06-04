from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.charset import is_gbk, is_han_char
from core.io import parse_cangjie_dict
from core.paths import CANGJIE5_DICT_PATH, REPO_ROOT


DEFAULT_OUTPUT_PATH = REPO_ROOT / "scripts" / "cangjie" / "data" / "sc_glyph_preferred_code.txt"
DEFAULT_UNRESOLVED_PATH = REPO_ROOT / "scripts" / "cangjie" / "data" / "sc_glyph_unresolved_code.txt"
DEFAULT_CACHE_PATH = REPO_ROOT / "scripts" / "cangjie" / "data" / "chidic_glyph_cache.json"
DEFAULT_MANUAL_PREFERRED_PATH = REPO_ROOT / "scripts" / "cangjie" / "data" / "sc_glyph_manual_preferred_code.txt"
CHIDIC_URL = "https://chidic.eduhk.hk/v.php?dicword={text}"
FIELD_PATTERN = re.compile(r"鍵盤字母：</font>([A-Z]+)")


def load_ambiguous_codes() -> dict[str, set[str]]:
    codes_by_text: dict[str, set[str]] = defaultdict(set)
    for entry in parse_cangjie_dict(CANGJIE5_DICT_PATH):
        if is_han_char(entry.text) and not entry.code.startswith(("x", "z")):
            codes_by_text[entry.text].add(entry.code)
    return {
        text: codes
        for text, codes in codes_by_text.items()
        if len(codes) > 1 and is_gbk(text)
    }


def extract_field(block: str, label: str) -> str:
    match = re.search(rf"{label}：</font>(.*?)</td>", block, flags=re.S)
    if match is None:
        return ""
    value = re.sub(r"<[^>]+>", "", match.group(1))
    return html.unescape(value).strip()


def extract_code_field(block: str, label: str) -> str:
    value = extract_field(block, label).upper()
    match = re.search(r"[A-Z]+", value)
    return match.group(0).lower() if match else ""


def parse_chidic_page(page: str) -> list[dict[str, str]]:
    matches = list(FIELD_PATTERN.finditer(page))
    entries: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
        block = page[match.start():end]
        entries.append({
            "code": match.group(1).lower(),
            "wucang_dup_code": extract_code_field(block, "五倉重碼"),
            "gbk": extract_field(block, "GBK"),
            "hkscs": extract_field(block, "HKSCS"),
            "big5": extract_field(block, "BIG5"),
        })
    return entries


def fetch_page(text: str, *, timeout: float, retries: int) -> str:
    url = CHIDIC_URL.format(text=urllib.parse.quote(text))
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl is None:
        raise RuntimeError("找不到 curl；请安装 curl 或使用 Windows 自带 curl.exe")
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                [
                    curl,
                    "--silent",
                    "--show-error",
                    "--location",
                    "--max-time",
                    str(timeout),
                    url,
                ],
                check=True,
                capture_output=True,
            )
            return result.stdout.decode("utf-8")
        except Exception:
            if attempt >= retries:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def fetch_entries(text: str, *, timeout: float, retries: int, delay: float) -> list[dict[str, str]]:
    try:
        for attempt in range(retries + 1):
            try:
                entries = parse_chidic_page(fetch_page(text, timeout=timeout, retries=0))
                if not entries:
                    raise ValueError("页面未解析出任何仓颉字形块")
                return entries
            except Exception:
                if attempt >= retries:
                    raise
                time.sleep(2 ** attempt)
        raise AssertionError("unreachable")
    finally:
        time.sleep(delay)


def load_cache(path: Path, allowed_texts: set[str]) -> dict[str, list[dict[str, str]]]:
    if not path.exists():
        return {}
    cache = json.loads(path.read_text(encoding="utf-8"))
    return {
        text: entries
        for text, entries in cache.items()
        if text in allowed_texts
    }


def write_cache(path: Path, cache: dict[str, list[dict[str, str]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sort_tsv_file_by_code(path: Path) -> None:
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    comments = [line for line in lines if not line or line.startswith("#")]
    rows = [line for line in lines if line and not line.startswith("#")]
    rows.sort(key=lambda line: (line.split("\t", maxsplit=2)[1], line.split("\t", maxsplit=1)[0]))
    path.write_text("\n".join(comments + rows) + "\n", encoding="utf-8", newline="\n")


def write_preferred_codes(path: Path, preferred_codes: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# encoding: utf-8",
        "# Mainland glyph preferred Cangjie5 codes.",
        "# Resolved from chidic.eduhk.hk GBK entries.",
        "# A unique non-x/z GBK code wins; otherwise normalize a unique x-prefixed GBK code when its",
        "# stripped code exists in the source table.",
    ]
    items = sorted(preferred_codes.items(), key=lambda item: (item[1], item[0]))
    lines.extend(f"{text}\t{code}" for text, code in items)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def load_preferred_codes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    preferred: dict[str, str] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2 or len(parts[0]) != 1 or not parts[1]:
            raise ValueError(f"{path}:{lineno}: 首选码格式应为 字<TAB>编码")
        preferred[parts[0]] = parts[1]
    return preferred


def resolve_x_prefixed_gbk_code(source_codes: set[str], entries: list[dict[str, str]]) -> str | None:
    exact_codes: set[str] = set()
    prefix_expanded_codes: set[str] = set()
    for entry in entries:
        code = entry["code"]
        if not entry["gbk"] or not code.startswith("x"):
            continue
        normalized = code.lstrip("x")
        if normalized in source_codes:
            exact_codes.add(normalized)
            continue
        matching_codes = {
            source_code
            for source_code in source_codes
            if source_code.startswith(normalized)
        }
        if len(matching_codes) == 1:
            prefix_expanded_codes.update(matching_codes)
    if len(exact_codes) == 1:
        return next(iter(exact_codes))
    if not exact_codes and len(prefix_expanded_codes) == 1:
        return next(iter(prefix_expanded_codes))
    return None


def write_unresolved_codes(
    path: Path,
    ambiguous_codes: dict[str, set[str]],
    cache: dict[str, list[dict[str, str]]],
    unresolved: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str, str, str]] = []
    for text in unresolved:
        entries = cache[text]
        source_codes = ",".join(sorted(ambiguous_codes[text]))
        gbk_codes = ",".join(sorted({
            effective_gbk_code(entry, ambiguous_codes[text]) or entry["code"]
            for entry in entries
            if entry["gbk"]
        }))
        normal_gbk_codes = ",".join(sorted({
            effective_gbk_code(entry, ambiguous_codes[text]) or entry["code"]
            for entry in entries
            if entry["gbk"] and not (effective_gbk_code(entry, ambiguous_codes[text]) or entry["code"]).startswith(("x", "z"))
        }))
        rows.append((text, source_codes, gbk_codes, normal_gbk_codes))
    rows.sort(key=lambda row: row[0])
    lines = [
        "# encoding: utf-8",
        "# text<TAB>source_codes<TAB>chidic_gbk_codes<TAB>chidic_normal_gbk_codes",
    ]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def resolve_preferred_codes(
    ambiguous_codes: dict[str, set[str]],
    cache: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, str], list[str]]:
    preferred_codes: dict[str, str] = {}
    unresolved: list[str] = []
    for text, source_codes in ambiguous_codes.items():
        entries = cache.get(text)
        if entries is None:
            continue
        gbk_codes = {
            code
            for entry in entries
            for code in [effective_gbk_code(entry, source_codes)]
            if (
                code is not None
                and entry["gbk"]
                and not code.startswith(("x", "z"))
                and code in source_codes
            )
        }
        if len(gbk_codes) == 1:
            preferred_codes[text] = next(iter(gbk_codes))
            continue
        normalized_x_code = resolve_x_prefixed_gbk_code(source_codes, entries)
        if normalized_x_code is not None:
            preferred_codes[text] = normalized_x_code
            continue
        unresolved.append(text)
    return preferred_codes, unresolved


def parse_chars(raw_chars: str) -> list[str]:
    return list(dict.fromkeys(char for char in raw_chars if char not in {",", " ", "\t", "\r", "\n"}))


def effective_gbk_code(entry: dict[str, str], source_codes: set[str]) -> str | None:
    code = entry["code"]
    if entry.get("gbk") and code in source_codes:
        return code
    dup_code = entry.get("wucang_dup_code", "")
    if entry.get("gbk") and code.startswith("x") and dup_code in source_codes:
        return dup_code
    return None


def load_unresolved_texts(path: Path) -> list[str]:
    if not path.exists():
        return []
    texts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        texts.append(line.split("\t", maxsplit=1)[0])
    return texts


def backfill_cache_from_preferred(
    *,
    cache_path: Path,
    manual_preferred_path: Path,
    preferred_path: Path,
    unresolved_path: Path,
    ambiguous_codes: dict[str, set[str]],
) -> tuple[int, int, int, int]:
    """把人工确认表反填进 cache，并刷新 preferred/unresolved。"""
    preferred = load_preferred_codes(manual_preferred_path)
    cache = load_cache(cache_path, set(ambiguous_codes))
    added = 0
    replaced = 0
    skipped = 0
    for text, code in preferred.items():
        source_codes = ambiguous_codes.get(text)
        if source_codes is None or code not in source_codes:
            skipped += 1
            continue
        entry = {"code": code, "gbk": "MANUAL", "hkscs": "", "big5": ""}
        old = cache.get(text)
        if old == [entry]:
            continue
        if old:
            replaced += 1
        else:
            added += 1
        cache[text] = [entry]
    write_cache(cache_path, cache)
    resolved, unresolved = resolve_preferred_codes(ambiguous_codes, cache)
    write_preferred_codes(preferred_path, resolved)
    write_unresolved_codes(unresolved_path, ambiguous_codes, cache, unresolved)
    return added, replaced, skipped, len(unresolved)


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(description="抓取大陆字形首选仓颉五码")
    parser.add_argument("--chars", default="", help="仅抓取指定汉字，例如 着,的,真；默认扫描全部多码字")
    parser.add_argument("--delay", type=float, default=1.0, help="每次网络请求后的等待秒数；默认 1.0")
    parser.add_argument("--workers", type=int, default=5, help="并发请求线程数；默认 5")
    parser.add_argument("--timeout", type=float, default=30.0, help="单次请求超时秒数；默认 30")
    parser.add_argument("--retries", type=int, default=0, help="单字失败重试次数；默认 0，限流后建议换 IP 再续跑")
    parser.add_argument("--failure-rounds", type=int, default=0, help="完成扫描后再次补抓失败字的轮数；默认 0")
    parser.add_argument("--checkpoint-every", type=int, default=20, help="每新增抓取多少字刷新一次首选码表；默认 20")
    parser.add_argument("--batch-size", type=int, default=150, help="每批最多查询数量；默认 150")
    parser.add_argument("--batch-pause", type=float, default=0.0, help="批次之间暂停秒数；默认 0")
    parser.add_argument("--limit", type=int, default=150, help="本次最多领取多少个未决字；默认 150，0 表示不限制")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="首选码输出文件")
    parser.add_argument("--unresolved-output", type=Path, default=DEFAULT_UNRESOLVED_PATH, help="仍需人工确认的歧义码输出文件")
    parser.add_argument("--sort-by-code", action="store_true", help="只将现有输出文件按仓颉编码排序，然后立即退出")
    parser.add_argument("--backfill-from-preferred", action="store_true",
                        help="从人工确认首选码文件反填 cache，并刷新首选码和未决文件；不访问网络")
    parser.add_argument("--manual-preferred", type=Path, default=DEFAULT_MANUAL_PREFERRED_PATH,
                        help="人工确认首选码文件，供 --backfill-from-preferred 使用")
    parser.add_argument("--refetch-unresolved", action="store_true",
                        help="只重查当前未决文件中的汉字，并先删除这些字的旧 cache")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH, help="断点缓存 JSON")
    args = parser.parse_args()
    if args.sort_by_code:
        sort_tsv_file_by_code(args.output)
        sort_tsv_file_by_code(args.unresolved_output)
        print(f"已按仓颉编码排序: {args.output}")
        print(f"已按仓颉编码排序: {args.unresolved_output}")
        return
    ambiguous_codes = load_ambiguous_codes()
    if args.backfill_from_preferred:
        added, replaced, skipped, unresolved_count = backfill_cache_from_preferred(
            cache_path=args.cache,
            manual_preferred_path=args.manual_preferred,
            preferred_path=args.output,
            unresolved_path=args.unresolved_output,
            ambiguous_codes=ambiguous_codes,
        )
        print(
            f"已从人工首选码反填 cache: 新增={added} 覆盖={replaced} "
            f"跳过={skipped} 剩余未决={unresolved_count}"
        )
        print(f"cache: {args.cache}")
        print(f"人工首选码: {args.manual_preferred}")
        print(f"首选码: {args.output}")
        print(f"未决码: {args.unresolved_output}")
        return
    if (
        args.delay < 0
        or args.workers <= 0
        or args.timeout <= 0
        or args.retries < 0
        or args.failure_rounds < 0
        or args.checkpoint_every <= 0
        or args.batch_size <= 0
        or args.batch_pause < 0
        or args.limit < 0
    ):
        parser.error("delay、retries、failure-rounds、batch-pause、limit 不能为负数，workers、timeout、checkpoint-every 和 batch-size 必须大于 0")

    online_ambiguous = ambiguous_codes
    if args.refetch_unresolved:
        texts = load_unresolved_texts(args.unresolved_output)
    else:
        texts = parse_chars(args.chars) if args.chars else sorted(online_ambiguous)
    texts = [text for text in texts if text in online_ambiguous]
    cache = load_cache(args.cache, set(online_ambiguous))
    if args.refetch_unresolved:
        for text in texts:
            cache.pop(text, None)
        write_cache(args.cache, cache)

    fetched = 0
    failures: list[tuple[str, str]] = []
    pending = [text for text in texts if not cache.get(text)]
    if args.limit:
        pending = pending[:args.limit]
    for round_index in range(args.failure_rounds + 1):
        if not pending:
            break
        if round_index:
            print(f"开始补抓失败字：第 {round_index}/{args.failure_rounds} 轮，共 {len(pending)} 字")
        round_pending = pending
        pending = []
        while round_pending:
            batch_limit = min(len(round_pending), args.batch_size)
            batch = round_pending[:batch_limit]
            round_pending = round_pending[batch_limit:]
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                future_texts = {
                    executor.submit(
                        fetch_entries,
                        text,
                        timeout=args.timeout,
                        retries=args.retries,
                        delay=args.delay,
                    ): text
                    for text in batch
                }
                for future in as_completed(future_texts):
                    text = future_texts[future]
                    try:
                        cache[text] = future.result()
                        fetched += 1
                        write_cache(args.cache, cache)
                        if fetched % args.checkpoint_every == 0:
                            online_preferred, _ = resolve_preferred_codes(online_ambiguous, cache)
                            write_preferred_codes(args.output, online_preferred)
                        print(f"[{fetched}] {text}: {cache[text]}")
                    except Exception as exc:
                        pending.append(text)
                        failures.append((text, str(exc)))
                        print(f"[ERROR] {text}: {exc}")
            if round_pending:
                print(f"批次完成，暂停 {args.batch_pause:g} 秒；本轮剩余 {len(round_pending)} 字")
                time.sleep(args.batch_pause)
        if pending and round_index < args.failure_rounds:
            print(f"本轮失败 {len(pending)} 字，暂停 {args.batch_pause:g} 秒后补抓")
            time.sleep(args.batch_pause)

    online_preferred, unresolved = resolve_preferred_codes(online_ambiguous, cache)
    online_remaining = sum(not cache.get(text) for text in online_ambiguous)

    write_preferred_codes(args.output, online_preferred)
    write_unresolved_codes(
        args.unresolved_output,
        online_ambiguous,
        cache,
        unresolved,
    )
    print(f"首选码已保存: {args.output}")
    print(f"未决码已保存: {args.unresolved_output}")
    print(
        f"GBK 多码字: {len(ambiguous_codes)}；在线缓存: {len(cache)}；在线补齐: {len(online_preferred)}；"
        f"在线剩余待处理: {online_remaining}；缓存内仍未决: {len(unresolved)}；"
        f"本批待补抓: {len(pending)}；失败记录: {len(failures)}"
    )


if __name__ == "__main__":
    main()
