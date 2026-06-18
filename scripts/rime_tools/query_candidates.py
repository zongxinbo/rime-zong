#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import os
from ctypes import (
    POINTER,
    Structure,
    byref,
    c_bool,
    c_char_p,
    c_int,
    c_size_t,
    c_void_p,
)
from pathlib import Path


DEFAULT_RIME_DIR = Path(r"C:\Program Files\Rime\weasel-0.17.4")
DEFAULT_USER_DIR = Path(os.environ.get("APPDATA", "")) / "Rime"


class RimeTraits(Structure):
    _fields_ = [
        ("data_size", c_int),
        ("shared_data_dir", c_char_p),
        ("user_data_dir", c_char_p),
        ("distribution_name", c_char_p),
        ("distribution_code_name", c_char_p),
        ("distribution_version", c_char_p),
        ("app_name", c_char_p),
        ("modules", c_void_p),
        ("min_log_level", c_char_p),
        ("log_dir", c_char_p),
        ("prebuilt_data_dir", c_char_p),
        ("staging_dir", c_char_p),
    ]


class RimeComposition(Structure):
    _fields_ = [
        ("length", c_int),
        ("cursor_pos", c_int),
        ("sel_start", c_int),
        ("sel_end", c_int),
        ("preedit", c_char_p),
    ]


class RimeCandidate(Structure):
    _fields_ = [
        ("text", c_char_p),
        ("comment", c_char_p),
        ("reserved", c_void_p),
    ]


class RimeMenu(Structure):
    _fields_ = [
        ("page_size", c_int),
        ("page_no", c_int),
        ("is_last_page", c_bool),
        ("highlighted_candidate_index", c_int),
        ("num_candidates", c_int),
        ("candidates", POINTER(RimeCandidate)),
        ("select_keys", c_char_p),
    ]


class RimeContext(Structure):
    _fields_ = [
        ("data_size", c_int),
        ("composition", RimeComposition),
        ("menu", RimeMenu),
        ("commit_text_preview", c_char_p),
        ("select_labels", c_char_p),
    ]


def utf8(text: str | Path) -> bytes:
    return str(text).encode("utf-8")


def decode(value: bytes | None) -> str:
    return value.decode("utf-8") if value else ""


def load_rime(rime_dir: Path):
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(rime_dir))
    dll_path = rime_dir / "rime.dll"
    if not dll_path.is_file():
        raise FileNotFoundError(f"找不到 rime.dll: {dll_path}")
    rime = ctypes.CDLL(str(dll_path))

    session_id = c_size_t
    rime.RimeSetup.argtypes = [POINTER(RimeTraits)]
    rime.RimeInitialize.argtypes = [POINTER(RimeTraits)]
    rime.RimeFinalize.argtypes = []
    rime.RimeCreateSession.argtypes = []
    rime.RimeCreateSession.restype = session_id
    rime.RimeDestroySession.argtypes = [session_id]
    rime.RimeDestroySession.restype = c_int
    rime.RimeSelectSchema.argtypes = [session_id, c_char_p]
    rime.RimeSelectSchema.restype = c_int
    rime.RimeSetOption.argtypes = [session_id, c_char_p, c_int]
    rime.RimeProcessKey.argtypes = [session_id, c_int, c_int]
    rime.RimeProcessKey.restype = c_int
    rime.RimeGetContext.argtypes = [session_id, POINTER(RimeContext)]
    rime.RimeGetContext.restype = c_int
    rime.RimeFreeContext.argtypes = [POINTER(RimeContext)]
    return rime


def initialize(rime, *, rime_dir: Path, user_dir: Path) -> RimeTraits:
    log_dir = Path(os.environ.get("TEMP", str(user_dir))) / "rime.query"
    log_dir.mkdir(parents=True, exist_ok=True)
    traits = RimeTraits()
    traits.data_size = ctypes.sizeof(RimeTraits)
    traits.shared_data_dir = utf8(rime_dir / "data")
    traits.user_data_dir = utf8(user_dir)
    traits.distribution_name = b"Weasel"
    traits.distribution_code_name = b"Weasel"
    traits.distribution_version = b"0.17.4"
    traits.app_name = b"rime_query_candidates"
    traits.modules = None
    traits.min_log_level = b"INFO"
    traits.log_dir = utf8(log_dir)
    traits.prebuilt_data_dir = None
    traits.staging_dir = None
    rime.RimeSetup(byref(traits))
    rime.RimeInitialize(byref(traits))
    return traits


def query_candidates(
    *,
    rime_dir: Path,
    user_dir: Path,
    schema: str,
    code: str,
    limit: int,
    extended_charset: bool,
) -> list[tuple[str, str]]:
    rime = load_rime(rime_dir)
    initialize(rime, rime_dir=rime_dir, user_dir=user_dir)
    session = rime.RimeCreateSession()
    if not session:
        raise RuntimeError("创建 Rime session 失败")
    try:
        if not rime.RimeSelectSchema(session, utf8(schema)):
            raise RuntimeError(f"切换 schema 失败: {schema}")
        rime.RimeSetOption(session, b"extended_charset", int(extended_charset))
        for char in code.encode("ascii"):
            if not rime.RimeProcessKey(session, char, 0):
                raise RuntimeError(f"输入按键失败: {chr(char)}")

        context = RimeContext()
        context.data_size = ctypes.sizeof(RimeContext)
        if not rime.RimeGetContext(session, byref(context)):
            raise RuntimeError("读取 Rime context 失败")
        try:
            results: list[tuple[str, str]] = []
            count = min(context.menu.num_candidates, limit)
            for index in range(count):
                candidate = context.menu.candidates[index]
                results.append((decode(candidate.text), decode(candidate.comment)))
            return results
        finally:
            rime.RimeFreeContext(byref(context))
    finally:
        rime.RimeDestroySession(session)
        rime.RimeFinalize()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用本机 librime 查询指定方案的候选顺序")
    parser.add_argument("code", help="要查询的编码，例如 oihg")
    parser.add_argument("--schema", default="sicang5_words", help="方案 ID")
    parser.add_argument("--limit", type=int, default=20, help="输出候选数量")
    parser.add_argument("--rime-dir", type=Path, default=DEFAULT_RIME_DIR, help="小狼毫安装目录")
    parser.add_argument("--user-dir", type=Path, default=DEFAULT_USER_DIR, help="Rime 用户目录")
    parser.add_argument("--extended-charset", action="store_true", help="打开 extended_charset")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates = query_candidates(
        rime_dir=args.rime_dir,
        user_dir=args.user_dir,
        schema=args.schema,
        code=args.code,
        limit=args.limit,
        extended_charset=args.extended_charset,
    )
    for index, (text, comment) in enumerate(candidates, start=1):
        if comment:
            print(f"{index}\t{text}\t{comment}")
        else:
            print(f"{index}\t{text}")


if __name__ == "__main__":
    main()
