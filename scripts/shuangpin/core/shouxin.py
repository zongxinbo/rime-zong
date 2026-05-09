from __future__ import annotations

from pathlib import Path

from .cangjie import load_aux_lists
from .paths import CHARS_SOURCE, PROTOTYPES_DIR


SHOUXIN_AUX_PATH = PROTOTYPES_DIR / "cangjie_aux.txt"


def load_source_chars(chars_path: Path = CHARS_SOURCE) -> set[str]:
    """读取单字原始字集，用来限制手心辅助码的导出范围。

    手心挂接文件不是 Rime 主码表，目标是给已有单字表补充辅助码，
    所以这里以 `scripts/shuangpin/prototypes/chars.txt` 为准，只导出
    原始单字表中已经出现的字符，避免把仓颉表里的部件、符号和扩展字
    一股脑塞进外部辅助码文件。
    """

    chars: set[str] = set()
    with chars_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if parts:
                chars.add(parts[0])
    return chars


def export_shouxin_aux(output_path: Path = SHOUXIN_AUX_PATH) -> int:
    """导出手心输入法可挂接的辅助码文件。

    手心输入法的外部辅助码通常只接受 GBK 字符，所以这里会先按
    `chars.txt` 限定字集，再过滤掉无法用 GBK 编码的扩展字。
    """

    source_chars = load_source_chars()
    aux_lists = load_aux_lists()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for text, auxes in aux_lists.items():
            if text not in source_chars:
                continue
            try:
                text.encode("gbk")
            except UnicodeEncodeError:
                continue
            for aux in auxes:
                f.write(f"{text}={aux}\n")
                count += 1
    return count
