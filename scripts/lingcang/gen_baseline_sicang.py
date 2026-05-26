#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.cangjie.core.cangjie_builder import is_han_char, parse_cangjie_dict, project_code
from scripts.lingcang.core.paths import REPO_ROOT, SOURCE_DICT

OUTPUT = REPO_ROOT / "_tmp/assess/sicang5_raw_cangjie5.dict.yaml"


def main() -> int:
    entries = parse_cangjie_dict(SOURCE_DICT)
    emitted: set[tuple[str, str]] = set()
    rows: list[tuple[str, str]] = []
    skipped_prefix = 0
    for entry in entries:
        if not is_han_char(entry.text):
            continue
        if entry.code.startswith(("x", "z")):
            skipped_prefix += 1
            continue
        code = project_code(entry.code, 4)
        item = (entry.text, code)
        if item in emitted:
            continue
        emitted.add(item)
        rows.append(item)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# encoding: utf-8",
        "# raw four-code projection from cangjie5.dict.yaml; no shortcuts, no suffix-z",
        "---",
        "name: sicang5_raw_cangjie5",
        f"version: '{dt.date.today().isoformat()}'",
        "sort: original",
        "...",
        "",
    ]
    OUTPUT.write_text("\n".join(header + [f"{char}\t{code}" for char, code in rows]) + "\n", encoding="utf-8", newline="\n")
    print(f"完成：entries={len(rows)} skipped_prefix={skipped_prefix} output={OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
