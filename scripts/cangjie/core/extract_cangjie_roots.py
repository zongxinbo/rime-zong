from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.io import parse_cangjie_dict
from core.paths import CANGJIE5_DICT_PATH, REPO_ROOT


DEFAULT_OUTPUT_PATH = REPO_ROOT / "scripts" / "cangjie" / "data" / "roots.txt"

MAIN_ROOT_CODES = set("abcdefghijklmnopqrstuvwy")


# 纯仓颉字根规则源。
# 这里不放从 IDS、郑码或整字码推测出来的扩展候选；只放仓颉字母及公开辅形。
# 第 4 列是例字种子，脚本会用仓颉码表和 IDS 再校验、补证据。
ROOT_SPEC_TEXT = """
日	a	主根	明,早,良,书,冒	日形；包含曰形等轻微笔形差异
{日横卧}	a	辅形	巴,眉,色,免,象	日形横卧
月	b	主根	朕,肝,胃,目,助	月形；包含肉月旁、目外形等近形
{月外框}	b	辅形	用,同,禺,奥,皿	月形或目形的外框
冖	b	辅形	冠,罕,骨,旁,雷	月形变矮后的盖形
{冎内重影}	b	辅形	冎,涡,骨,体	月形内部累增式衍生
{斜月}	b	辅形	望,亘,炙,然,豹	斜月形
爫	b	辅形	爱,采,受,溪,菜	爪头整形
金	c	主根	鉴,淦,铜,刘,镜	金形
{金下两点}	c	辅形	丫,弟,业,仆,尞	金下方两点
八	c	辅形	只,谷,亦,扒,巷	金形倒转
{儿形}	c	辅形	四,西,空,詹,沿	金形变形
木	d	主根	来,困,相,茶,东	木形
{木主干}	d	辅形	才,子,乎,争,孩	木形主干
{木横卧}	d	辅形	皮,也,五,韦,决	木形横卧
水	e	主根	冰,永,丞,踏,氹	水形
又	e	辅形	支,叉,各,厦,及	水形两边笔画相叠
氵	e	辅形	沿,溪,涂,衍,汇	水偏旁形
氺	e	辅形	求,录,康,黎,鳏	水字底形
{犀下}	e	辅形	犀,迟,属,瞩,皋	水形变形，五代新增
火	f	主根	灰,秋,焚,灶,炎	火形
灬	f	辅形	照,鲤,鸟,尽,驹	火字底形
小	f	辅形	丝,系,平,尚,示	火形减一点或小形
{小倒形}	f	辅形	樱,觉,战,佥,米	小形倒转
{不字形}	f	辅形	不,祈,否,社,𣎴	火形衍生
土	g	主根	走,再,里,球,动	土形
士	g	辅形	仕,吉,款,树,壻	土形变形
竹	h	主根	𢎉,竺,简,符,噬	竹形或竹字头
丿	h	辅形	乃,亢,牛,白,千	斜撇形
{爪撇形}	h	辅形	后,反,爪,析,爬	斜撇衍生形
戈	i	主根	戒,戚,越,几,我	戈形
丶	i	辅形	冰,尤,刃,社,之	点形
广	i	辅形	库,厕,厦,鹧,渡	戈形向下衍生
厶	i	辅形	台,去,糸,充,芸	戈形向左衍生
十	j	主根	古,车,哉,办,刊	横竖相交形
宀	j	辅形	安,宋,空,伫,萱	十形两端下垂、中间上缩
大	k	主根	爽,淹,器,决,奇	大形
{大左上}	k	辅形	右,力,九,老,希	大形左上角
乂	k	辅形	文,丈,希,教,狗	撇捺交叉形
疒	k	辅形	病,痛,痊,痴,嫉	大形变形衍生
中	l	主根	忠,仲,史,事,虫	中形
丨	l	辅形	引,川,介,亦,冘	纵形
肀	l	辅形	书,尽,事,唐,庚	中形上下皆竖的变形
衤	l	辅形	衫,裤,被,裇,袜	衣旁变形，上下皆竖
一	m	主根	旦,低,天,不,合	横形
{一提形}	m	辅形	刁,冰,匀,羽,划	一形整形或提形
厂	m	辅形	原,历,炭,危,厘	一形左端向下衍生
石	m	辅形	石,百,豚,光,状	一形变形
工	m	辅形	空,巫,丘,哥,功	一形累增式向下衍生
弓	n	主根	弦,穷,疆,弟,夷	弓形
亅	n	辅形	丁,了,予,到,赤	竖钩形
乙	n	辅形	乃,承,今,丑,吴	横钩形
{弓左衍}	n	辅形	你,色,陷,久,夕	弓形向左衍生
几	n	辅形	乞,亢,役,飞,佩	弓形向下衍生
人	o	主根	走,以,舍,内,陕	人形
{人末笔变形}	o	辅形	气,海,知,攻,御	人形末笔变形
亻	o	辅形	仁,确,众,丘,岳	人偏旁形
{人右边形}	o	辅形	啄,象,飞,兆,狐	人形右边
入	o	辅形	尺,夫,规,迭,之	人形末笔
心	p	主根	思,沁,闷,宁,必	心形
忄	p	辅形	怕,怡,恒,悭,筷	心偏旁形
⺗	p	辅形	恭,慕,忝,添,隳	心字底形
匕	p	辅形	旨,老,化,屯,顷	心形中央形
{心乙形}	p	辅形	托,虐,也,世,切	心形变形
{心戈形}	p	辅形	代,民,低,式,曳	心形变形
勹	p	辅形	炮,渴,鸟,队,象	心形中央倒转
手	q	主根	拿,掰,举,挙,罉	手形
扌	q	辅形	打,浙,誓,找,我	手偏旁形
{手主干}	q	辅形	清,承,羊,耘,扥	手形主干
夫	q	辅形	夫,那,专,看,着	手形变形
{年下}	q	辅形	降,韦,桀,年,鵇	手形变形
口	r	主根	吹,石,区,巳,官	四边形内不含其他笔画
尸	s	主根	尺,局,旎,户,房	尸形
{尸侧形}	s	辅形	己,巨,彗,尹,刍	尸形上半或侧形
刀	s	辅形	司,局,成,豕,犭	尸形末尾缩短
匚	s	辅形	臣,虐,姬,区,巨	尸侧形反转
耳	s	辅形	耳,耶,长,套,发	尸形半累增式衍生
{乍形}	s	辅形	乍,非,假,面,高	尸形竖笔上下延伸，五代新增
廿	t	主根	甘,庶,燕,革,难	并列形
卄	t	辅形	昔,共,其,典,毕	廿形末笔伸长
艹	t	辅形	曲,草,雚,卅,卉	两侧对称并列形
{虚下繁}	t	辅形	虚,墟,嘘,联,关	廿形变形
业	t	辅形	业,虚,并,皿,恤	廿形主干
{并变形}	t	辅形	豆,益,立,并,站	廿形变形
山	u	主根	仙,茁,昆,幽,峡	山形
凵	u	辅形	齿,凶,目,息,画	仰形
乚	u	辅形	孔,光,己,辉,改	山形末尾缩短
屮	u	辅形	嗤,艸,逆,朔,刍	山形竖笔伸长
女	v	主根	汝,娶,好,魏,威	女形
幺	v	辅形	巡,俞,糸,互,彔	纽形
{女折角}	v	辅形	県,吴,亡,曷,甚	女形改变角度
{女斜折}	v	辅形	收,以,氏,民,瓜	女形改变角度
{鼠下}	v	辅形	鼠,鼬,巤,猎,邋	女形打斜
{衣下}	v	辅形	很,展,衣,衷,表	女形向右衍生
田	w	主根	畦,车,毕,宙,伸	方形
囗	w	辅形	国,罪,黑,衰,贯	方形外框，内部含其他笔画
母	w	辅形	母,毋,海,莓,敏	田形变形
卜	y	主根	下,外,上,真,正	卜形
{卜横卧}	y	辅形	充,文,亡,母,言	卜形横卧
⺀	y	辅形	斗,雨,於,冬,尽	卜形横缩成点
辶	y	辅形	连,追,逆,巡,涟	卜形向下衍生
""".strip()


