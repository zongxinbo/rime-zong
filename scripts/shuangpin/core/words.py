from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from .cangjie import load_aux_map
from .io import iter_rime_dict_rows, parse_int
from .models import WordEntry
from .paths import (
    CANGJIE5_DICT,
    CHARS_SOURCE,
    ESSAY_ZH_HANS,
    PINYIN_ICE_BASE_DICT,
)


Converter = Callable[[str], str]


@dataclass(frozen=True)
class WordSourceRow:
    """词源中的一条候选词。

    `pinyin` 只在词源本身是 Rime 词典时才可能有值。默认的 essay 词频表没有
    读音列，所以后续会用词级读音表和单字读音表补齐。
    """

    text: str
    weight: int
    pinyin: str | None = None


@dataclass(frozen=True)
class WordPinyinInfo:
    """pinyin_ice 中的词级读音和权重。

    这里的读音用于处理“白术 bai zhu”这类异读词；权重只在 pinyin_ice 作为补充词源时使用，
    不再反向抬高 essay 主词源中的低频条目，避免“我们将”这类语流片段回流。
    """

    pinyin: str
    weight: int


# 主词源使用 essay-zh-hans，它本来就是面向输入法的词频表，频率口径比通用分词词频更贴近打字。
# 阈值故意压得比较低：二字词保留日常短词，三字词略收紧以过滤语流片段，四字词保留常见成语和固定搭配。
DEFAULT_MIN_WEIGHT_BY_LENGTH = {
    2: 50,
    3: 100,
    4: 50,
}

# “入库”和“给短码”分开控制。主词源条目只按 essay 频率判断短码资格；
# 低频词可以用全双拼码输入，但不抢单字和高频词的短码空间。
# essay 频率尺度比 pinyin_ice 小很多，阈值按 essay 的分布重定：
# 二字词适度放宽，让“好了”“走了”这类日用短词进入逐字首码层；
# 三字词和四字词继续收紧，避免“我们将”“是中国”这类语流片段干扰单字三码。
ESSAY_SHORT_CODE_MIN_WEIGHT_BY_LENGTH = {
    2: 12_000,
    3: 8_000,
    4: 3_000,
}

# pinyin_ice 只额外补 essay 缺失的超高频二字词。它的主要价值仍是词级读音，
# 补词只解决 essay 偶尔漏掉的日用口语短词，避免把 pinyin_ice 的普通二字长尾全部带回来。
PINYIN_ICE_EXTRA_TWO_CHAR_MIN_WEIGHT = 500_000


def is_han_char(ch: str) -> bool:
    """判断字符是否属于常见汉字或 CJK 扩展汉字范围。"""

    codepoint = ord(ch)
    return (
        0x3400 <= codepoint <= 0x9FFF
        or 0x20000 <= codepoint <= 0x323AF
        or 0x2F800 <= codepoint <= 0x2FA1F
    )


def is_han_word(text: str) -> bool:
    """只收二字及以上的纯汉字词，过滤标点、数字、拉丁字母和混排条目。"""

    return len(text) >= 2 and all(is_han_char(ch) for ch in text)


def iter_word_source_rows(path: Path) -> Iterator[WordSourceRow]:
    """读取词源，兼容 Rime 词典和“词 频率”两列词频表。

    当前默认词源是 `essay-zh-hans.txt`，它负责提供“哪些词值得收”和对应输入法频率；
    如果以后临时传入 Rime 词典，本函数也会保留其中的词级拼音，方便做对比实验。
    """

    if not path.exists():
        return

    text = path.read_text(encoding="utf-8-sig")
    if "..." in text:
        for parts in iter_rime_dict_rows(path):
            if len(parts) < 2:
                continue
            weight = parse_int(parts[2], 0) if len(parts) >= 3 else 0
            yield WordSourceRow(text=parts[0], pinyin=parts[1], weight=weight)
        return

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            weight = int(float(parts[1]))
        except ValueError:
            continue
        yield WordSourceRow(text=parts[0], weight=weight)


def load_word_pinyin_map(path: Path) -> dict[str, WordPinyinInfo]:
    """从 pinyin_ice.base 读取词级拼音和输入法权重。

    词级读音能解决“白术 bai zhu”“单于 chan yu”这类单字读音表无法可靠消歧的问题。
    词级权重只用于判断 pinyin_ice 自己是否足够高频、值得作为缺词补入；同一个词如果有多行，取权重最高的一行。
    """

    best: dict[str, WordPinyinInfo] = {}
    if not path.exists():
        return {}

    for parts in iter_rime_dict_rows(path):
        if len(parts) < 2:
            continue
        text, pinyin = parts[0], parts[1]
        if not is_han_word(text):
            continue
        weight = parse_int(parts[2], 0) if len(parts) >= 3 else 0
        old = best.get(text)
        if old is None or weight > old.weight:
            best[text] = WordPinyinInfo(pinyin=pinyin, weight=weight)

    return best


