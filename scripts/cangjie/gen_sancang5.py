import sys
from pathlib import Path
from cangjie_builder import run_generator

def main() -> int:
    return run_generator(
        description="从仓颉五代单字编码按三码规则取码生成字典。",
        default_output="sancang5/sancang5.dict.yaml",
        default_name="sancang5",
        default_frequency_file="sancang5/essay-zh-hans.txt",
        max_code_length=3,
        script_name="gen_sancang5.py",
    )

if __name__ == "__main__":
    sys.exit(main())
