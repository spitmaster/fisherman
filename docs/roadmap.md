# Fisherman — 路线图

> 功能级粗粒度路线图。月级更新。
> 细化里程碑见 [milestones.md](./milestones.md);具体待办见 `docs/todo/<branch>.md`。
> 真相源 [SPEC.md](./SPEC.md)。

---

## 当前版本

**v1.0.0**(2026-05 之前) — 完成训练 / 识别 / GUI 主体闭环,详见 [SPEC.md §6.1 模块完成度](./SPEC.md#61-模块完成度)。

---

## 进行中

### P0-1 recognition 多目标识别策略与健壮性(⏳ 2026-05-19 启动)

详见 [milestones/20260204.md M2 段](./milestones/20260204.md#m2--recognition-多目标识别策略与健壮性-)。

- 多目标策略:Top-N / 轮询 / 几何过滤(Strategy 模式)
- 错误处理与重试机制
- FPS / 延迟性能调优
- 责任 agent:[screen-recognition-engineer](./agents/screen-recognition-engineer.md)

---

## P0 — 体验完成度(下一批次)

### P0-2 training_result 模型对比视图
- mAP / loss 曲线对比(同一图表内多个模型)
- 模型导入/导出流程闭环
- 模型版本切换的数据库一致性
- 责任 agent:[pyqt5-ui-developer](./agents/pyqt5-ui-developer.md) + [sqlalchemy-db-engineer](./agents/sqlalchemy-db-engineer.md)

### P0-3 标注器快捷键 + 批量操作
- 快捷键:空格保存、WASD 切换图片、撤销
- 批量校验进度展示
- 责任 agent:[annotation-tool-engineer](./agents/annotation-tool-engineer.md) + [pyqt5-ui-developer](./agents/pyqt5-ui-developer.md)

---

## P1 — 能力扩展

### P1-1 多设备支持(训练 + 推理)✅ 架构骨架已落地(2026-05-22)
- `global_support/device_resolver.py`:枚举 CPU / CUDA 设备,全局缓存
- 训练参数面板加"计算设备"下拉;识别测试/操作页各加"计算设备"下拉
- `config_builder` / `screen_recognition` 全链路透传 `device` 参数
- ⚠️ PyInstaller 打包含 CUDA 依赖的影响**尚未评估**,打包前需补充

### P1-2 自定义点击脚本沙箱
- 用户脚本超时 / import 限制 / 异常捕获
- 责任 agent:[screen-recognition-engineer](./agents/screen-recognition-engineer.md)

### P1-3 多模型切换与热加载
- 运行时切换模型不重启识别
- 模型缓存策略
- 责任 agent:[yolo-training-engineer](./agents/yolo-training-engineer.md) + [sqlalchemy-db-engineer](./agents/sqlalchemy-db-engineer.md)

### P1-4 pytest 测试套件
- 当前只有 simple_test.py / test_modular_structure.py 等冒烟脚本
- 建立 ORM / 调度器 / 校验规则的单元测试
- 责任 agent:fixture-validator(脚手架自带通用 agent)

---

## P2 — 高级特性

### P2-1 分布式训练
- 暂不规划,等用户量级到达再评估

### P2-2 多模型协同识别(投票)
- 同一帧多模型推理 + 结果融合

### P2-3 云端模型同步 / 版本仓库

### P2-4 PyInstaller 一键打包分发
- ⚠️ 红线:仅在用户明确要求时启动
- 责任:暂由 orchestrator 协调,后续可引入 packaging-engineer

---

## 技术债

| # | 内容 | 优先级 |
|---|------|--------|
| TD-1 | 旧版 `gui/tabs/recognition_tab.py` 已被替代,需决定保留或删除 | 低 |
| TD-2 | 数据库无 `ON DELETE CASCADE`,删训练任务时业务层手动级联 | 中 |
| TD-3 | 训练/识别线程内有散落的 `print` 调试,应统一进 logging | 中 |
| TD-4 | YOLO `runs/` 缓存目录与 `training_result/` 同步逻辑不明确 | 低 |
| TD-5 | 脚手架自带的 codeviz / miniprogram / 3D agent 与本项目无关,可删 | 低 |
| TD-6 | `olddocs/技术设计/`、`olddocs/需求文档/`、`olddocs/README.md` 是脚手架占位,吸收完后可删 | 低 |

---

## 非目标(明确不做)

参见 [SPEC.md §1.3](./SPEC.md#13-非目标non-goals):
- ❌ Web / 云端推理服务
- ❌ 分布式训练
- ❌ 从零开始的模型结构设计
- ❌ macOS / Linux 正式支持(理论可跑,不投入测试)

---

## 已发布版本

| 版本 | 日期 | 简介 |
|------|------|------|
| v1.0.0 | 2026 上半年(具体日期见 git tag) | 训练 / 识别 / GUI 主体闭环 |

> 当版本数 ≥ 5 时,按全局 ~/.claude/CLAUDE.md §3.3 把旧版本压缩到 `docs/roadmap/archive/early-versions.md`。

---

## 变更日志

| 日期 | 变更 |
|------|------|
| 2026-05-22 | P1-1 多设备支持骨架 ✅(架构落地,打包评估待补);SPEC 不变量 6 更新 |
| 2026-05-19 | SDD 体系建立 ✅(M1 完结);P0-1 多目标识别策略启动(M2)。"进行中"区从 SDD 切换为 P0-1 |
| 2026-05-19 | 初版。从 `olddocs/原始设计文档/09_roadmap.md` 吸收,按 SDD 三档规划分级到 P0/P1/P2 |
