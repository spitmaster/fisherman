-- Fisherman 视觉自动化程序 - 数据库建表语句
-- 用于存储训练任务、训练结果、识别任务和日志信息
-- 所有主键和部分字段使用 UUID 格式

-- 训练任务表
CREATE TABLE IF NOT EXISTS training_tasks (
    id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    task_description TEXT,
    status TEXT DEFAULT 'pending', -- pending/annotating/training/completed/failed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    dataset_path TEXT,
    model_path TEXT,
    epochs INTEGER DEFAULT 50,
    batch_size INTEGER DEFAULT 8,
    mAP REAL,
    loss REAL
);

-- 训练日志表
CREATE TABLE IF NOT EXISTS training_logs (
    id TEXT PRIMARY KEY,
    training_task_id TEXT,
    log_level TEXT DEFAULT 'INFO',
    log_message TEXT,
    log_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (training_task_id) REFERENCES training_tasks(id)
);

-- 识别任务表
CREATE TABLE IF NOT EXISTS recognition_tasks (
    id TEXT PRIMARY KEY,
    training_task_id TEXT,
    status TEXT DEFAULT 'pending', -- pending/running/stopped/completed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    ended_at DATETIME,
    confidence_threshold INTEGER DEFAULT 70,
    click_cooldown INTEGER DEFAULT 5,
    total_recognitions INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,
    avg_fps INTEGER DEFAULT 0,
    FOREIGN KEY (training_task_id) REFERENCES training_tasks(id)
);

-- 识别日志表
CREATE TABLE IF NOT EXISTS recognition_logs (
    id TEXT PRIMARY KEY,
    recognition_task_id TEXT,
    log_level TEXT DEFAULT 'INFO',
    log_message TEXT,
    log_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recognition_task_id) REFERENCES recognition_tasks(id)
);

-- 识别详情表
CREATE TABLE IF NOT EXISTS recognition_details (
    id TEXT PRIMARY KEY,
    recognition_task_id TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    target_x INTEGER,
    target_y INTEGER,
    confidence INTEGER,
    target_class TEXT,
    FOREIGN KEY (recognition_task_id) REFERENCES recognition_tasks(id)
);

-- 模型版本表
CREATE TABLE IF NOT EXISTS model_versions (
    id TEXT PRIMARY KEY,
    training_task_id TEXT,
    model_path TEXT,
    version TEXT,
    is_default BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_size INTEGER,
    FOREIGN KEY (training_task_id) REFERENCES training_tasks(id)
);

-- 图库表
CREATE TABLE IF NOT EXISTS image_library (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL,
    source TEXT DEFAULT 'import', -- screenshot/import
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_training_task_status ON training_tasks(status);
CREATE INDEX IF NOT EXISTS idx_training_task_created ON training_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_training_log_task ON training_logs(training_task_id);
CREATE INDEX IF NOT EXISTS idx_recognition_task_status ON recognition_tasks(status);
CREATE INDEX IF NOT EXISTS idx_recognition_log_task ON recognition_logs(recognition_task_id);
CREATE INDEX IF NOT EXISTS idx_recognition_detail_task ON recognition_details(recognition_task_id);
CREATE INDEX IF NOT EXISTS idx_model_version_task ON model_versions(training_task_id);
CREATE INDEX IF NOT EXISTS idx_model_version_default ON model_versions(is_default);
CREATE INDEX IF NOT EXISTS idx_image_library_source ON image_library(source);
CREATE INDEX IF NOT EXISTS idx_image_library_created ON image_library(created_at);

-- 初始化数据（可选）
-- INSERT INTO training_tasks (task_name, task_description, status) VALUES ('示例任务', '这是一个示例训练任务', 'pending');