@dataclass(frozen=True)
class RootSpec:
    shape: str
    code: str
    kind: str
    seed_examples: tuple[str, ...]
    note: str


@dataclass
class RootRow:
    shape: str
    code: str
    kind: str
    standalone_codes: str
    examples: str
    note: str


def is_named_shape(shape: str) -> bool:
    return shape.startswith("{") and shape.endswith("}")


def parse_specs() -> list[RootSpec]:
    specs: list[RootSpec] = []
    seen: set[str] = set()
    for lineno, line in enumerate(ROOT_SPEC_TEXT.splitlines(), start=1):
        parts = line.split("\t")
        if len(parts) != 5:
            raise ValueError(f"字根规则第 {lineno} 行应有 5 列，实际为 {len(parts)} 列：{line}")
        shape, code, kind, examples, note = parts
        if shape in seen:
            raise ValueError(f"重复字根标识：{shape}")
        if kind not in {"主根", "辅形"}:
            raise ValueError(f"字根规则第 {lineno} 行类别非法：{kind}")
        if len(code) != 1 or code not in MAIN_ROOT_CODES:
            raise ValueError(f"字根规则第 {lineno} 行编码非法：{code}")
        seen.add(shape)
        specs.append(RootSpec(shape, code, kind, tuple(examples.split(",")), note))
    return specs


