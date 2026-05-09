from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable


SHUANGPIN_DIR = Path(__file__).resolve().parent.parent
if str(SHUANGPIN_DIR) not in sys.path:
    sys.path.append(str(SHUANGPIN_DIR))

from flypyify import flypyify1  # noqa: E402
from zrmify import zrmify1  # noqa: E402


Converter = Callable[[str], str]


def get_converter(schema: str) -> Converter:
    if schema == "zrm":
        return zrmify1
    if schema == "flypy":
        return flypyify1
    raise ValueError(f"unsupported schema: {schema}")

