# 05 数据库设计

## 1. 存储概览

- **数据库引擎**：SQLite
- **文件位置**：`fisherman.db`（项目根目录）
- **ORM**：SQLAlchemy（`declarative_base`）
- **建表 SQL**：`sql/create_tables.sql`（权威手工脚本，供直接建库/审阅用）
- **迁移脚本**：`database_migration.py`

所有主键均为 UUID（`String(36)`），由 Python 侧 `uuid.uuid4()` 生成。

## 2. 实体关系

```
TrainingTask (1) ──< (N) TrainingLog
TrainingTask (1) ──< (N) ModelVersion
TrainingTask (1) ──< (N) RecognitionTask
RecognitionTask (1) ──< (N) RecognitionLog
RecognitionTask (1) ──< (N) RecognitionDetail
```

## 3. 表结构

### 3.1 training_tasks — 训练任务
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| task_name | TEXT NOT NULL | 训练集/任务名 |
| task_description | TEXT | 备注 |
| status | TEXT | pending / annotating / training / completed / failed |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |
| dataset_path | TEXT | 数据集路径（`training_data/{uuid}/dataset`） |
| model_path | TEXT | 训练产出模型路径 |
| epochs | INTEGER | 训练轮数（默认 50） |
| batch_size | INTEGER | 批次大小（默认 8） |
| mAP | REAL | 最终 mAP |
| loss | REAL | 最终 loss |

### 3.2 training_logs — 训练日志
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| training_task_id | TEXT FK | 关联训练任务 |
| log_level | TEXT | INFO/WARN/ERROR 等 |
| log_message | TEXT | 日志正文 |
| log_time | DATETIME | 时间 |

### 3.3 recognition_tasks — 识别任务
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| training_task_id | TEXT FK | 使用哪个训练任务的模型 |
| status | TEXT | pending / running / stopped / completed |
| created_at | DATETIME | 创建时间 |
| started_at | DATETIME | 开始时间 |
| ended_at | DATETIME | 结束时间 |
| confidence_threshold | INTEGER | 置信度阈值（0-100，UI 侧使用） |
| click_cooldown | INTEGER | 点击冷却（秒） |
| total_recognitions | INTEGER | 累计识别次数 |
| total_clicks | INTEGER | 累计点击次数 |
| avg_fps | INTEGER | 平均帧率 |

### 3.4 recognition_logs — 识别日志
同 training_logs，但关联 `recognition_task_id`。

### 3.5 recognition_details — 识别详情
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| recognition_task_id | TEXT FK | 所属识别任务 |
| timestamp | DATETIME | 识别时间戳 |
| target_x / target_y | INTEGER | 目标中心点坐标 |
| confidence | INTEGER | 置信度（0-100） |
| target_class | TEXT | 目标类别名 |

### 3.6 model_versions — 模型版本
| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | UUID |
| training_task_id | TEXT FK | 所属训练任务 |
| model_path | TEXT | 权重文件 |
| version | TEXT | 版本号/标签 |
| is_default | BOOLEAN | 是否默认 |
| created_at | DATETIME | 创建时间 |
| file_size | INTEGER | 文件大小（字节） |

## 4. 索引策略

| 索引 | 用途 |
|------|------|
| idx_training_task_status | 列表按状态过滤 |
| idx_training_task_created | 按时间排序 |
| idx_training_log_task | 按任务查日志 |
| idx_recognition_task_status | 识别任务按状态过滤 |
| idx_recognition_log_task | 按识别任务查日志 |
| idx_recognition_detail_task | 按识别任务查详情 |
| idx_model_version_task | 按训练任务查模型 |
| idx_model_version_default | 快速定位默认模型 |

## 5. 数据一致性与约束

- 所有外键（`FOREIGN KEY`）由 SQLAlchemy 关系维护，删除父记录时需应用层级联（当前未在表上声明 ON DELETE CASCADE，删除训练任务时需应用层删除子表数据与磁盘目录）
- 状态字段采用字符串枚举（非 CHECK 约束），由业务层 `StatusTracker` 保证合法值
- `ModelVersion.is_default` 至多一条为 1，由 `ModelManager.set_default()` 在同一事务内切换

## 6. 数据生命周期

1. 创建训练集 → 插入 `training_tasks`，状态 `pending`
2. 开始标注 → 状态改为 `annotating`
3. 开始训练 → 状态改为 `training`，持续写入 `training_logs`
4. 训练结束 → 状态改为 `completed` 或 `failed`，写入 `model_versions`
5. 用户启动识别 → 插入 `recognition_tasks`，持续写入 `recognition_logs` + `recognition_details`
6. 停止识别 → 更新 `ended_at` 与统计字段

## 7. 迁移策略

- 轻量改动通过 `database_migration.py` 顺序执行 ALTER
- 重大结构变更建议：导出 → 重建 → 导入，保留 `sql/create_tables.sql` 为单一权威
