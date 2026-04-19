# 03 功能设计

按界面入口拆解功能点，每项功能包括：入口、输入、处理、输出、关键控件。

## 1. 训练标签页（TrainingTab）

### 1.1 新建训练集
- **入口**：点击"新建训练集"按钮
- **输入**：训练集名称（必填）、备注（可选）
- **处理**：`TrainingManager.create_task()` → 生成 UUID，落库 `training_tasks`，创建 `training_data/{uuid}/dataset/{images,labels}` 目录
- **输出**：列表中新增一行记录

### 1.2 训练集列表
- **字段**：名称、备注、总图片数、已标注数、标注进度、创建时间、状态
- **操作**：双击打开 `DatasetDetailDialog`；右键/按钮删除

### 1.3 删除训练集
- **二次确认** → 同时删除数据库记录和 `training_data/{uuid}/` 目录

## 2. 训练集详情对话框（DatasetDetailDialog）

内嵌 2 个子 Tab：**图片管理** 与 **训练**。

### 2.1 图片管理（ImagesTab）
- 导入图片：选择文件/文件夹 → 复制到 `dataset/images/`，原文件不动
- 图片列表：展示文件名、是否已标注
- 开始标注：打开 `AnnotationWindow`，进入逐张标注模式
- 清空所有图片：删除 `images/` 与对应 `labels/`

### 2.2 训练（detail_tabs/training）
- **TrainingParamsWidget**：配置 epochs、batch_size、imgsz、模型类型（yolov8n/s/m）、lr、patience 等
- **TrainingControlPanel**：开始 / 暂停 / 停止按钮
- **TrainingLogWidget**：实时滚动训练日志（epoch、loss、mAP）

## 3. 标注窗口（AnnotationWindow）

- 显示当前图片 + 可拖拽绘制的矩形框
- 支持多类别标签、撤销、跳转上一张/下一张
- 保存时生成 YOLO 格式 `.txt` 至 `dataset/labels/`
- 标注数据经 `training/annotation/validator.py` 校验合规性

## 4. 训练结果标签页（TrainingResultTab）

- 展示所有已训练模型（`training_result/` 下的 `.pt` 文件）
- 操作：导入外部模型、删除、打开目录、设为默认
- 规划：模型对比（mAP、Loss 曲线对比）

## 5. 识别测试标签页（RecognitionTestTab）

用于验证模型识别效果，不触发点击。

- **输入**：选择模型、置信度阈值（Slider 10-95）、ROI 区域（可拖拽）或全屏
- **实时显示**：检测到的目标位置、置信度、类别、BBox
- **统计**：FPS、识别总数

## 6. 识别操作标签页（RecognitionActionTab）

在识别基础上触发操作。

- 继承 RecognitionTestTab 的基础配置
- 增加：点击冷却时间、点击动作类型、可选自定义 Python 脚本
- 启动后进入后台循环，每识别到一次目标即触发鼠标点击（受冷却时间限制）

## 7. 设置标签页（SettingsTab）

- 展示运行环境信息：Python、PyTorch、CUDA 状态、设备
- 展示项目路径、数据库位置

## 8. 日志查看器（LogViewerDialog）

- 入口：主窗口底部"运行日志"按钮
- 支持按任务 ID / 级别 / 时间过滤
- 读取 `training_logs`、`recognition_logs` 两张表与 `logs/fisherman.log`

## 9. 任务调度（隐式能力）

- 所有训练、识别任务在提交时均走 `task_scheduler.submit(task)`
- 调度器保证同一时刻只运行一个重资源任务（默认 `max_concurrent_tasks=1`）
- 用户无感知，但保证不出现 GPU/CPU 争抢

## 10. 数据持久化

- 所有业务数据进 SQLite（`fisherman.db`）
- 大文件（图片、标注、模型）使用文件系统 + UUID 目录组织
- 详见 [05_database.md](05_database.md) 与 [07_directory_layout.md](07_directory_layout.md)

## 11. 未实现 / 规划中功能

- 模型对比曲线图（mAP / loss）
- 多目标协同识别
- 训练早停机制的参数化配置
- 分布式 / GPU 训练支持
- 云端模型同步
