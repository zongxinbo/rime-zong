# 仓颉方案生成系统

本目录用于管理 Sicang5/Wucang5 方案的生成与简码设计。

# 1. 设计简码 (在 prototypes/ 生成建议稿)
使用核心脚本分析语料并生成简码原型文件。
```powershell
python scripts/cangjie/core/gen_shortcut_1.py
python scripts/cangjie/core/gen_shortcut_2.py
python scripts/cangjie/core/gen_shortcut_3.py
python scripts/cangjie/core/gen_shortcut_4.py
```

# 2. 生成最终码表 (Wucang5)

## 模式 A：全字符竞争模式 (Default)
此模式平衡了各字符集的简码分布，允许长码字抢占低频原主位。默认不生成四简。
```powershell
python scripts/cangjie/gen_wucang5.py
```

## 模式 B：GB2312 绝对保护模式
此模式强制所有 GB2312 字符码长 ≤ 4，并保护 GB2312 原生位置。默认自动生成四简。
```powershell
python scripts/cangjie/gen_wucang5.py --gb-only --s2-coverage 1.0 --s3-coverage 1.0
```

# 3. 生成最终码表 (Sicang5)
Sicang5 现在支持与 Wucang5 相同的二简/三简参数化配置（不包含四简）。
```powershell
python scripts/cangjie/gen_sicang5.py
```

## 技术规范
详见 [CANGJIE_SPEC.md](CANGJIE_SPEC.md) 了解详细的设计算法与取码规则。
