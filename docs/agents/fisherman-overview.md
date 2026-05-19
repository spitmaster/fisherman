---
name: "fisherman-overview"
description: "Fisherman 项目的 agent 拓扑与契约文档。给 fisherman-orchestrator 与各专职 agent 提供共享的上下文(项目定位、模块边界、共用契约、架构不变量、里程碑路径)。本身不是 agent,是项目级文档。"
model: opus
color: purple
memory: project
---

# Fisherman — Agent 拓扑与契约

> 本文件**不是 agent**,是 fisherman 项目的 agent 体系总览。
> 任何 agent 启动时若涉及跨模块协作,**先读本文件**建立上下文。
> 真相源指向 [docs/SPEC.md](../SPEC.md)。

---

## 1. 项目一句话

**Fisherman** 是 Windows 桌面端的视觉自动化工具,基于 YOLOv8,提供「数据标注 → 模型训练 → 屏幕识别 → 自动点击」一站式 GUI 闭环。技术栈:Python 3.8+ / PyQt5 / PyTorch CPU / Ultralytics YOLO / SQLAlchemy + SQLite / mss / pyautogui / uv 包管理。

---

## 2. 角色映射

| 模块 / 关注点 | 责任 agent | 主要源代码位置 |
|---------------|-----------|---------------|
| 跨模块调度、契约对齐、端到端联调 | [fisherman-orchestrator](./fisherman-orchestrator.md) | (全局) |
| YOLOv8 训练管道、超参、回调、产物归档 | [yolo-training-engineer](./yolo-training-engineer.md) | `training/training/` |
| 屏幕截图 + YOLO 推理 + pyautogui 点击 | [screen-recognition-engineer](./screen-recognition-engineer.md) | `recognition/` |
| PyQt5 主窗口、Tabs、Dialogs、信号槽 | [pyqt5-ui-developer](./pyqt5-ui-developer.md) | `gui/` |
| SQLAlchemy ORM、SQLite schema、迁移、索引 | [sqlalchemy-db-engineer](./sqlalchemy-db-engineer.md) | `global_support/database.py` + `sql/` |
| TaskScheduler、线程模型、并发互斥 | [task-scheduler-engineer](./task-scheduler-engineer.md) | `global_support/task_scheduler.py` |
| 标注器逻辑、Strategy 校验、YOLO 格式转换 | [annotation-tool-engineer](./annotation-tool-engineer.md) | `training/annotation/` + `gui/annotation_window.py` |

---

## 3. 共享数据契约

下游 agent 必须遵守的关键数据结构(以 SPEC §5.5 为权威):

### 3.1 ORM 模型(SQLAlchemy)

`global_support/database.py` 中定义,**所有 agent 共读**:

- `TrainingTask` — 训练任务/数据集
- `TrainingLog` — 训练日志
- `RecognitionTask` — 识别任务
- `RecognitionLog` — 识别日志
- `RecognitionDetail` — 单次识别详情
- `ModelVersion` — 模型版本

**改动这些表必须经 sqlalchemy-db-engineer**;改完通知 orchestrator 全局回归。

### 3.2 任务调度协议

提交重任务统一走:
```python
task_scheduler.submit(Task(
    task_id=uuid,
    task_type='TRAINING' | 'RECOGNITION',
    status='PENDING',
    priority=int,
))
```
绕过调度器直接起线程是**红线违反**。

### 3.3 路径约定

- 训练集:`training_data/{task_uuid}/dataset/{images,labels}/`
- 训练结果:`training_result/{task_name}/weights/{best,last}.pt`
- 标注格式:YOLO `.txt`(class_id cx cy w h,归一化)
- 模型导入:`models/`

集中由 `training/dataset_path_manager.py::DatasetPathManager` 管理。

### 3.4 UI ↔ 后台通信

跨线程更新 UI **必须**通过 Qt 信号槽:
```python
class Worker(QObject):
    progress = pyqtSignal(int, str)  # epoch, message
    finished = pyqtSignal(dict)       # 结果
```
**禁止**在后台线程里直接 `widget.setText(...)`。

---

## 4. 架构不变量(红线)

每个 agent 动手前**必须扫一遍**,可能违反时主动汇报:

