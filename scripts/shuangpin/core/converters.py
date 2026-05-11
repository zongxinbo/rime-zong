from typing import Callable

from .flypyify import flypyify1
from .zrmify import zrmify1


Converter = Callable[[str], str]


def get_converter(schema: str) -> Converter:
    if schema in {"zrm", "zrm_single"}:
        return zrmify1
    if schema in {"flypy", "flypy_single"}:
        return flypyify1
    raise ValueError(f"unsupported schema: {schema}")
