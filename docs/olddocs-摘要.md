# olddocs 吸收摘要

> 本文档记录 `olddocs/原始设计文档/` 的吸收过程与结论
> 吸收时间:2026-05-19
> 吸收人:AI (Claude Code)

---

## 1. 吸收源

`olddocs/原始设计文档/` 共 10 份文档(原 `design/` 目录,git 历史已通过 `git mv` 保留):

| 原文档 | 主题 | 价值评估 |
|--------|------|---------|
| 01_overview.md | 项目定位、目标用户、功能清单、技术栈摘要 | ⭐⭐⭐ 高 — 直接吸收到 SPEC §1/§2 |
| 02_architecture.md | 4 层架构、模块划分、设计模式、线程模型 | ⭐⭐⭐ 高 — 直接吸收到 SPEC §5 + 架构不变量 |
| 03_features.md | 按 GUI 入口拆解的功能点 | ⭐⭐⭐ 高 — 直接吸收到 SPEC §2 功能需求 |
| 04_modules.md | 各包 / 文件 / 类的职责清单 | ⭐⭐ 中 — 摘要到 SPEC §5;详情留 olddocs/ 作参考 |
| 05_database.md | ORM 模型、表结构、索引、生命周期 | ⭐⭐⭐ 高 — 直接吸收到 SPEC §5 数据模型 |
| 06_workflows.md | 训练 / 识别 / 调度 / 启动关闭 端到端时序图 | ⭐⭐⭐ 高 — 吸收到 SPEC §5 关键流程 |
| 07_directory_layout.md | 代码与运行期目录结构 | ⭐⭐ 中 — 关键目录吸收到 SPEC §5;详情留 olddocs |
| 08_tech_stack.md | 依赖清单、版本、安装、启动 | ⭐⭐ 中 — 摘要到 SPEC §5 + 项目根 README |
| 09_roadmap.md | 模块完成度、进行中项、技术债、路线图 | ⭐⭐⭐ 高 — 吸收到 SPEC §6 现状 + 后续 docs/roadmap.md |
| README.md | 文档索引 | ⭐ 低 — 已被本摘要替代 |

---

## 2. 吸收去向

### 2.1 `docs/SPEC.md`(SDD 真相源)
吸收所有 P0 内容:

- **§1 项目概述** ← `01_overview.md` §1-§4(项目定位、目标用户、核心功能、非目标)
- **§2 功能需求** ← `03_features.md` 全部 11 节,按"训练标签页 / 标注 / 识别测试 / 识别操作 / 设置 / 调度"重组
- **§3 非功能需求** ← `01_overview.md` §6 + `02_architecture.md` §7-§8(性能、并发、错误边界)
- **§4 UI 结构** ← `02_architecture.md` §4 + `04_modules.md` §5(Tab 列表、Dialog 列表)
- **§5 技术架构** ← `02_architecture.md` §1-§3 + `04_modules.md` + `05_database.md` + `07_directory_layout.md` + `08_tech_stack.md` 合并
- **§6 当前状态与验收标准** ← `09_roadmap.md` §1-§3
- **§7 关键流程** ← `06_workflows.md` 全部 6 节(训练 / 识别 / 调度 / 启动关闭 / 错误恢复)

### 2.2 `docs/roadmap.md`(后续生成)
吸收 `09_roadmap.md` §4-§5(P0/P1/P2 路线图 + 技术债)。

### 2.3 保留在 `olddocs/` 不动
以下作为详细参考长期保留,**不复制内容到 docs/**,避免冗余:

- `04_modules.md` 各类各方法的完整清单 → 维护代码时直接看代码 + docstring
- `07_directory_layout.md` 运行期目录的详尽描述 → 程序自动创建
- `08_tech_stack.md` 安装常见问题清单 → 已有 `README.md` 覆盖大部分

---

## 3. 吸收过程中识别的差异(代码 vs 文档)

实际代码扫描发现以下与设计文档不完全一致的地方:

| 项 | 设计文档 | 实际代码 | 处理 |
|----|---------|---------|------|
| `gui/screen_area_selector.py` | 未提及 | 存在(屏幕区域选择器) | 已补入 SPEC §5 模块清单 |
| `recognition/visualizer.py` | 未提及 | 存在(识别可视化) | 已补入 SPEC §5 模块清单 |
| `gui/detail_tabs/training/training_controller.py` | 未提及 | 存在(控制器层) | 已补入 SPEC §5 模块清单 |
| 测试脚本 `test_*.py` | 列了 5 个 | 实际有 `simple_test.py`、`test_modular_structure.py` | SPEC §6 验收标准引用现有脚本 |

设计文档主体准确度约 95%,差异主要是文档晚于代码、未及时同步;吸收时按代码现状修正。

---

## 4. 后续维护建议

1. **olddocs/ 只读化**:吸收完成后,`olddocs/原始设计文档/` 视为冻结的历史快照,**不再更新**
2. **新增/修改设计** 一律改 `docs/SPEC.md`,并按 SDD 流程同步更新代码
3. **若 SPEC.md 与 olddocs 内容冲突**:以 SPEC.md 为准,olddocs 仅供溯源
4. **olddocs/技术设计/、olddocs/需求文档/**:这两个是脚手架自带的占位模板,与本项目无关,后续可删
5. **`olddocs/README.md`**:脚手架自带的"吸收指南"说明,可在确认无需后删除

---

## 5. 待办(本次未做)

- [ ] 生成 `docs/roadmap.md`(吸收 09_roadmap.md §4-§5)
- [ ] 生成 `docs/milestones.md` 主索引 + `docs/milestones/20260204.md`
- [ ] 生成 `docs/todo/20260204.md`(当前分支待办)
- [ ] 生成项目根 `CLAUDE.md`(按全局 ~/.claude/CLAUDE.md §7 最小骨架)
- [ ] 决定是否删除 `olddocs/技术设计/`、`olddocs/需求文档/`、`olddocs/README.md` 等脚手架占位
