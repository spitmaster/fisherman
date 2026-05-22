# Fisherman — 项目 SPEC(真相源)

> 本文件是 Fisherman 项目按 SDD 方法论维护的**唯一真相源**。所有需求与架构决策以本文为准。
> 代码注释、git log、README 都可能滞后,**冲突时以本 SPEC 为准**。
>
> 版本:v1.0(2026-05-19 由 olddocs 吸收 + 代码扫描产出)
> 维护人:Fisherman Team
> 上次同步:2026-05-19

---

## 0. 文档定位

- 信息来源:`olddocs/原始设计文档/` 全部 10 份 + 实际代码扫描 + `pyproject.toml`
- 吸收记录:[olddocs-摘要.md](./olddocs-摘要.md)
- 详细模块清单/运行期目录结构等长尾信息:`olddocs/原始设计文档/04_modules.md`、`07_directory_layout.md`(只读历史快照)

---

## 1. 项目概述

### 1.1 基本信息

| 项 | 内容 |
|----|------|
| 项目名称 | Fisherman |
| 当前版本 | 1.0.0 |
| 项目类型 | Windows 桌面应用 |
| 项目简介 | 基于 YOLOv8 的视觉自动化工具,提供「数据标注 → 模型训练 → 屏幕识别 → 自动点击」一站式闭环能力 |
| 目标用户 | 游戏辅助开发者、自动化办公人员、CV 初学者 |
| 项目背景 | 让用户无需编写代码即可通过图形界面训练识别模型并实时监控屏幕、识别目标、触发鼠标点击 |

### 1.2 核心价值

- **闭环完整**:数据 → 模型 → 实时推理全流程可视化
- **零代码**:用户全程 GUI 操作,不需要写 Python
- **模块化**:gui / training / recognition / training_result / global_support 解耦,易扩展
- **本地化**:全部 CPU 推理,无云端依赖

### 1.3 非目标(Non-Goals)

- ❌ 不做 Web / 云端推理服务
- ❌ 不做分布式训练(单机 CPU)
- ❌ 不提供从零开始的模型结构设计(基于 YOLOv8 预训练权重微调)
- ❌ 不做 macOS / Linux 正式支持(代码理论可跑,未正式测试)

---

## 2. 功能需求

按 GUI 主入口拆解。每个功能项标注当前完成度。

### 2.1 训练标签页(TrainingTab)— ✅ 已完成

**作为** 用户,**我希望** 通过列表管理我的训练集,**以便** 组织多个独立的识别任务。

**功能点**:
- F2.1.1 新建训练集(输入名称 + 备注 → 生成 UUID 训练集)
- F2.1.2 训练集列表(显示名称、备注、图片数、标注进度、状态、创建时间)
- F2.1.3 删除训练集(二次确认,同时删除数据库记录 + 磁盘目录)
- F2.1.4 双击打开训练集详情对话框

**验收标准**:
- [x] 训练集 UUID 与目录名一致(避免名称冲突)
- [x] 删除训练集后数据库与磁盘均无残留
- [x] 列表实时刷新

### 2.2 训练集详情 — 图片管理(ImagesTab)— ✅ 已完成

**功能点**:
- F2.2.1 导入图片(选文件/文件夹 → **复制**到 `dataset/images/`,不动原文件)
- F2.2.2 图片列表(显示文件名 + 已标注/未标注状态)
- F2.2.3 进入标注(打开 `AnnotationWindow` 逐张标注)
- F2.2.4 清空全部图片(同时清空 `labels/`)

### 2.3 训练集详情 — 训练(detail_tabs/training)— ✅ 已完成

**功能点**:
- F2.3.1 参数配置:epochs、batch_size、imgsz、模型类型(yolov8n/s/m)、lr、patience
- F2.3.2 训练控制:开始 / 暂停 / 停止
- F2.3.3 实时日志:epoch / loss / mAP 滚动显示
- F2.3.4 训练完成后权重自动归档到 `training_result/{task_name}/weights/best.pt`

**验收标准**:
- [x] 训练参数有合法性校验(epochs 1-1000、batch 1-128)
- [x] 训练过程不阻塞 UI 主线程
- [x] 训练异常不导致主程序崩溃

### 2.4 标注窗口(AnnotationWindow)— ✅ 已完成

**作为** 用户,**我希望** 用图形化方式给图片画框打标签,**以便** 不写代码就能产出 YOLO 训练数据。

