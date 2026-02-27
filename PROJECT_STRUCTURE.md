# Fisherman 项目代码结构和功能作用

## 项目概述

Fisherman 是一个基于计算机视觉的自动化程序，主要用于识别和操作屏幕上的特定物体。项目采用模块化设计，主要分为训练模块、识别模块和图形界面模块。

## 项目根目录结构

```
d:\workspace\wow\fisherman\
├── global_support/            # 全局支撑模块
├── gui/                       # 图形界面模块
├── recognition/               # 识别模块
├── training/                  # 训练模块
├── training_result/           # 训练结果管理模块
├── fisherman_env/             # Python虚拟环境
├── logs/                      # 日志目录
├── models/                    # 训练好的模型目录
├── sql/                       # 数据库建表语句
├── training_data/             # 训练数据目录
├── database_migration.py      # 数据库迁移脚本
├── diagnose_pytorch.py        # PyTorch诊断工具
├── diagnose_pytorch_advanced.py # 高级PyTorch诊断工具
├── main.py                    # 程序主入口
├── simple_test.py             # 简单测试脚本
├── test_modular_structure.py  # 模块结构测试
├── test_module_functionality.py # 模块功能测试
├── test_without_pytorch.py    # 无PyTorch依赖的测试
├── requirements.txt           # 项目依赖
└── README.md                  # 项目说明
```

## 主程序包结构

### 1. global_support/ - 全局支撑模块

| 文件 | 功能描述 |
|------|----------|
| **database.py** | 数据库连接和操作模块，提供数据库连接、表创建和CRUD操作 |
| **task_scheduler.py** | 任务调度器，负责统一调度训练和识别任务，避免资源冲突 |

### 2. gui/ - 图形界面模块

