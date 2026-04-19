# 04 模块设计

本文档列出各包的职责、关键文件、核心类与对外方法。

## 1. global_support — 全局支撑

### 1.1 database.py
- **ORM 模型**：`TrainingTask`、`TrainingLog`、`RecognitionTask`、`RecognitionLog`、`RecognitionDetail`、`ModelVersion`
- **DatabaseManager**（单例 `db_manager`）
  - `connect()`：创建 SQLite 引擎，连接 `fisherman.db`
  - `create_tables()`：依据 ORM 元数据建表
  - `get_session()`：返回 `sessionmaker` 会话（调用方负责关闭）
- **主键策略**：`default=lambda: str(uuid.uuid4())`
- **时间戳**：`created_at=datetime.now`、`updated_at` 带 `onupdate`

### 1.2 task_scheduler.py
- **Task**：`task_id / task_type(TRAINING|RECOGNITION) / status(PENDING|RUNNING|COMPLETED|FAILED) / priority`
- **TaskScheduler**（单例 `task_scheduler`）
  - `start_scheduler()` / `stop_scheduler()`
  - `submit(task)`：入队
  - `_scheduler_loop()`：后台线程，从优先级队列取任务，在 `running < max_concurrent_tasks` 时执行
  - 使用 `threading.Condition` + `RLock` 做冲突互斥

## 2. training — 训练模块

### 2.1 training_manager.py （门面）
- `TrainingManager`：整合 task、annotation、training 三个子包，为 GUI 提供一致入口
- 典型方法：创建任务、启动训练、获取状态、获取进度

### 2.2 dataset_path_manager.py
- `DatasetPathManager`：集中管理训练集与训练结果的目录结构，保证 `training_data/{uuid}/dataset/{images,labels}` 的一致性
- 常用方法：`get_images_dir(task_id)`、`get_labels_dir(task_id)`、`get_result_dir(task_id)`

### 2.3 core/
- `base_manager.py::BaseManager`：所有管理器基类，提供通用的日志、异常、回调钩子
- `interfaces.py`：定义训练过程中的数据结构、接口契约

### 2.4 task/
- `creator.TaskCreator`：新建训练任务，校验任务名/参数
- `manager.TaskManager`：任务的查询、更新、删除
- `dataset_manager.DatasetManager`：图片的导入（复制）、列表、删除
- `status_tracker.StatusTracker`：任务状态机（pending → annotating → training → completed/failed）

### 2.5 annotation/
- `manager.AnnotationManager`：标注任务调度与进度；内部 `ThreadPoolExecutor`
- `tool.AnnotationTool`：标注器的核心逻辑（供 GUI 调用）
- `validator.Validator` + `validation_strategies.py`：以 Strategy 模式组合多种校验规则
- `annotation_validator.py`：顶层业务校验（数据集完整性）
- `visualizer.py`：标注结果可视化（绘 BBox）
- `yolo_formatter.py`：将内部标注结构转换为 YOLO `.txt`
- `exporter.py`：导出标注数据包

### 2.6 training/
- `executor.TrainingExecutor`：训练入口，按任务名加载并执行
- `config_builder.py`：组装 `data.yaml`、训练超参
- `yolo_trainer.YOLOTrainer`：封装 ultralytics `YOLO.train()` 调用
- `callback_handler.py` + `training_callbacks.py`：注册到 YOLO 的回调（epoch 开始/结束、训练结束）
- `log_manager.py`：把 YOLO 输出写入数据库与日志文件
- `result_saver.ResultSaver`：训练完成后把权重复制到 `training_result/`

### 2.7 utils/
- `file_ops.py`：复制/移动文件、安全删除、路径规范化

### 2.8 backup.py / statistics.py / validator.py
- `backup.py`：训练任务与标注数据的备份/恢复
- `statistics.py`：计算任务统计（图片数、标注进度、mAP/loss）
- `validator.py`（顶层）：训练参数与数据集合法性验证（epochs 1-1000、batch 1-128 等）

### 2.9 annotation_tool.py
- 标注能力的顶层入口，供命令行或外部调用

## 3. recognition — 识别模块

### 3.1 screen_recognition.py
- **ScreenRecognition**
  - 构造：`model_path, confidence_threshold=0.7, click_cooldown=5`
  - 核心方法：
    - `set_monitor_area(x,y,w,h)` / `use_full_screen_monitor()`
    - `start_recognition()` / `pause_recognition()` / `resume_recognition()` / `stop_recognition()`
    - `_recognition_loop()`：帧循环
    - `_capture_screen()`：`mss.grab()` + `cv2.cvtColor`
    - `_detect_objects(image)`：YOLO 推理，过滤置信度
    - `_handle_detection_results(detections)`：触发回调 + 冷却判断
    - `_click_target(pos)`：`pyautogui.click()`
  - 回调：`on_recognition_result / on_click_event / on_error`
  - 统计：`recognitions_count / clicks_count / fps`
- **recognition_manager**（全局单例）：包装 `ScreenRecognition`，提供任务级 API（`start_recognition_task`、`stop_recognition_task`、`is_recognition_active`）

## 4. training_result — 模型管理

### 4.1 model_manager.py
- `ModelManager`
  - 列出可用模型（扫描 `training_result/` 与 `models/`）
  - 导入外部模型
  - 删除模型（同步 `model_versions` 表）
  - 设为默认模型（`is_default=1`，其它置 0）
  - 规划：模型对比（对比两个版本的 mAP/loss 指标）

## 5. gui — 图形界面

### 5.1 main_window.py
- `MainWindow`：挂载主 Tab，初始化 `db_manager`、`task_scheduler`
- 顶部菜单、底部状态栏、日志按钮
- `update_recognition_stats()`：每秒定时刷新识别 Tab 的统计

### 5.2 tabs/
- `training_tab.TrainingTab`
- `training_result_tab.TrainingResultTab`
- `recognition_test_tab.RecognitionTestTab`
- `recognition_action_tab.RecognitionActionTab`
- `settings_tab.SettingsTab`
- `recognition_tab.RecognitionTab`（旧版，已不在主窗口挂载，保留作参考）

### 5.3 detail_tabs/
- `images_tab.ImagesTab`：图片导入 / 列表 / 标注入口
- `training/`：训练参数、控制面板、日志组件

### 5.4 对话框
- `dataset_detail_dialog.DatasetDetailDialog`：训练集详情容器
- `annotation_window.AnnotationWindow`：标注器
- `log_viewer_dialog.LogViewerDialog`：日志查看器

## 6. 入口与脚本

- `main.py`：程序主入口（PyTorch 检查 → 日志配置 → `MainWindow`）
- `database_migration.py`：数据库迁移
- `diagnose_pytorch.py` / `diagnose_pytorch_advanced.py`：PyTorch 环境诊断
- `test_*.py`：模块化结构与功能测试
- `启动_Fisherman.bat`：Windows 一键启动器（含依赖检测）
