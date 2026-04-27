#!/usr/bin/env python3

import sys
from cangjie_builder import run_generator

def main() -> int:
    return run_generator(
        description="从仓颉五代单字编码按四码规则取码生成字典。",
        default_output="sicang5/sicang5.dict.yaml",
        default_name="sicang5",
        default_frequency_file="sancang5/essay-zh-hans.txt",
        max_code_length=4,
        script_name="gen_sicang5.py",
        default_sort="original",
        default_no_vocabulary=True,
        default_max_phrase_length=1,
    )

if __name__ == "__main__":
    sys.exit(main())