| 目录/文件 | 功能描述 |
|-----------|----------|
| **main_window.py** | 主窗口组件(已重构,160行),负责窗口框架和标签页集成 |
| **tabs/** | 标签页模块目录,高内聚低耦合的标签页实现 |
| tabs/**training_tab.py** | 训练标签页,提供训练集创建、查看、删除功能 |
| tabs/**training_result_tab.py** | 训练结果标签页,提供模型管理功能 |
| tabs/**recognition_tab.py** | 识别标签页,提供识别任务管理功能 |
| tabs/**settings_tab.py** | 设置标签页,显示系统信息 |
| **annotation_window.py** | 标注对话框,Qt图形化标注工具 |
| **dataset_detail_dialog.py** | 训练集详情对话框,提供图片导入、标注、训练功能 |
| **log_viewer_dialog.py** | 日志查看对话框 |

### 3. recognition/ - 识别模块

| 文件 | 功能描述 |
|------|----------|
| **screen_recognition.py** | 屏幕识别模块，负责从屏幕抓取图像并识别目标物体 |

### 4. training/ - 训练模块

训练模块采用分层架构，包含以下子目录：

#### 4.1 training/core/ - 训练核心模块

| 文件 | 功能描述 |
|------|----------|
| **base_manager.py** | 训练管理器基类，提供训练过程的通用功能 |
| **interfaces.py** | 训练接口定义，规范训练过程中的数据结构和方法 |

#### 4.2 training/task/ - 任务管理模块

| 文件 | 功能描述 |
|------|----------|
| **manager.py** | 训练任务管理器，负责任务的生命周期管理（创建、更新、删除、查询） |
| **creator.py** | 训练任务创建器，负责创建新的训练任务 |
| **dataset_manager.py** | 数据集管理器，负责训练集的导入、管理和操作 |
| **status_tracker.py** | 任务状态追踪器，负责跟踪任务的执行状态和进度 |

#### 4.3 training/annotation/ - 标注模块

| 文件 | 功能描述 |
|------|----------|
| **manager.py** | 标注管理器，负责标注任务的调度和管理 |
| **tool.py** | 标注工具，提供图像标注的核心功能 |
| **validator.py** | 标注验证器，负责验证标注数据的正确性和完整性 |
| **visualizer.py** | 标注可视化工具，负责可视化标注结果 |
| **yolo_formatter.py** | YOLO格式转换器，负责将标注数据转换为YOLO训练格式 |

#### 4.4 training/training/ - 训练执行模块

| 文件 | 功能描述 |
|------|----------|
| **executor.py** | 训练执行器，负责启动和管理训练过程 |
| **callback_handler.py** | 训练回调处理器，处理训练过程中的进度更新和事件通知 |
| **result_saver.py** | 训练结果保存器，负责保存训练结果和模型 |
| **yolo_trainer.py** | YOLO训练器，负责调用YOLOv8模型进行训练 |

#### 4.5 training/utils/ - 训练工具模块

| 文件 | 功能描述 |
|------|----------|
| **file_ops.py** | 文件操作工具，提供训练过程中的文件和目录操作 |

#### 4.6 其他训练模块文件

| 文件 | 功能描述 |
|------|----------|
| **dataset_path_manager.py** | 训练集路径管理器,统一管理训练集和训练结果的目录路径及创建 |
| **annotation_tool.py** | 标注工具主入口，提供用户与标注功能的交互接口 |
| **training_manager.py** | 训练管理器主入口，整合所有训练功能并提供统一接口 |

### 5. training_result/ - 训练结果管理模块

| 文件 | 功能描述 |
|------|----------|
| **model_manager.py** | 模型管理器，负责训练结果的管理、比较和模型导入导出 |

## 项目数据存储结构

### 1. 数据库结构

项目使用SQLite数据库存储训练任务和识别任务的相关信息，主要表包括：

- **training_tasks** - 训练任务表，存储任务基本信息
- **training_logs** - 训练日志表，存储训练过程的日志信息
- **recognition_tasks** - 识别任务表，存储识别任务基本信息
- **recognition_logs** - 识别日志表，存储识别过程的日志信息
- **recognition_details** - 识别详情表，存储每次识别的详细信息
- **model_versions** - 模型版本表，存储训练好的模型版本信息

### 2. 文件存储结构

| 目录 | 功能描述 |
|------|----------|
| **training_data/** | 训练数据存储目录,使用UUID作为目录名: `training_data/{UUID}/dataset/images/`, `training_data/{UUID}/dataset/labels/` |
| **models/** | 训练好的模型存储目录 |
| **logs/** | 程序运行日志存储目录 |

## 核心功能流程

### 1. 训练流程

1. 创建训练集(自动生成UUID)
2. 导入训练图像(复制方式,非移动)
3. 打开训练集详情进行图像标注
4. 配置训练参数
5. 开始训练
6. 监控训练过程
7. 训练结果自动同步到 `training_result/` 目录

### 2. 识别流程

1. 选择训练好的模型
2. 配置识别参数
3. 选择识别区域
4. 开始识别
5. 监控识别过程
6. 记录识别结果

## 技术栈

- **图形界面**：PyQt5
- **计算机视觉**：OpenCV、YOLOv8（Ultralytics）
- **数据存储**：SQLite（SQLAlchemy ORM）
- **任务调度**：自定义任务调度器
- **屏幕操作**：mss（屏幕截图）、pyautogui（自动点击）

## 运行说明

### 启动程序

```bash
python main.py
```

### 创建训练任务

1. 在训练标签页点击"新建训练集"按钮
2. 填写训练集名称和备注
3. 点击"打开详情"按钮导入训练图像
4. 使用图形化标注工具进行图像标注
5. 配置训练参数(训练轮数、批次大小、图片尺寸、模型类型)
6. 点击"开始训练"按钮启动训练

### 执行识别任务

1. 在训练结果标签页选择训练好的模型
2. 在识别标签页选择识别区域和参数
3. 点击"开始识别"按钮启动识别任务
4. 监控识别过程和结果

## 项目特色

1. **完整的训练闭环**：从数据导入、标注、训练到模型保存的完整流程
2. **实时监控**：训练和识别过程实时监控和进度显示
3. **模块化设计**：清晰的模块划分，便于维护和扩展
4. **任务调度**：统一的任务调度机制，避免资源冲突
5. **可扩展性**：支持多任务训练和多模型管理

## 总结

Fisherman项目是一个功能完善、架构清晰的计算机视觉自动化程序，采用模块化设计，提供了训练和识别两个核心功能，并通过图形界面提供了良好的用户体验。项目的代码结构清晰，功能齐全，是一个优秀的计算机视觉应用案例。

---

# 项目进度追踪

## 进度说明

| 标记 | 含义 |
|------|------|
| ✅ 已完成 | 功能开发完成，可正常使用 |
| 🔄 进行中 | 正在开发中，部分功能可用 |
| ❌ 未开始 | 尚未开始开发 |

| 颜色 | 进度范围 |
|------|----------|
| 🟢 绿色 | 80%-100% 完成 |
| 🟡 黄色 | 30%-80% 完成 |
| 🔴 红色 | 0%-30% 完成 |

---

## 模块完成度总览

| 模块 | 完成度 | 状态 | 说明 |
|------|--------|------|------|
| **global_support** | 🟢 92% | ✅ 已完成 | 数据库和任务调度 |
| **gui** | 🟢 90% | ✅ 已完成 | 主窗口和界面（含标注窗口） |
| **recognition** | 🔄 65% | 🔄 进行中 | 屏幕识别功能 |
| **training** | 🟢 88% | ✅ 已完成 | 训练相关功能（含完整流程） |
| **training_result** | 🟢 75% | 🔄 进行中 | 模型管理 |
| **main.py** | 🔄 80% | 🔄 进行中 | 主入口 |

---

## 详细进度

### 1. global_support - 全局支撑模块

| 文件 | 功能 | 完成度 | 状态 | 待办事项 |
|------|------|--------|------|----------|
| database.py | 数据库连接和操作 | 🟢 95% | ✅ 已完成 | - 完善事务回滚机制<br>- 添加数据库备份功能 |
| task_scheduler.py | 任务调度器 | 🟢 90% | ✅ 已完成 | - 添加任务优先级设置<br>- 完善冲突检测逻辑 |

### 2. gui - 图形界面模块

| 文件 | 功能 | 完成度 | 状态 | 待办事项 |
|------|------|--------|------|----------|
| main_window.py | 主窗口(已重构为160行) | 🟢 95% | ✅ 已完成 | - 完善识别结果展示<br>- 完善训练结果管理界面 |
| tabs/training_tab.py | 训练标签页 | 🟢 100% | ✅ 已完成 | - |
| tabs/training_result_tab.py | 训练结果标签页 | 🟢 80% | 🔄 进行中 | - 完善模型列表展示<br>- 实现模型对比功能 |
| tabs/recognition_tab.py | 识别标签页 | 🟢 90% | ✅ 已完成 | - 完善识别参数配置 |
| tabs/settings_tab.py | 设置标签页 | 🟢 100% | ✅ 已完成 | - |
| dataset_detail_dialog.py | 训练集详情对话框 | 🟢 95% | ✅ 已完成 | - |
| annotation_window.py | 标注窗口 | 🟢 100% | ✅ 已完成 | - |
| log_viewer_dialog.py | 日志查看对话框 | 🟢 100% | ✅ 已完成 | - |

### 3. recognition - 识别模块

| 文件 | 功能 | 完成度 | 状态 | 待办事项 |
|------|------|--------|------|----------|
| screen_recognition.py | 屏幕识别 | 🟢 65% | 🔄 进行中 | - 完善错误处理和重试机制<br>- 添加多目标识别支持<br>- 优化识别性能<br>- 添加识别日志详细记录 |

### 4. training - 训练模块

| 文件 | 功能 | 完成度 | 状态 | 待办事项 |
|------|------|--------|------|----------|
| **core/** | 核心模块 | | | |
| base_manager.py | 训练管理器基类 | 🟢 80% | 🔄 进行中 | - 添加更多回调接口 |
| interfaces.py | 训练接口定义 | 🟢 85% | ✅ 已完成 | - |
| **路径管理** | | | | |
| dataset_path_manager.py | 训练集路径管理 | 🟢 100% | ✅ 已完成 | - |
| **task/** | 任务管理 | | | |
| manager.py | 训练任务管理器 | 🟢 75% | 🔄 进行中 | - 完善任务状态管理 |
| creator.py | 任务创建器 | 🟢 70% | 🔄 进行中 | - 完善参数校验 |
| dataset_manager.py | 数据集管理 | 🟢 100% | ✅ 已完成 | - |
| status_tracker.py | 状态追踪器 | 🟢 80% | ✅ 已完成 | - |
| **annotation/** | 标注模块 | | | |
| manager.py | 标注管理器 | 🟢 60% | 🔄 进行中 | - 完善标注任务调度 |
| tool.py | 标注工具 | 🟢 100% | ✅ 已完成 | Qt GUI标注工具已实现 |
| validator.py | 标注验证器 | 🟢 70% | 🔄 进行中 | - 完善验证规则 |
| visualizer.py | 可视化工具 | 🟢 50% | 🔄 进行中 | - 丰富可视化样式 |
| yolo_formatter.py | YOLO格式转换 | 🟢 65% | 🔄 进行中 | - 完善格式验证 |
| **training/** | 训练执行 | | | |
| executor.py | 训练执行器 | 🟢 100% | ✅ 已完成 | 支持训练结果同步 |
| callback_handler.py | 回调处理 | 🟢 70% | 🔄 进行中 | - 添加更多回调事件 |
| result_saver.py | 结果保存 | 🟢 80% | ✅ 已完成 | - |
| yolo_trainer.py | YOLO训练器 | 🟢 65% | 🔄 进行中 | - 支持更多训练参数<br>- 添加早停机制 |
| **utils/** | 工具模块 | | | |
| file_ops.py | 文件操作 | 🟢 75% | 🔄 进行中 | - 添加批量操作支持 |
| **入口文件** | | | | |
| annotation_tool.py | 标注入口 | 🟢 60% | 🔄 进行中 | - 集成GUI标注界面 |
| training_manager.py | 训练入口 | 🟢 70% | 🔄 进行中 | - 完善任务流程整合 |

### 5. training_result - 训练结果管理

| 文件 | 功能 | 完成度 | 状态 | 待办事项 |
|------|------|--------|------|----------|
| model_manager.py | 模型管理器 | 🟢 70% | 🔄 进行中 | - 添加模型对比功能<br>- 完善模型导入导出<br>- 添加模型版本管理 |

### 6. 主程序

| 文件 | 功能 | 完成度 | 状态 | 待办事项 |
|------|------|--------|------|----------|
| main.py | 程序入口(已简化,删除minimal_window回退逻辑) | 🟢 95% | ✅ 已完成 | - |

---

## 开发优先级建议

### 第一优先级（核心功能）
1. ✅ global_support/database.py - 已完成
2. ✅ global_support/task_scheduler.py - 已完成
3. ✅ gui/main_window.py - 已完成
4. ✅ training/dataset_path_manager.py - 已完成
5. ✅ training/task/dataset_manager.py - 已完成
6. ✅ training/training/executor.py - 已完成
7. ✅ gui/annotation_window.py - 已完成
8. 🔄 recognition/screen_recognition.py - 完善识别功能

### 第二优先级（体验优化）
1. 🔄 gui/main_window.py - 训练结果管理界面
2. 🔄 training_result/model_manager.py - 模型管理完善
3. 🔄 gui/main_window.py - 设置页面

### 第三优先级（高级功能）
1. 分布式训练支持
2. 多模型协同识别
3. 云端模型同步

---

## 最近更新 (2026-02-27)

### 重构优化
1. ✅ **重构 `gui/main_window.py`** - 从968行重构为160行,实现高内聚低耦合
2. ✅ **创建 `gui/tabs/` 模块** - 将标签页拆分为独立文件:
   - `training_tab.py` - 训练集管理
   - `training_result_tab.py` - 模型管理
   - `recognition_tab.py` - 识别任务管理
   - `settings_tab.py` - 系统信息
3. ✅ **删除 `gui/minimal_window.py`** - 移除不必要的最小化窗口回退机制
4. ✅ **简化 `main.py`** - 删除minimal_window相关逻辑,直接导入主窗口
5. ✅ **修复路径问题** - 修正 `dataset_path_manager.py` 的 `BASE_DIR` 计算错误

### 功能改进
- 训练集创建对话框简化,移除重复的"描述"字段,只保留"备注"
- 训练集目录使用UUID命名: `training_data/{UUID}/dataset/images/`
- 图片导入使用复制方式,不移动原文件
- 数据库表ID改为UUID格式

### 架构优势
- **高内聚低耦合**: 每个标签页独立管理自己的UI和逻辑
- **职责清晰**: 各模块功能明确,互不干扰
- **易于维护**: 修改一个功能不影响其他模块
- **代码复用**: 标签页可在其他地方复用

### 目录结构
```
training_data/
└── {UUID}/                    # 使用UUID作为训练集ID
    ├── dataset/
    │   ├── images/           # 训练图片(复制方式)
    │   ├── labels/           # YOLO格式标注
    │   └── remark.txt        # 备注信息
    ├── models/               # 训练好的模型
    └── annotations/          # 标注数据
```

### 第二优先级（体验优化）
1. training/annotation/tool.py - 标注工具优化
2. training_result/model_manager.py - 模型管理完善
3. gui/main_window.py - 设置页面

### 第三优先级（高级功能）
1. 分布式训练支持
2. 多模型协同识别
3. 云端模型同步
