---
name: 将所有表 id 改为 UUID
overview: 将数据库6张表的主键 id 和外键从 INTEGER 改为 UUID 格式
todos:
  - id: modify-sql-schema
    content: 修改 sql/create_tables.sql 建表语句，将所有改为 id 和外键 UUID 类型
    status: completed
  - id: modify-orm-models
    content: 修改 global_support/database.py 的 ORM 模型定义
    status: completed
    dependencies:
      - modify-sql-schema
---

## 需求概述

将所有数据库表的 id 从 INTEGER AUTOINCREMENT 改为 UUID（标准格式，如 550e8400-e29b-41d4-a716-446655440000）

## 数据处理

直接删除旧表，用新结构重建（数据会丢失）

## 涉及修改的表（6张）

| 表名 | 主键修改 | 外键修改 |
| --- | --- | --- |
| training_tasks | id → TEXT PRIMARY KEY | - |
| training_logs | id → TEXT PRIMARY KEY | training_task_id → TEXT |
| recognition_tasks | id → TEXT PRIMARY KEY | training_task_id → TEXT |
| recognition_logs | id → TEXT PRIMARY KEY | recognition_task_id → TEXT |
| recognition_details | id → TEXT PRIMARY KEY | recognition_task_id → TEXT |
| model_versions | id → TEXT PRIMARY KEY | training_task_id → TEXT |


## 技术方案

### 修改文件

1. **sql/create_tables.sql** - 建表语句

- 主键 id 改为 TEXT PRIMARY KEY
- 外键字段改为 TEXT 类型
- 添加 UUID 生成函数作为默认值

2. **global_support/database.py** - ORM 模型

- 主键 id 改为 Column(String(36), primary_key=True)
- 外键字段改为 Column(String(36), ForeignKey(...))
- 使用 Python uuid.uuid4() 生成 UUID

### 实现细节

- SQL 使用 `gen_random_uuid()` 或应用程序层生成
- SQLAlchemy 模型使用 `default=lambda: str(uuid.uuid4())`