from __future__ import annotations

from pathlib import Path

from .cangjie import build_prefixed_cangjie_entries
from .chars import build_char_entries, write_chars_prototype
from .converters import get_converter
from .models import CharEntry
from .paths import PROTOTYPES_DIR, SHUANGPIN_SCHEMAS_DIR
from .shouxin import SHOUXIN_AUX_PATH, export_shouxin_aux
from .words import build_word_entries, write_words_prototype
from .writer import (
    merge_entries,
    write_cangjie_prototype,
    write_dict,
    write_report,
    write_schema,
)


def schema_prototype_dir(schema: str) -> Path:
    return PROTOTYPES_DIR / schema


def schema_output_dir(schema: str) -> Path:
    """返回某个双拼方案在 Rime schemas 目录下的输出目录。"""

    return SHUANGPIN_SCHEMAS_DIR / schema


def build_chars_prototype(schema: str, simplified: bool = False) -> tuple[list[CharEntry], set[str], Path]:
    converter = get_converter(schema)
    entries, dropped = build_char_entries(converter, simplified=simplified)
    path = schema_prototype_dir(schema) / f"{schema}.chars.txt"
    write_chars_prototype(entries, path)
    aux_path = SHOUXIN_AUX_PATH
    aux_count = export_shouxin_aux(aux_path)
    print(f"已生成 {aux_path}（{aux_count} 行）")
    return entries, dropped, path


def build_scheme(
    schema: str,
    simplified: bool = False,
    min_word_weight: int = 5000,
    max_word_length: int = 4,
    emit_schema: bool = True,
) -> None:
    converter = get_converter(schema)
    proto_dir = schema_prototype_dir(schema)
    schema_dir = schema_output_dir(schema)

    char_entries, dropped_chars = build_char_entries(converter, simplified=simplified)
    write_chars_prototype(char_entries, proto_dir / f"{schema}.chars.txt")
    aux_path = SHOUXIN_AUX_PATH
    aux_count = export_shouxin_aux(aux_path)

    word_entries, dropped_words = build_word_entries(
        converter,
        min_weight=min_word_weight,
        max_length=max_word_length,
    )
    write_words_prototype(word_entries, proto_dir / f"{schema}.words.txt")

    cangjie_entries = build_prefixed_cangjie_entries()
    write_cangjie_prototype(cangjie_entries, proto_dir / f"{schema}.cangjie.txt")

    merged = merge_entries(char_entries, word_entries, cangjie_entries)
    write_dict(schema, merged, schema_dir / f"{schema}.dict.yaml")
    if emit_schema:
        write_schema(schema, schema_dir / f"{schema}.schema.yaml")

    write_report(
        proto_dir / f"{schema}.report.md",
        schema=schema,
        entries=merged,
        char_count=len(char_entries),
        word_count=len(word_entries),
        cangjie_count=len(cangjie_entries),
        dropped_chars=len(dropped_chars),
        dropped_words=dropped_words,
    )

    print(f"已生成 {proto_dir / f'{schema}.chars.txt'}")
    print(f"已生成 {aux_path}（{aux_count} 行）")
    print(f"已生成 {proto_dir / f'{schema}.words.txt'}")
    print(f"已生成 {proto_dir / f'{schema}.cangjie.txt'}")
    print(f"已生成 {schema_dir / f'{schema}.dict.yaml'}")
    if emit_schema:
        print(f"已生成 {schema_dir / f'{schema}.schema.yaml'}")
    print(f"已生成 {proto_dir / f'{schema}.report.md'}")
