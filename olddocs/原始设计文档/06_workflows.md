# 06 业务流程

## 1. 训练流程（端到端）

```
用户  GUI/TrainingTab  TrainingManager  DatasetPathManager  DatasetManager  AnnotationTool  TrainingExecutor  YOLOTrainer  DB
 │        │                 │                 │                  │              │                │              │         │
 │ 新建训练集                │                 │                  │              │                │              │         │
 ├───────►│ create_task     │                 │                  │              │                │              │         │
 │        ├────────────────►│ create_task()   │                  │              │                │              │         │
 │        │                 ├────────────────►│ make_dirs(uuid)  │              │                │              │         │
 │        │                 │                 │<─────────────────┤              │                │              │         │
 │        │                 ├──── insert ─────┼──────────────────┼──────────────┼────────────────┼──────────────┼────────►│
 │ 导入图片                  │                 │                  │              │                │              │         │
 ├───────►│ add_images      ├────────────────────────────────────►│ copy_images  │                │              │         │
 │ 打开详情 → 标注           │                 │                  │              │                │              │         │
 ├───────►│                 ├─────────────────────────────────────────────────►│ annotate (Qt)  │              │         │
 │        │                 │                                                 │ save YOLO .txt │              │         │
 │ 配置参数 → 开始训练       │                 │                  │              │                │              │         │
 ├───────►│ start_training  ├────────────────────────────────────────────────────────────────►│ train_by_name │         │
 │        │                 │                                                                  ├─────────────►│ train() │
 │        │ ◄── callbacks ─ epoch/loss/mAP 日志 ─────────────────────────────────────────────┤              │         │
 │        │                 │                                                                  │ ResultSaver ──────────►│ model_versions INSERT
 │ 查看结果 (TrainingResultTab) ← ModelManager.list_models()
```

### 步骤详解

1. **新建训练集**：`TrainingTab` → `TrainingManager.create_task(name, description)`；写库并创建 `training_data/{uuid}/dataset/{images,labels,annotations}` 目录。
2. **导入图片**：`ImagesTab` → `DatasetManager.add_images(task_id, src_paths)`，执行复制，不移动原文件。
3. **图像标注**：`ImagesTab → AnnotationWindow`（Qt 绘图）→ 保存 YOLO `.txt` 至 `labels/`；`AnnotationValidator` 做一致性检查。
4. **配置训练参数**：`detail_tabs/training/TrainingParamsWidget` 收集 epochs / batch_size / imgsz / model_type。
5. **启动训练**：
   - `TrainingControlPanel.on_start()` → `TrainingExecutor.train_by_name(task_name, params)`
   - `config_builder` 生成 `data.yaml`；`YOLOTrainer` 调用 `ultralytics.YOLO(model).train(...)`
   - `CallbackHandler` 注册到 YOLO，逐 epoch 将进度推送到 GUI 日志组件
   - `LogManager` 同步写库（`training_logs`）与文件
6. **保存结果**：训练完成由 `ResultSaver` 复制权重到 `training_result/{task_name}/` 并写 `model_versions` 表；`TrainingTask.status` 更新为 `completed`。

## 2. 识别流程

```
用户  GUI/RecognitionActionTab  recognition_manager  ScreenRecognition  mss  YOLO  pyautogui  DB
 │          │                        │                     │              │     │       │        │
 │ 选择模型/区域/阈值                 │                     │              │     │       │        │
 │ 点击"开始"                        │                     │              │     │       │        │
 ├─────────►│ start_recognition_task │                     │              │     │       │        │
 │          ├───────────────────────►│ init ScreenRecognition              │     │       │        │
 │          │                        ├────────────────────►│ start_thread │     │       │        │
 │                                   │                     │ while running:
 │                                   │                     │  capture ──►│     │       │        │
 │                                   │                     │  detect ───────────►│       │        │
 │                                   │                     │ ◄── detections ─────┤       │        │
 │                                   │                     │  if cooldown OK:
 │                                   │                     │  click ─────────────────────►│       │
 │                                   │                     │  write detail ──────────────────────►│
 │ 点击"停止"                        │                     │              │     │       │        │
 ├─────────►│ stop_recognition_task ─►│ stop_recognition ─►│ join thread │     │       │        │
```

### 关键点

- **线程模型**：识别运行在守护线程中，GUI 不阻塞
- **冷却控制**：`last_click_time` 与 `click_cooldown` 保证不会连续触发点击
- **区域监控**：`mss.grab` 支持全屏或 ROI 坐标
- **统计刷新**：`MainWindow.update_recognition_stats()` 每秒读取 `ScreenRecognition.recognitions_count/clicks_count/fps` 更新 UI
- **详细记录**：每次识别结果可选写入 `recognition_details` 表

## 3. 任务调度时序

```
调用方            TaskScheduler          Worker/线程
   │                 │                        │
   │ submit(task) ──►│ 入优先级队列            │
   │                 │                        │
   │                 │ _scheduler_loop         │
   │                 │ while running:          │
   │                 │   if len(running)<max: │
   │                 │     task = queue.pop()  │
   │                 │     status=RUNNING      │
   │                 │     _execute_task ────►│ run (训练/识别)
   │                 │                        │ ...
   │                 │ ◄── done / failed ─────┤
   │                 │   status=COMPLETED      │
```

- 默认 `max_concurrent_tasks = 1`：同一时刻仅一个重任务执行
- 通过 `threading.Condition` 通知调度循环推进
- `task_locks` 与 `global_lock` 防止并发修改状态

## 4. 应用启动流程

1. `启动_Fisherman.bat` 检测 Python → 安装依赖 → 启动 `python main.py`
2. `main.py`：
   1. 尝试 `import torch`（失败不阻塞，仅记警告）
   2. `setup_logging()` → `logs/fisherman.log`
   3. `QApplication` → `MainWindow()`
3. `MainWindow.init_application()`：
   1. `db_manager.connect()` + `create_tables()`
   2. `task_scheduler.start_scheduler()`
4. 构建 Tab → 进入事件循环

## 5. 关闭流程

- `MainWindow.closeEvent`：
  1. 逐个 Tab 的 `close()` 停止内部线程
  2. `recognition_manager.stop_recognition_task()`（若在跑）
  3. `task_scheduler.stop_scheduler()`
  4. 等线程 join 后退出

## 6. 错误与恢复

- **PyTorch 缺失**：降级运行，训练/识别按钮禁用并提示
- **YOLO 模型加载失败**：`ScreenRecognition` 置 `model=None`，UI 给出错误回调
- **训练异常**：`CallbackHandler` 捕获 → 更新任务状态为 `failed` → 写日志 → 通知 GUI
- **标注数据不合规**：`AnnotationValidator` 阻止进入训练步骤并提示用户
