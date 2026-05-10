from __future__ import annotations

from pathlib import Path
from typing import Callable

from .cangjie import load_aux_map
from .io import iter_rime_dict_rows, parse_int
from .models import WordEntry
from .paths import CANGJIE5_DICT, PINYIN_ICE_BASE_DICT


Converter = Callable[[str], str]

# 默认收词阈值按词长区分：二字词编码短、语义凝固度高，放宽到很低
# 以覆盖“白术”这类低频实词；三四字词数量膨胀更快，保持中等阈值。
DEFAULT_MIN_WEIGHT_BY_LENGTH = {
    2: 10,
    3: 3000,
    4: 3000,
}

# 这些字通常只承担语气作用，放在词尾时更像拼音输入法的造句片段，
# 不适合作为音形码的固定词条。过滤时同时核对拼音，避免误删异读词。
MOOD_SUFFIX_PINYIN = {
    "啊": "a",
    "呀": "ya",
    "吧": "ba",
    "呢": "ne",
    "吗": "ma",
    "嘛": "ma",
    "啦": "la",
    "咯": "lo",
    "呗": "bei",
    "哇": "wa",
    "哦": "o",
    "噢": "o",
    "哟": "yo",
}

# 这些结构助词结尾的短语信息量较低，例如“代理商的”“安全的”。
# 音形方案更适合保留“代理商”“安全”这类实词本体。
STRUCTURAL_SUFFIX_PINYIN = {
    "的": "de",
    "地": "de",
    "着": "zhe",
    "了": "le",
}

# “必然会、应该会、可能会”这类词组虽然频率不低，但更像语流片段。
# 只过滤“会”前一个字落在此集合里的三字及以上短语，不影响“开会”
# “会议”“奥运会”等真正词汇。
AUXILIARY_HUI_PREV = set(
    "然定该能将也都还仍就便"
    "才再只必常总须需却先后"
    "可真更不没未应"
)

# “并签署、并按照”这类以“并”连接后续谓词的片段不进词库；
# 但“并发、并行、并查集”等已经词化或术语化的条目需要保留。
BING_PREFIX = "并"
BING_CONTENT_PREFIXES = (
    "并发",
    "并行",
    "并购",
    "并联",
    "并网",
    "并线",
    "并列",
    "并入",
    "并轨",
    "并案",
    "并表",
    "并肩",
    "并用",
    "并存",
    "并重",
    "并称",
    "并举",
    "并吞",
    "并拢",
    "并蒂",
    "并排",
    "并进",
    "并查",
)


def is_han_word(text: str) -> bool:
    return len(text) >= 2 and all("\u3400" <= ch <= "\u9fff" for ch in text)


def is_light_phrase(text: str, pinyin: str) -> bool:
    syllables = pinyin.split()
    if len(syllables) != len(text):
        return True

    last = text[-1]
    last_pinyin = syllables[-1]
    if MOOD_SUFFIX_PINYIN.get(last) == last_pinyin:
        return True
    if STRUCTURAL_SUFFIX_PINYIN.get(last) == last_pinyin:
        return True
    if len(text) >= 3 and last == "会" and last_pinyin == "hui" and text[-2] in AUXILIARY_HUI_PREV:
        return True
    if len(text) >= 3 and text.startswith(BING_PREFIX) and not text.startswith(BING_CONTENT_PREFIXES):
        return True
    return False


def shuangpin_syllables(text: str, pinyin: str, converter: Converter) -> list[str] | None:
    """把词语拼音转换成逐字双拼码。

    词语编码需要保证“一个汉字对应一个拼音音节”。如果词条里有儿化、
    多音节外文、标注不齐等情况，直接返回 `None`，由上层丢弃。
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
) -> tuple[str, ...] | None:
    """生成词语的全部静态编码。

    规则分成两条路线：短码使用逐字双拼首码，并可追加首末字仓颉辅码；
    全码使用逐字双拼全码，也可追加首末字仓颉辅码。这样既保留双拼
    输入习惯，又能在词库扩大后用仓颉辅助码继续定重。
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
    codes = (
        short_base,
        short_base + first_aux,
        short_base + first_aux + last_aux,
        full_base,
        full_base + first_aux,
        full_base + first_aux + last_aux,
    )
    return tuple(dict.fromkeys(codes))


def collect_word_entries(
    converter: Converter,
    aux_map: dict[str, str],
    seen: dict[tuple[str, str], WordEntry],
    source_path: Path,
    min_weight_for_length: Callable[[int], int],
    max_length: int,
) -> int:
    dropped = 0
    for parts in iter_rime_dict_rows(source_path):
        if len(parts) < 2:
            continue
        text, pinyin = parts[0], parts[1]
        weight = parse_int(parts[2], 0) if len(parts) >= 3 else 0
        length = len(text)
        if (
            length > max_length
            or not is_han_word(text)
            or is_light_phrase(text, pinyin)
            or weight < min_weight_for_length(length)
        ):
            continue
        codes = build_word_codes(text, pinyin, converter, aux_map)
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
        key = (text, codes[0])
        old = seen.get(key)
        if old is None or entry.weight > old.weight:
            seen[key] = entry
    return dropped


def build_word_entries(
    converter: Converter,
    source_path: Path = PINYIN_ICE_BASE_DICT,
    cangjie_path: Path = CANGJIE5_DICT,
    min_weight: int | None = None,
    max_length: int = 4,
) -> tuple[list[WordEntry], int]:
    aux_map = load_aux_map(cangjie_path)
    entries: list[WordEntry] = []
    dropped = 0
    seen: dict[tuple[str, str], WordEntry] = {}

    def min_weight_for_length(length: int) -> int:
        if min_weight is not None:
            return min_weight
        return DEFAULT_MIN_WEIGHT_BY_LENGTH.get(length, 3000)

    dropped = collect_word_entries(
        converter=converter,
        aux_map=aux_map,
        seen=seen,
        source_path=source_path,
        min_weight_for_length=min_weight_for_length,
        max_length=max_length,
    )

    entries.extend(seen.values())
    entries.sort(key=lambda e: (e.code, -e.weight, e.text))
    return entries, dropped


def write_words_prototype(entries: list[WordEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# 词语\t拼音\t六码原型\t权重\t词长\t附加词码\n")
        for entry in entries:
            aliases = " ".join(entry.aliases)
            f.write(
                f"{entry.text}\t{entry.pinyin}\t{entry.code}\t"
                f"{entry.weight}\t{entry.length}\t{aliases}\n"
            )
