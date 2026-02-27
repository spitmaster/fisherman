---
name: Training模块代码重构
overview: 将training模块代码按高内聚低耦合原则拆分，使用面向对象思想重构
todos:
  - id: analyze-code-structure
    content: 分析现有代码结构，确定具体拆分方案
    status: completed
  - id: create-training-validator
    content: 新建 training/validator.py - 训练验证器
    status: completed
    dependencies:
      - analyze-code-structure
  - id: create-training-statistics
    content: 新建 training/statistics.py - 训练统计模块
    status: completed
    dependencies:
      - analyze-code-structure
  - id: create-training-backup
    content: 新建 training/backup.py - 训练备份恢复模块
    status: completed
    dependencies:
      - analyze-code-structure
  - id: create-annotation-exporter
    content: 新建 annotation/exporter.py - 标注导出器
    status: completed
    dependencies:
      - analyze-code-structure
  - id: refactor-training-manager
    content: 重构 training_manager.py - 简化 facade，委托子模块
    status: completed
    dependencies:
      - create-training-validator
      - create-training-statistics
      - create-training-backup
  - id: refactor-annotation-tool
    content: 重构 annotation_tool.py - 简化 facade，委托子模块
    status: completed
    dependencies:
      - create-annotation-exporter
  - id: update-init-export
    content: 更新 training/__init__.py 统一导出
    status: completed
    dependencies:
      - refactor-training-manager
      - refactor-annotation-tool
  - id: test-backward-compatibility
    content: 测试向后兼容性，确保现有调用不受影响
    status: completed
    dependencies:
      - update-init-export
---

## 需求概述

当前training模块代码混乱，单个py文件上千行，难以维护。需要使用面向对象思想进行拆分重构，提高代码可维护性和可扩展性。

## 现状分析

1. **training_manager.py (1460行, 35个方法)** - 混杂了任务CRUD、数据集管理、标注、训练执行、结果保存、验证、备份恢复、统计等功能
2. **annotation_tool.py (1197行, 35个方法)** - 混杂了标注工具GUI、标注管理、验证、导出、备份恢复等功能

## 现有良好基础

项目已有较完善的模块化结构：

- `task/` - 任务管理 (manager.py, creator.py, dataset_manager.py, status_tracker.py)
- `training/` - 训练相关 (executor.py, yolo_trainer.py, result_saver.py, callback_handler.py)
- `annotation/` - 标注相关 (tool.py, manager.py, validator.py, visualizer.py, yolo_formatter.py)
- `core/` - 核心接口 (interfaces.py, base_manager.py)

## 重构目标

- 遵循SOLID原则，保持单一职责
- 保持向后兼容，不破坏现有调用
- 提高代码可读性、可测试性和可维护性

## 技术方案

### 重构策略

采用" facade模式 + 委托模式"：保留原有 facade 类作为统一入口，将具体实现委托给各子模块。

### 目录结构规划

```
training/
├── __init__.py                    # [MODIFY] 更新导出
├── training_manager.py             # [MODIFY] 简化 facade，委托给子模块
├── annotation_tool.py             # [MODIFY] 简化 facade，委托给子模块
├── task/
│   ├── manager.py                 # [NEW] 任务管理器 - 封装task CRUD
│   ├── dataset_manager.py         # [MODIFY] 扩展数据集管理功能
│   └── status_tracker.py          # [EXIST] 已有
├── training/
│   ├── executor.py                # [MODIFY] 扩展训练执行功能
│   ├── validator.py               # [NEW] 训练验证器
│   ├── statistics.py              # [NEW] 训练统计
│   └── backup.py                  # [NEW] 训练备份恢复
├── annotation/
│   ├── tool.py                    # [EXIST] 标注工具
│   ├── manager.py                 # [MODIFY] 扩展标注管理
│   └── exporter.py                # [NEW] 标注导出器
└── core/
    ├── interfaces.py              # [MODIFY] 扩展接口定义
    └── base_manager.py            # [EXIST] 已有
```

### 拆分映射

**training_manager.py 拆分方案:**

| 现有方法 | 目标模块 |
| --- | --- |
| 任务CRUD (create/delete/update/get) | task/manager.py |
| 数据集相关 (import_images/get_dataset_info) | task/dataset_manager.py |
| 标注相关 (start_annotation/save_annotation) | annotation/manager.py |
| 训练执行 (start_training/_run_training) | training/executor.py |
| 结果保存 (_save_training_result) | training/result_saver.py |
| 验证 (validate_training_task) | training/validator.py |
| 备份恢复 (create_backup/restore_backup) | training/backup.py |
| 统计 (get_training_statistics) | training/statistics.py |


**annotation_tool.py 拆分方案:**

| 现有方法 | 目标模块 |
| --- | --- |
| GUI标注 (start_gui_annotation) | annotation/tool.py |
| OpenCV标注 (_run_opencv_annotation_loop) | annotation/tool.py |
| 标注验证 (batch_validate_annotations) | annotation/validator.py |
| 导出 (batch_export_annotations) | annotation/exporter.py |
| 备份恢复 (create_backup/restore_backup) | annotation/backup.py |
| 统计 (get_annotation_progress) | annotation/manager.py |