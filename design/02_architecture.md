# 02 系统架构

## 1. 分层结构

```
┌──────────────────────────────────────────────────────────┐
│  表示层 (Presentation)                                   │
│  gui/  — PyQt5 主窗口 + Tabs + Dialogs                   │
└──────────────────────────────────────────────────────────┘
                          │  信号 / 方法调用
                          ▼
┌──────────────────────────────────────────────────────────┐
│  业务层 (Business)                                       │
│  training/    训练管道：任务/数据集/标注/执行             │
│  recognition/ 屏幕识别：截图/推理/点击                    │
│  training_result/ 模型版本管理                           │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  支撑层 (Infrastructure)                                 │
│  global_support/  数据库连接 / 任务调度器 / 日志          │
│  sql/             建表语句                                │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  存储层 (Storage)                                        │
│  SQLite (fisherman.db) | training_data/ | training_result/│
│  models/ | logs/                                          │
└──────────────────────────────────────────────────────────┘
```

## 2. 模块划分与职责

| 顶层包 | 职责 | 对外门面 |
|--------|------|----------|
| `gui/` | 提供主窗口与所有对话框、Tab | `gui.main_window.MainWindow` |
| `training/` | 训练生命周期管理 | `training.training_manager.TrainingManager` |
| `recognition/` | 屏幕监控与 YOLO 推理 | `recognition.screen_recognition.recognition_manager` |
| `training_result/` | 训练产物与模型版本管理 | `training_result.model_manager.ModelManager` |
| `global_support/` | 数据库、任务调度等横切能力 | `global_support.database.db_manager` / `task_scheduler` |

## 3. 训练模块内部分层

```
training/
├── core/            抽象接口与基类（BaseManager, Interfaces）
├── task/            训练任务生命周期（创建/查询/状态追踪/数据集管理）
├── annotation/      标注管理（管理器/工具/验证/可视化/YOLO 格式转换）
├── training/        训练执行（执行器/配置构建/回调/日志/结果保存/YOLO 封装）
├── utils/           文件操作等工具
├── training_manager.py  对外门面
├── dataset_path_manager.py  统一路径管理
├── backup.py / statistics.py / validator.py  支撑功能
```

此分层遵循 **Facade + 分包子职责** 的模式：

- `training_manager.TrainingManager`：门面，协调 task / annotation / training 三个子包
- `training/task`：纯粹的元数据与数据集状态管理
- `training/annotation`：围绕标注的策略化子系统（含验证策略、格式转换）
- `training/training`：真正触发 YOLO 训练的重资源子系统

## 4. GUI 层结构

```
gui/
├── main_window.py           主窗口（仅 ~160 行，只做布局 + Tab 挂载）
├── tabs/                    主 Tab 集合（高内聚低耦合）
│   ├── training_tab.py
│   ├── training_result_tab.py
│   ├── recognition_tab.py          旧版识别页（保留未挂载）
│   ├── recognition_test_tab.py     识别测试
│   ├── recognition_action_tab.py   识别操作
│   └── settings_tab.py
├── detail_tabs/             DatasetDetailDialog 内嵌 Tab
│   ├── images_tab.py                图片管理
│   └── training/                    训练参数与控制
├── annotation_window.py     Qt 图形化标注器
├── dataset_detail_dialog.py 训练集详情对话框
└── log_viewer_dialog.py     日志查看器
```

重构后主窗口只负责窗口容器与 Tab 组织；每个 Tab 独立管理自身状态与后端调用，降低耦合。

## 5. 交互关系（核心数据流）

### 5.1 创建训练任务
`TrainingTab` → `TrainingManager.create_task()` → `task.creator.TaskCreator` + `DatasetPathManager` → 写入 `TrainingTask` 表并创建 `training_data/{uuid}/` 目录。

### 5.2 启动训练
`DatasetDetailDialog (TrainingTab)` → `TrainingExecutor.train_by_name()` → `YOLOTrainer` → `ultralytics.YOLO.train()` → 回调 `CallbackHandler` → GUI 日志。

### 5.3 启动识别
`RecognitionActionTab` → `recognition_manager.start_recognition_task(cfg)` → `ScreenRecognition._recognition_loop`（后台线程）→ 截屏 → 推理 → 可选点击。

### 5.4 跨模块调度
涉及重资源的启动一律先经 `task_scheduler.submit()`，由调度器保证同一时刻至多一个"重任务"运行，避免训练与识别互相争抢 CPU。

## 6. 关键设计模式

| 模式 | 体现位置 |
|------|----------|
| Facade | `training.training_manager.TrainingManager` 聚合子模块 |
| Singleton | `global_support.database.db_manager`、`task_scheduler`、`recognition_manager` |
| Strategy | `training/annotation/validation_strategies.py` 标注校验 |
| Template Method | `training/core/base_manager.py` 定义通用流程骨架 |
| Observer / Callback | 训练回调 (`training_callbacks.py`, `callback_handler.py`)、识别回调 (`on_recognition_result`) |
| Factory | `task.creator.TaskCreator` 创建训练任务 |

## 7. 线程与并发模型

- **GUI 主线程**：PyQt5 事件循环
- **任务调度线程**：`TaskScheduler._scheduler_loop`（后台守护线程）
- **训练线程**：`TrainingExecutor` 在调度器中以子进程/线程方式执行 YOLO 训练
- **识别线程**：`ScreenRecognition.thread`（守护线程），帧循环中每帧截图、推理、点击
- **标注并发**：`AnnotationManager` 内部使用 `ThreadPoolExecutor` 处理批量标注

所有与 UI 交互的回调通过信号槽切回主线程，避免跨线程操作 QWidget。

## 8. 错误边界

- 数据库层统一捕获 `SQLAlchemyError`，在 `db_manager` 中记日志并抛出业务异常
- 训练/识别线程内部捕获异常后通过回调通知 GUI，不让后台线程崩溃影响主程序
- PyTorch 导入失败不会阻止程序启动，仅禁用相关功能（见 `main.py` 启动检查）