def iter_pinyin_ice_extra_rows(
    word_pinyin_map: dict[str, WordPinyinInfo],
    excluded_texts: set[str],
) -> Iterator[WordSourceRow]:
    """从 pinyin_ice 额外补高频二字词。

    这一步只处理 essay 主词源没有收录的二字词。已经在 essay 中的词保持 essay 频率，
    不用 pinyin_ice 权重提权；三字和四字完全交给 essay 控制，避免旧词库里的语流片段回流。
    """

    for text, info in sorted(word_pinyin_map.items(), key=lambda item: (-item[1].weight, item[0])):
        if (
            text not in excluded_texts
            and len(text) == 2
            and is_han_word(text)
            and info.weight >= PINYIN_ICE_EXTRA_TWO_CHAR_MIN_WEIGHT
        ):
            yield WordSourceRow(text=text, weight=info.weight, pinyin=info.pinyin)


def load_char_pinyin_map(path: Path = CHARS_SOURCE) -> dict[str, list[str]]:
    """读取单字读音表，作为词级拼音缺失时的兜底。

    `chars.txt` 是单字表，不知道词语中的异读；因此这里只在一个字没有多读音歧义时使用。
    多音字如果缺少词级读音，宁可丢弃该词，也不自动猜错读音。
    """

    weighted: dict[str, list[tuple[int, str]]] = {}
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            char, pinyin = parts[0], parts[1]
            if len(char) != 1 or not pinyin:
                continue
            weight = parse_int(parts[-1], 0)
            weighted.setdefault(char, []).append((weight, pinyin))

    result: dict[str, list[str]] = {}
    for char, values in weighted.items():
        seen: set[str] = set()
        pinyins: list[str] = []
        for _, pinyin in sorted(values, key=lambda item: (-item[0], item[1])):
            if pinyin in seen:
                continue
            seen.add(pinyin)
            pinyins.append(pinyin)
        result[char] = pinyins
    return result


def infer_word_pinyin(
    row: WordSourceRow,
    word_pinyin_map: dict[str, WordPinyinInfo],
    char_pinyin_map: dict[str, list[str]],
) -> str | None:
    """为词源条目确定词级拼音。

    优先级为：pinyin_ice 词级读音 > 词源自带读音 > 单字读音兜底。
    单字兜底只接受每个字都没有多音歧义的情况，避免把“白术”误推成 `bai shu`。
    """

    info = word_pinyin_map.get(row.text)
    if info is not None:
        return info.pinyin
    if row.pinyin:
        return row.pinyin

    syllables: list[str] = []
    for char in row.text:
        pinyins = char_pinyin_map.get(char)
        if not pinyins or len(pinyins) != 1:
            return None
        syllables.append(pinyins[0])
    return " ".join(syllables)


def effective_word_weight(row: WordSourceRow) -> int:
    """确定最终写入原型的词频权重。

    主词源条目只使用主词源自带频率。pinyin_ice 的词频只用于它自己补进来的缺词，
    不反向影响 essay 条目的入库阈值和排序，避免低频三四字语流片段被高权重旧词库抬进来。
    """

    return row.weight


def shuangpin_syllables(text: str, pinyin: str, converter: Converter) -> list[str] | None:
    """把词语拼音转换成逐字双拼码。

    词语编码需要保证“一个汉字对应一个拼音音节”。如果词条里有儿化、多音节外文、
    标注不齐等情况，直接返回 `None`，由上层丢弃。
    """

    syllables = pinyin.split()
    if len(syllables) != len(text):
        return None

    try:
        return [converter(syllable) for syllable in syllables]
    except Exception:
        return None


def build_word_codes(
    text: str,
    pinyin: str,
    converter: Converter,
    aux_map: dict[str, str],
    include_short: bool,
) -> tuple[str, ...] | None:
    """生成词语的全部静态编码。

    短码路线使用逐字双拼首码，并可追加首末字仓颉辅助码；全码路线使用逐字双拼全码，
    也可追加首末字仓颉辅助码。低频词只保留全码路线，高频词才额外给短码路线。
    """

    sps = shuangpin_syllables(text, pinyin, converter)
    if sps is None:
        return None

    if any(len(sp) != 2 for sp in sps):
        return None

    auxes = [aux_map.get(ch) for ch in text]
    if any(not aux for aux in auxes):
        return None

    first_aux = auxes[0][0]
    last_aux = auxes[-1][0]

    short_base = "".join(sp[0] for sp in sps)
    full_base = "".join(sps)
    full_codes = (
        full_base,
        full_base + first_aux,
        full_base + first_aux + last_aux,
    )
    if include_short:
        codes = (
            short_base,
            short_base + first_aux,
            short_base + first_aux + last_aux,
            *full_codes,
        )
    else:
        codes = full_codes
    return tuple(dict.fromkeys(codes))


