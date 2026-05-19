# 07 目录与文件结构

## 1. 代码目录

```
fisherman/
├── main.py                       程序入口
├── 启动_Fisherman.bat             Windows 启动器（依赖检测 + 启动）
├── pyproject.toml                项目元数据与依赖（uv 管理）
├── uv.lock                       依赖锁文件（uv 自动生成，纳入版本控制）
├── database_migration.py         数据库迁移脚本
├── diagnose_pytorch.py           PyTorch 环境诊断
├── diagnose_pytorch_advanced.py  高级诊断
├── simple_test.py                快速冒烟测试
├── test_modular_structure.py     模块结构测试
├── test_module_functionality.py  模块功能测试
├── test_training.py              训练模块测试
├── test_without_pytorch.py       无 PyTorch 场景测试
├── yolov8n.pt                    YOLOv8 nano 预训练权重
│
├── global_support/               全局支撑
│   ├── database.py
│   └── task_scheduler.py
│
├── gui/                          图形界面
│   ├── main_window.py
│   ├── annotation_window.py
│   ├── dataset_detail_dialog.py
│   ├── log_viewer_dialog.py
│   ├── tabs/                     主 Tab
│   │   ├── training_tab.py
│   │   ├── training_result_tab.py
│   │   ├── recognition_tab.py
│   │   ├── recognition_test_tab.py
│   │   ├── recognition_action_tab.py
│   │   └── settings_tab.py
│   └── detail_tabs/              详情对话框内嵌 Tab
│       ├── images_tab.py
│       ├── training_tab.py
│       └── training/             训练参数/控制/日志组件
│
├── recognition/                  识别模块
│   └── screen_recognition.py
│
├── training/                     训练模块
│   ├── training_manager.py       对外门面
│   ├── annotation_tool.py
│   ├── dataset_path_manager.py
│   ├── backup.py
│   ├── statistics.py
│   ├── validator.py
│   ├── core/
│   │   ├── base_manager.py
│   │   └── interfaces.py
│   ├── task/
│   │   ├── creator.py
│   │   ├── manager.py
│   │   ├── dataset_manager.py
│   │   └── status_tracker.py
│   ├── annotation/
│   │   ├── manager.py
│   │   ├── tool.py
│   │   ├── validator.py
│   │   ├── annotation_validator.py
│   │   ├── validation_strategies.py
│   │   ├── visualizer.py
│   │   ├── yolo_formatter.py
│   │   └── exporter.py
│   ├── training/
│   │   ├── executor.py
│   │   ├── yolo_trainer.py
│   │   ├── config_builder.py
│   │   ├── callback_handler.py
│   │   ├── training_callbacks.py
│   │   ├── log_manager.py
│   │   └── result_saver.py
│   └── utils/
│       └── file_ops.py
│
├── training_result/              训练结果管理
│   └── model_manager.py
│
├── sql/
│   └── create_tables.sql         建表 SQL
│
├── design/                       设计文档（本目录）
└── logs/                         运行期日志
```

## 2. 运行期数据目录

运行期由程序自动创建，不纳入版本控制（建议 `.gitignore`）。

```
training_data/                     训练数据根目录
└── {task_uuid}/
    ├── dataset/
    │   ├── images/                训练图片（由用户导入，复制方式）
    │   ├── labels/                YOLO 格式标注 (.txt)
    │   └── remark.txt             备注信息
    ├── annotations/               原始/中间标注数据
    └── models/                    （可选）任务内的模型

training_result/                   全局训练产物
└── {task_name_or_uuid}/
    ├── weights/
    │   ├── best.pt
    │   └── last.pt
    ├── results.png / results.csv  YOLO 训练曲线
    └── ...

models/                            外部导入或用户精选的模型
logs/
└── fisherman.log                  程序运行日志（UTF-8）

fisherman.db                       SQLite 数据库
```

## 3. 命名约定

| 场景 | 约定 |
|------|------|
| 训练集目录名 | 使用 `task_id`（UUID），避免名称冲突 |
| 数据库主键 | UUID v4 |
| 模型文件 | YOLO 默认 `best.pt` / `last.pt` |
| 日志文件 | `fisherman.log` + 按需滚动 |
| Python 模块 | 全小写 + 下划线 |
| Qt Widget 类 | 大驼峰，后缀与职责匹配（`XxxTab` / `XxxDialog` / `XxxWidget`） |

## 4. 配置与路径入口

- 路径集中管理：`training/dataset_path_manager.py::DatasetPathManager`
- 数据库 URI：`global_support/database.py`（SQLite 固定为项目根目录下 `fisherman.db`）
- 依赖：`pyproject.toml` + `uv.lock`（默认索引指向清华镜像，详见 08_tech_stack.md）

## 5. 版本控制建议

建议纳入版本控制：`*.py`、`sql/`、`design/`、`pyproject.toml`、`uv.lock`、`README.md`、`*.bat`、`yolov8n.pt`（可选，较大）
建议忽略：`logs/`、`training_data/`、`training_result/`、`models/`、`fisherman.db`、`__pycache__/`、`.venv/`
