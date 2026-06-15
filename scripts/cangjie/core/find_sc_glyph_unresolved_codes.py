from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.glyph_codes import load_glyph_preferred_codes
from core.paths import DATA_DIR, IDS_PATH, SC_GLYPH_PREFERRED_CODE_PATH


DEFAULT_OUTPUT_PATH = DATA_DIR / "sc_glyph_unresolved_code.txt"


def load_ids_containing_component(path: Path, component: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=2)
        if len(parts) < 3:
            continue
        _codepoint, text, ids = parts
        if len(text) != 1:
            raise ValueError(f"{path}:{lineno}: IDS 字段应为单字")
        if component in ids:
            rows[text] = ids
    return rows


def review_note(
    text: str,
    code: str,
    ids: str,
    *,
    component: str,
    self_code: str | None,
    left_prefix: str | None,
) -> str:
    if text == component:
        if self_code is None:
            return f"{component}本字，待人工复核"
        return (
            f"{component}本字应复核为 {self_code}"
            if code != self_code
            else f"{component}本字已为 {self_code}"
        )
    if ids.startswith(f"⿰{component}") or ids.startswith(f"⿲{component}"):
        if left_prefix is None:
            return f"{component}作左部首，待人工复核"
        return (
            f"{component}作左部首，通常应以 {left_prefix} 开头"
            if not code.startswith(left_prefix)
            else f"{component}作左部首，已以 {left_prefix} 开头"
        )
    return f"含{component}，待人工复核"


def needs_review(
    text: str,
    code: str,
    ids: str,
    *,
    component: str,
    self_code: str | None,
    left_prefix: str | None,
) -> bool:
    if text == component and self_code is not None:
        return code != self_code
    if (
        left_prefix is not None
        and (ids.startswith(f"⿰{component}") or ids.startswith(f"⿲{component}"))
    ):
        return not code.startswith(left_prefix)
    return True


def build_review_rows(
    preferred_codes: dict[str, str],
    component_ids: dict[str, str],
    *,
    component: str,
    self_code: str | None,
    left_prefix: str | None,
) -> list[tuple[str, str, str, str]]:
    rows = [
        (
            text,
            code,
            component_ids[text],
            review_note(
                text,
                code,
                component_ids[text],
                component=component,
                self_code=self_code,
                left_prefix=left_prefix,
            ),
        )
        for text, code in preferred_codes.items()
        if text in component_ids
        and needs_review(
            text,
            code,
            component_ids[text],
            component=component,
            self_code=self_code,
            left_prefix=left_prefix,
        )
    ]
    return sorted(rows, key=lambda row: (row[1], row[0]))


def write_review(path: Path, rows: list[tuple[str, str, str, str]], *, component: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# encoding: utf-8",
        f"# Mainland glyph preferred Cangjie5 codes whose IDS contains {component}; manually review these entries.",
        "# text<TAB>current_code<TAB>ids<TAB>review_note",
    ]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="把 sc_glyph_preferred_code.txt 中 IDS 含指定部件的字写入 unresolved，供人工复核大陆字形编码。"
    )
    parser.add_argument("component", help="要在 IDS 中查找的部件，例如：片")
    parser.add_argument("--ids", type=Path, default=IDS_PATH)
    parser.add_argument("--preferred", type=Path, default=SC_GLYPH_PREFERRED_CODE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--self-code", help="部件本字预期编码，例如片为 llmn")
    parser.add_argument("--left-prefix", help="部件作左部首时的预期编码前缀，例如片为 ln")
    args = parser.parse_args()

    preferred_codes = load_glyph_preferred_codes(args.preferred)
    component_ids = load_ids_containing_component(args.ids, args.component)
    rows = build_review_rows(
        preferred_codes,
        component_ids,
        component=args.component,
        self_code=args.self_code,
        left_prefix=args.left_prefix,
    )
    write_review(args.output, rows, component=args.component)
    print(f"写出 {len(rows)} 条：{args.output}")


if __name__ == "__main__":
    main()