**功能点**:
- F2.4.1 矩形框绘制(鼠标拖拽)
- F2.4.2 多类别标签
- F2.4.3 撤销 / 上一张 / 下一张
- F2.4.4 自动保存为 YOLO 格式 `.txt` 到 `dataset/labels/`
- F2.4.5 标注一致性校验(`AnnotationValidator`)

### 2.5 训练结果标签页(TrainingResultTab)— 🚧 75% 完成

**功能点**:
- F2.5.1 列出 `training_result/` 与 `models/` 的所有 `.pt` 模型
- F2.5.2 导入外部模型
- F2.5.3 删除模型(同步 `model_versions` 表)
- F2.5.4 设为默认(`is_default=1`,其它置 0)
- ⏳ F2.5.5 模型对比(mAP / loss 曲线对比)— **未实现**

### 2.6 识别测试标签页(RecognitionTestTab)— ✅ 已完成

**作为** 用户,**我希望** 在不触发点击的情况下验证模型识别效果,**以便** 调试模型/参数。

**功能点**:
- F2.6.1 选择模型 + 置信度阈值(10-95)
- F2.6.2 ROI 区域选择(可拖拽)或全屏监控
- F2.6.3 实时显示 BBox + 置信度 + 类别
- F2.6.4 FPS / 识别总数统计

### 2.7 识别操作标签页(RecognitionActionTab)— 🚧 65% 完成

继承 RecognitionTestTab 的能力,增加点击执行。

**功能点**:
- F2.7.1 点击冷却时间(避免连续触发)
- F2.7.2 点击动作类型
- F2.7.3 可选自定义 Python 脚本
- F2.7.4 受 TaskScheduler 调度,与训练任务串行

**进行中 / 待优化**:
- ⏳ 多目标识别策略(轮流/优先级)
- ⏳ 错误处理与重试
- ⏳ 自定义脚本沙箱

### 2.8 设置标签页(SettingsTab)— ✅ 已完成

- F2.8.1 显示运行环境(Python、PyTorch、CUDA 状态)
- F2.8.2 显示项目路径、数据库位置

### 2.9 日志查看器(LogViewerDialog)— ✅ 已完成

- F2.9.1 按任务 ID / 级别 / 时间过滤
- F2.9.2 读取 `training_logs`、`recognition_logs` 表 + `logs/fisherman.log`

### 2.10 任务调度(隐式能力)— ✅ 已完成

- F2.10.1 训练 + 识别任务统一走 `task_scheduler.submit()`
- F2.10.2 同一时刻至多一个重任务运行(`max_concurrent_tasks=1`)
- F2.10.3 用户无感知

---

## 3. 非功能需求

### 3.1 性能

| 项 | 要求 | 当前状态 |
|----|------|---------|
| 屏幕截图速度 | mss.grab(),≥ 30 FPS @ 全屏 1920x1080 | ✅ 满足 |
| YOLO 推理 | yolov8n CPU,≥ 5 FPS | ✅ 满足 |
| UI 响应 | 任何后台操作不阻塞主线程 > 100ms | ✅ 通过信号槽切回主线程 |
| 训练吞吐 | 由 PyTorch CPU 决定,不在本项目优化范围 | N/A |

### 3.2 并发与线程模型

- **GUI 主线程**:PyQt5 事件循环,唯一 QWidget 操作线程
- **调度线程**:`TaskScheduler._scheduler_loop`(daemon)
- **训练线程**:`TrainingExecutor` 在调度器中执行
- **识别线程**:`ScreenRecognition.thread`(daemon)帧循环
- **标注并发**:`AnnotationManager` 内部 `ThreadPoolExecutor`(批量任务)

**约束**:所有后台 → UI 的回调**必须通过 Qt 信号槽**切回主线程。

### 3.3 错误边界

- 数据库层:统一捕获 `SQLAlchemyError`,在 `db_manager` 记日志后抛业务异常
- 训练/识别线程:内部捕获异常 → 通过回调通知 GUI;后台线程崩溃**不影响主程序**
- PyTorch 缺失:程序仍能启动,训练/识别按钮禁用并提示

### 3.4 兼容性

| 项 | 要求 |
|----|------|
| OS | Windows 10/11 64 位(主)、Linux/macOS(未正式测试) |
| Python | ≥ 3.8 |
| 内存 | ≥ 4 GB |
| 磁盘 | ≥ 2 GB |
| 运行时 | Visual C++ Redistributable 2015-2022(PyTorch 要求) |

