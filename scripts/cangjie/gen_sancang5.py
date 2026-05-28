import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from core.cangjie_builder import ESSAY_ZH_HANS_PATH, SANCANG5_DICT_PATH, run_generator

def main() -> int:
    return run_generator(
        description="从仓颉五代单字编码按三码规则取码生成字典。",
        default_output=SANCANG5_DICT_PATH,
        default_name="sancang5",
        default_frequency_file=ESSAY_ZH_HANS_PATH,
        max_code_length=3,
        script_name="gen_sancang5.py",
    )

if __name__ == "__main__":
    sys.exit(main())
