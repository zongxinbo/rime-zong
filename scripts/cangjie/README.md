# 仓颉方案生成系统

本目录用于管理 Sicang5/Wucang5 方案的生成与简码设计。

## 快速上手
使用以下指令生成最终码表：

```powershell
# 1. 设计简码 (在 prototypes/ 生成建议稿)
python scripts/cangjie/core/gen_shortcut_1.py
python scripts/cangjie/core/gen_shortcut_2.py
python scripts/cangjie/core/gen_shortcut_3.py

# 2. 构建词库 (生成最终 .dict.yaml)
python scripts/cangjie/gen_sicang5.py
python scripts/cangjie/gen_wucang5.py
```

## 技术规范
详见 [CANGJIE_SPEC.md](CANGJIE_SPEC.md) 了解详细的设计算法与取码规则。