### 3.5 可用性

- 全程 GUI 操作,无需编辑配置文件
- `启动_Fisherman.bat` 一键启动(检测依赖 + 启动应用)
- 错误提示走 UI 弹窗,不强制查日志

---

## 4. UI 结构

### 4.1 主窗口(MainWindow)

```
MainWindow (~160 行,仅做布局 + Tab 挂载)
├── 顶部菜单
├── QTabWidget
│   ├── TrainingTab           — 训练集管理
│   ├── TrainingResultTab     — 模型版本管理
│   ├── RecognitionTestTab    — 识别测试(不触发点击)
│   ├── RecognitionActionTab  — 识别操作(触发点击)
│   └── SettingsTab           — 环境信息
└── 底部状态栏 + "运行日志"按钮 → LogViewerDialog
```

### 4.2 对话框

- `DatasetDetailDialog`:容器,内嵌 `ImagesTab` + `detail_tabs/training/`
- `AnnotationWindow`:Qt 图形化标注器
- `LogViewerDialog`:日志查看
- `ScreenAreaSelector`:屏幕区域选择器(用于 ROI 配置)

### 4.3 已废弃但保留的组件

- `gui/tabs/recognition_tab.py`(旧版识别页,已被测试/操作两个 Tab 替代,**保留作参考**)

---

## 5. 技术架构

### 5.1 技术栈

| 类别 | 选型 | 版本 |
|------|------|------|
| 语言 | Python | ≥ 3.8 |
| 包管理 | uv | 最新(astral) |
| GUI | PyQt5 | ≥ 5.15.0(Windows 锁 PyQt5-Qt5 ==5.15.2) |
| 深度学习 | PyTorch | ==2.3.0(CPU 版,便于打包) |
| | torchvision | ==0.18.0 |
| 目标检测 | Ultralytics YOLO | ≥ 8.0.0 |
| 图像处理 | OpenCV(headless) | ≥ 4.8.0(避开 Qt 冲突) |
| | Pillow | ≥ 10.0.0 |
| 屏幕截图 | mss | ≥ 9.0.0 |
| 自动化 | pyautogui | ≥ 0.9.50 |
| 数据库 | SQLAlchemy + SQLite | ≥ 2.0.0 |
| 数值 | numpy | < 2(YOLO 生态限制) |
| | pandas | ≥ 2.0.0 |
| | scipy | ≥ 1.10.0 |
| 系统信息 | psutil | ≥ 6.0.0 |
| 包索引 | 清华镜像 | https://pypi.tuna.tsinghua.edu.cn/simple |

### 5.2 分层架构

```
┌─────────────────────────────────────────────────────┐
│ 表示层 (Presentation)  gui/                          │
│   PyQt5 主窗口 + Tabs + Dialogs                      │
└─────────────────────────────────────────────────────┘
                       │ 信号 / 方法调用
                       ▼
┌─────────────────────────────────────────────────────┐
│ 业务层 (Business)                                    │
│   training/    训练管道(任务/数据集/标注/执行)        │
│   recognition/ 屏幕识别(截图/推理/点击)              │
│   training_result/  模型版本管理                     │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 支撑层 (Infrastructure)                              │
│   global_support/  数据库 / 任务调度 / 日志           │
│   sql/  建表 SQL                                     │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 存储层 (Storage)                                     │
│   SQLite (fisherman.db) | training_data/ | training_result/ │
│   models/ | logs/                                    │
└─────────────────────────────────────────────────────┘
```

### 5.3 模块清单(对外门面)

| 顶层包 | 职责 | 对外门面 |
|--------|------|----------|
| `gui/` | 主窗口 + Tabs + Dialogs | `gui.main_window.MainWindow` |
| `training/` | 训练生命周期管理 | `training.training_manager.TrainingManager` |
| `recognition/` | 屏幕监控与 YOLO 推理 | `recognition.screen_recognition.recognition_manager` |
| `training_result/` | 训练产物与模型版本 | `training_result.model_manager.ModelManager` |
| `global_support/` | 数据库 / 任务调度 | `global_support.database.db_manager` + `global_support.task_scheduler.task_scheduler` |

### 5.4 关键设计模式