1. **【MUST】UI 线程安全** — 跨线程更新 QWidget 一律走信号槽
2. **【MUST】重任务串行** — 训练/识别经 task_scheduler.submit(),禁绕过
3. **【MUST】UUID 主键** — 数据库主键 + 训练集目录名一律 UUID v4
4. **【MUST】uv.lock 锁定** — 依赖锁文件入版本控制
5. **【MUST】CPU 推理** — 当前 CPU only,引入 GPU 需评估打包影响
6. **【MUST】SPEC 优先** — 业务规则改动先改 [SPEC.md](../SPEC.md),再改代码
7. **【SHOULD】logging 体系** — 新代码禁止 print,走 logging
8. **【SHOULD】opencv-python-headless** — 不引入带 Qt 的 opencv-python,避免冲突

详见 [SPEC.md §8 架构不变量](../SPEC.md#8-架构不变量不可违反)。

---

## 5. 关键流程边界(谁负责什么)

### 训练流程
```
TrainingTab (pyqt5) → TrainingManager → DatasetPathManager (paths)
   → AnnotationManager (annotation-tool) → AnnotationValidator
   → TaskScheduler.submit (task-scheduler) → TrainingExecutor (yolo-training)
   → YOLOTrainer → ultralytics.YOLO.train()
   → CallbackHandler → GUI 回写(信号槽) + LogManager → DB (sqlalchemy-db)
   → ResultSaver → model_versions 插入
```

### 识别流程
```
RecognitionActionTab (pyqt5) → recognition_manager
   → TaskScheduler.submit → ScreenRecognition (screen-recognition)
   → 后台线程:mss 截屏 → YOLO 推理 → 过滤 → 回调 → pyautogui 点击
   → 写 recognition_details (sqlalchemy-db)
```

---

## 6. 任务路由表

| 任务关键词 | 路由到 agent |
|-----------|------------|
| YOLO / 训练 / epoch / batch / mAP / 超参 | yolo-training-engineer |
| 屏幕识别 / FPS / mss / 截图 / 点击 / pyautogui / ROI | screen-recognition-engineer |
| Tab / Dialog / Widget / 信号槽 / Qt 主窗口 / 标注 UI | pyqt5-ui-developer |
| 表 / ORM / 索引 / 迁移 / SQL / 数据库 | sqlalchemy-db-engineer |
| 调度 / 线程 / 并发 / Condition / 锁 | task-scheduler-engineer |
| 标注 / 校验 / Strategy / YOLO .txt / 导出标注 | annotation-tool-engineer |
| 跨多个上述 / 不确定 / 联调 | fisherman-orchestrator |

---

## 7. 里程碑路径(P0 → P2)

按 [SPEC.md §6](../SPEC.md#6-当前状态与验收标准) 与 olddocs/09_roadmap.md:

### P0 — 体验完成度(当前焦点)
1. recognition 多目标识别策略与健壮性 → screen-recognition-engineer
2. training_result 模型对比视图 → pyqt5-ui-developer + sqlalchemy-db-engineer
3. 标注器快捷键 + 批量操作 → annotation-tool-engineer + pyqt5-ui-developer

### P1 — 能力扩展
1. GPU 训练支持(可配置 device) → yolo-training-engineer
2. 自定义点击脚本的沙箱与错误恢复 → screen-recognition-engineer
3. 多模型切换与热加载 → yolo-training-engineer + sqlalchemy-db-engineer

### P2 — 高级特性
1. 分布式训练
2. 多模型协同识别(投票)
3. 云端模型同步
4. PyInstaller 一键打包

---

## 8. 不变量违反时的处理

发现某个 agent 的提案/产出违反不变量时:

1. **stop**:暂停该任务
2. **report**:由 orchestrator 汇报给用户,说明违反哪条
3. **propose**:给出两个方案(改方案 vs 改不变量),让用户拍板
4. **never silently apply**:不擅自实施

---

## 9. 维护本文件

- 新增模块/agent → 同步更新 §2 角色映射
- 新增共享契约 → 加到 §3
- 新增不变量 → 加到 §4,同步加到 [SPEC.md §8](../SPEC.md#8-架构不变量不可违反)
- 路线图推进 → 更新 §7

修改本文件**应该**让 fisherman-orchestrator 审核,确保契约一致性。