def collect_word_entries(
    converter: Converter,
    aux_map: dict[str, str],
    seen: dict[str, WordEntry],
    source_rows: Iterator[WordSourceRow],
    min_weight_for_length: Callable[[int], int],
    short_code_min_weight_for_length: Callable[[int], int],
    max_length: int,
    word_pinyin_map: dict[str, WordPinyinInfo],
    char_pinyin_map: dict[str, list[str]],
) -> int:
    """从词频表收词，并生成可迁移的显式词码。

    返回值是丢弃数量，包含低于阈值以外的“无法确定读音/无法生成编码”的候选词。
    """

    dropped = 0
    for row in source_rows:
        text = row.text
        source_weight = row.weight
        weight = effective_word_weight(row)
        length = len(text)
        if (
            length > max_length
            or not is_han_word(text)
            or weight < min_weight_for_length(length)
        ):
            continue

        pinyin = infer_word_pinyin(row, word_pinyin_map, char_pinyin_map)
        if not pinyin:
            dropped += 1
            continue

        include_short = source_weight >= short_code_min_weight_for_length(length)
        codes = build_word_codes(text, pinyin, converter, aux_map, include_short=include_short)
        if not codes:
            dropped += 1
            continue

        entry = WordEntry(
            text=text,
            pinyin=pinyin,
            code=codes[0],
            weight=weight,
            length=length,
            aliases=codes[1:],
        )
        old = seen.get(text)
        if old is None or len(entry.code) < len(old.code) or (
            len(entry.code) == len(old.code) and entry.weight > old.weight
        ):
            seen[text] = entry
    return dropped


def build_word_entries(
    converter: Converter,
    source_path: Path = ESSAY_ZH_HANS,
    cangjie_path: Path = CANGJIE5_DICT,
    pinyin_path: Path = PINYIN_ICE_BASE_DICT,
    char_pinyin_path: Path = CHARS_SOURCE,
    min_weight: int | None = None,
    max_length: int = 4,
) -> tuple[list[WordEntry], int]:
    """构建词语原型表。

    默认使用 `essay-zh-hans.txt` 决定收词和排序，用 `pinyin_ice.base` 借词级读音，
    再用 `chars.txt` 对无歧义词做兜底读音推导。
    """

    aux_map = load_aux_map(cangjie_path)
    entries: list[WordEntry] = []
    seen: dict[str, WordEntry] = {}

    word_pinyin_map = load_word_pinyin_map(pinyin_path)
    char_pinyin_map = load_char_pinyin_map(char_pinyin_path)
    source_texts = {
        row.text
        for row in iter_word_source_rows(source_path)
        if len(row.text) <= max_length and is_han_word(row.text)
    }

    def min_weight_for_length(length: int) -> int:
        if min_weight is not None:
            return min_weight
        return DEFAULT_MIN_WEIGHT_BY_LENGTH.get(length, 10**18)

    def short_code_min_weight_for_length(length: int) -> int:
        return ESSAY_SHORT_CODE_MIN_WEIGHT_BY_LENGTH.get(length, 10**18)

    dropped = collect_word_entries(
        converter=converter,
        aux_map=aux_map,
        seen=seen,
        source_rows=iter_word_source_rows(source_path),
        min_weight_for_length=min_weight_for_length,
        short_code_min_weight_for_length=short_code_min_weight_for_length,
        max_length=max_length,
        word_pinyin_map=word_pinyin_map,
        char_pinyin_map=char_pinyin_map,
    )

    dropped += collect_word_entries(
        converter=converter,
        aux_map=aux_map,
        seen=seen,
        source_rows=iter_pinyin_ice_extra_rows(word_pinyin_map, source_texts),
        min_weight_for_length=lambda length: (
            PINYIN_ICE_EXTRA_TWO_CHAR_MIN_WEIGHT if length == 2 else 10**18
        ),
        short_code_min_weight_for_length=lambda length: 10**18,
        max_length=max_length,
        word_pinyin_map=word_pinyin_map,
        char_pinyin_map=char_pinyin_map,
    )

    entries.extend(seen.values())
    entries.sort(key=lambda entry: (entry.code, -entry.weight, entry.text))
    return entries, dropped


def write_words_prototype(entries: list[WordEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# 词语\t拼音\t主码\t权重\t词长\t附加词码\n")
        for entry in entries:
            aliases = " ".join(entry.aliases)
            f.write(
                f"{entry.text}\t{entry.pinyin}\t{entry.code}\t"
                f"{entry.weight}\t{entry.length}\t{aliases}\n"
            )