| 模式 | 体现位置 |
|------|----------|
| Facade | `training_manager.TrainingManager`(聚合 task/annotation/training) |
| Singleton | `db_manager`、`task_scheduler`、`recognition_manager` |
| Strategy | `training/annotation/validation_strategies.py`(标注校验) |
| Template Method | `training/core/base_manager.py`(管理器基类) |
| Observer/Callback | YOLO 训练回调、识别 `on_recognition_result` |
| Factory | `task.creator.TaskCreator` |

### 5.5 数据模型

**SQLite 数据库**:`fisherman.db`(项目根)。全部主键为 UUID v4(`String(36)`)。

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `training_tasks` | 训练任务/数据集 | id, task_name, status, dataset_path, epochs, batch_size, mAP, loss |
| `training_logs` | 训练日志 | id, training_task_id (FK), log_level, log_message, log_time |
| `recognition_tasks` | 识别任务 | id, training_task_id (FK), status, confidence_threshold, click_cooldown |
| `recognition_logs` | 识别日志 | id, recognition_task_id (FK), log_level, log_message |
| `recognition_details` | 识别详情 | id, recognition_task_id (FK), timestamp, target_x/y, confidence, target_class |
| `model_versions` | 模型版本 | id, training_task_id (FK), model_path, version, is_default, file_size |

**关系图**:
```
TrainingTask (1) ──< (N) TrainingLog
TrainingTask (1) ──< (N) ModelVersion
TrainingTask (1) ──< (N) RecognitionTask
RecognitionTask (1) ──< (N) RecognitionLog
RecognitionTask (1) ──< (N) RecognitionDetail
```

**索引**:见 `sql/create_tables.sql`(单一权威),关键索引 `idx_training_task_status`、`idx_recognition_log_task`、`idx_model_version_default`。

**一致性约束**:
- 外键由 SQLAlchemy 关系维护,**当前无 `ON DELETE CASCADE`**,业务层级联清理
- `ModelVersion.is_default` 至多一条为 1,由 `ModelManager.set_default()` 同事务切换
- 状态字段为字符串枚举,由 `StatusTracker` 保证合法性

### 5.6 关键目录结构

```
fisherman/
├── main.py                       入口
├── 启动_Fisherman.bat             Windows 启动器
├── pyproject.toml + uv.lock      依赖管理
├── fisherman.db                  SQLite(运行期产生)
├── yolov8n.pt                    YOLOv8 预训练权重
│
├── global_support/               全局支撑
├── gui/                          PyQt5 GUI
│   ├── tabs/                     主 Tab 集合
│   ├── detail_tabs/              Dialog 内嵌 Tab
│   └── *.py                      标注窗口/日志窗口/区域选择器
├── recognition/                  屏幕识别
├── training/                     训练管道
│   ├── task/ annotation/ training/  3 个子包
│   └── core/ utils/
├── training_result/              模型管理
├── sql/create_tables.sql         建表 SQL(单一权威)
│
└── 运行期目录(.gitignore)
    ├── training_data/{uuid}/dataset/{images,labels}
    ├── training_result/{name}/weights/best.pt
    ├── models/
    └── logs/fisherman.log
```

---

## 6. 当前状态与验收标准

### 6.1 模块完成度

| 模块 | 完成度 | 状态 |
|------|--------|------|
| global_support | ~92% | ✅ |
| gui | ~90% | ✅ |
| training | ~88% | ✅ |
| main.py | ~95% | ✅ |
| training_result | ~75% | 🚧 |
| recognition | ~65% | 🚧 |

### 6.2 已知技术债

- 旧版 `gui/tabs/recognition_tab.py` 与新版并存,未清理
- 数据库无 `ON DELETE CASCADE`,删训练任务时业务层手动级联
- 训练/识别线程内有散落的 `print` 调试输出(应该走 logging)
- YOLO `runs/` 缓存目录与 `training_result/` 同步逻辑不明确

### 6.3 测试覆盖

| 测试脚本 | 用途 |
|---------|------|
| `simple_test.py` | 快速冒烟 |
| `test_modular_structure.py` | 模块结构校验 |
| `diagnose_pytorch.py` / `diagnose_pytorch_advanced.py` | PyTorch 环境诊断 |

**当前无 pytest 测试套件**,后续 P1 应建立。

### 6.4 健康检查清单

```bash
# 1. 依赖同步
uv sync

# 2. PyTorch 可用性
uv run python diagnose_pytorch.py

# 3. 启动应用
uv run python main.py
# 或双击 启动_Fisherman.bat
```

---

## 7. 关键流程

### 7.1 训练流程(端到端)