def validate_main_roots(specs: list[RootSpec]) -> None:
    main_roots = [spec for spec in specs if spec.kind == "主根"]
    main_codes = {spec.code for spec in main_roots}
    if len(main_roots) != 24:
        raise ValueError(f"主根数量应为 24，实际为 {len(main_roots)}")
    if main_codes != MAIN_ROOT_CODES:
        missing = "".join(sorted(MAIN_ROOT_CODES - main_codes))
        extra = "".join(sorted(main_codes - MAIN_ROOT_CODES))
        raise ValueError(f"主根键位不完整，缺少={missing!r} 多出={extra!r}")


def read_cangjie_codes(path: Path) -> dict[str, list[str]]:
    codes: dict[str, list[str]] = defaultdict(list)
    for entry in parse_cangjie_dict(path):
        if len(entry.text) == 1:
            codes[entry.text].append(entry.code)
    return {
        char: sorted(set(items), key=lambda code: (code.startswith(("x", "z")), len(code), code))
        for char, items in codes.items()
    }


def choose_examples(
    spec: RootSpec,
    codes: dict[str, list[str]],
    limit: int,
) -> str:
    examples: list[str] = []
    seen: set[str] = set()

    def add(char: str) -> None:
        if char and char not in seen and char in codes:
            seen.add(char)
            examples.append(char)

    for char in spec.seed_examples:
        add(char)

    return ",".join(examples[:limit])


def build_rows(
    specs: list[RootSpec],
    codes: dict[str, list[str]],
    example_limit: int,
) -> list[RootRow]:
    rows: list[RootRow] = []
    for spec in specs:
        standalone = ",".join(codes.get(spec.shape, [])) if not is_named_shape(spec.shape) else ""
        rows.append(
            RootRow(
                shape=spec.shape,
                code=spec.code,
                kind=spec.kind,
                standalone_codes=standalone,
                examples=choose_examples(spec, codes, example_limit),
                note=spec.note,
            )
        )
    return rows


def write_roots(path: Path, rows: list[RootRow]) -> None:
    lines = [
        "# encoding: utf-8",
        "# 仓颉五代纯字根表，只列仓颉字母及其公开辅形。",
        "# 本表不包含从 IDS、郑码字根或整字仓颉码推测出的扩展候选。",
        "# 字根规则源在脚本内维护；本字码由脚本从仓颉五码表自动补充。",
        "# 同一类细微字形差异合并为一行；无法稳定用单个 Unicode 字符表示的形块用 {...} 标识。",
        "# 编码是该形块作为部件参与拆字时使用的仓颉键，不一定等于该形块独立成字时的全码。",
        "# 列：字根<TAB>编码<TAB>类别<TAB>本字码<TAB>例字<TAB>说明",
    ]
    lines.extend(
        "\t".join(
            (
                row.shape,
                row.code,
                row.kind,
                row.standalone_codes,
                row.examples,
                row.note,
            )
        )
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成仓颉五代纯字根表")
    parser.add_argument("--cangjie-dict", type=Path, default=CANGJIE5_DICT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--examples-per-root", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    specs = parse_specs()
    validate_main_roots(specs)
    codes = read_cangjie_codes(args.cangjie_dict)
    rows = build_rows(specs, codes, args.examples_per_root)
    write_roots(args.output, rows)
    main_count = sum(1 for spec in specs if spec.kind == "主根")
    aux_count = len(specs) - main_count
    print(f"纯仓颉字根={len(specs)} 主根={main_count} 辅形={aux_count} 写出：{args.output}")


if __name__ == "__main__":
    main()