```
新建训练集 → 创建 UUID 目录 + 入库
       ↓
导入图片 → 复制到 dataset/images/
       ↓
图形化标注 → 保存 YOLO .txt 到 dataset/labels/
       ↓
校验标注 → AnnotationValidator
       ↓
配置参数 → epochs/batch/imgsz/model_type
       ↓
TaskScheduler.submit → TrainingExecutor.train_by_name
       ↓
YOLOTrainer → ultralytics.YOLO.train()
       ↓
CallbackHandler → epoch/loss/mAP 回写 GUI + DB
       ↓
训练结束 → ResultSaver 复制权重 → model_versions 插入
       ↓
状态变 completed
```

### 7.2 识别流程

```
选择模型 + 区域 + 阈值 → RecognitionActionTab
       ↓
recognition_manager.start_recognition_task(cfg)
       ↓
ScreenRecognition 起后台线程
       ↓
帧循环:
  mss 截屏 → cv2.cvtColor → YOLO.predict
    → 过滤置信度 → 触发回调
    → 若冷却 OK:pyautogui.click + 写 recognition_details
       ↓
用户停止 → 线程 join → 状态归位
```

### 7.3 任务调度

- 优先级队列 + `threading.Condition` + `RLock`
- `max_concurrent_tasks = 1`(默认)
- 防止训练与识别同时抢 CPU

### 7.4 应用启动

```
启动_Fisherman.bat → uv sync → uv run python main.py
  ↓
main.py:
  - 尝试 import torch(失败仅警告)
  - setup_logging()
  - QApplication + MainWindow
       ↓
MainWindow.init_application():
  - db_manager.connect() + create_tables()
  - task_scheduler.start_scheduler()
  - 构建 Tabs
       ↓
进入 Qt 事件循环
```

### 7.5 应用关闭

```
MainWindow.closeEvent:
  - 逐 Tab.close() 停止内部线程
  - recognition_manager.stop_recognition_task()
  - task_scheduler.stop_scheduler()
  - 等线程 join → exit
```

---

## 8. 架构不变量(不可违反)

> 修改代码前必须检查,可能违反时**先与用户确认**:

1. **【MUST】单一真相源**:任何业务规则改动先改本 SPEC,再改代码
2. **【MUST】UI 线程安全**:跨线程更新 QWidget 必须通过 Qt 信号槽,禁止直接调用
3. **【MUST】重资源串行**:训练/识别任务必须经 `task_scheduler.submit()`,不绕过调度器
4. **【MUST】UUID 主键**:所有数据库主键 + 训练集目录名一律 UUID v4,禁止用名称
5. **【MUST】依赖锁定**:`uv.lock` 必须纳入版本控制,保证团队构建一致
6. **【MUST】设备选择显式化**:训练/推理使用的硬件设备必须由用户在任务发起时显式选择;系统**不自动降级**,设备不可用时报错提示用户;设备枚举走 `global_support/device_resolver.get_available_devices()`
7. **【SHOULD】logging 优先**:新代码禁止 `print`,统一走 logging 体系

---

## 9. 附录

### 9.1 术语表

| 术语 | 定义 |
|------|------|
| 训练集 | TrainingTask 的别名,GUI 中的展示名,对应 1 个 UUID 目录 + 1 行数据库记录 |
| 数据集 | 训练集内部的 `dataset/` 子目录,包含 images/ + labels/ |
| 模型版本 | 一次训练产出的 .pt 权重文件,对应 `model_versions` 表一行 |
| 默认模型 | 识别模块默认加载的模型,`model_versions.is_default=1` |
| 重任务 | 占用大量 CPU/GPU 的任务(训练/识别),受 TaskScheduler 串行化 |
| ROI | Region of Interest,用户指定的屏幕监控子区域 |

### 9.2 参考资料

- 原始设计文档(只读历史快照):[olddocs/原始设计文档/](../olddocs/原始设计文档/)
- 吸收摘要:[docs/olddocs-摘要.md](./olddocs-摘要.md)
- YOLOv8 文档:https://docs.ultralytics.com
- PyQt5 文档:https://www.riverbankcomputing.com/static/Docs/PyQt5/
- uv 文档:https://docs.astral.sh/uv/

### 9.3 变更日志

| 日期 | 版本 | 改动 |
|------|------|------|
| 2026-05-19 | v1.0 | 初版。由 olddocs/原始设计文档/ 10 份文档 + 实际代码扫描合并产出 |
