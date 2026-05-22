import sys
import os
import logging
import sqlite3
from pathlib import Path

# 配置基础日志记录
logging.basicConfig(level=logging.INFO)

def check_and_migrate_database():
    """检查并迁移数据库表结构"""
    try:
        # 数据库文件路径
        db_path = "fisherman.db"
        
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            logging.info("数据库文件不存在，将创建新的数据库")
            return True
            
        # 连接到SQLite数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查training_tasks表是否包含epochs和batch_size列
        cursor.execute("PRAGMA table_info(training_tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        logging.info(f"当前training_tasks表列: {columns}")
        
        # 检查是否需要添加epochs列
        if "epochs" not in columns:
            logging.info("添加epochs列")
            cursor.execute("ALTER TABLE training_tasks ADD COLUMN epochs INTEGER DEFAULT 50")
            
        # 检查是否需要添加batch_size列
        if "batch_size" not in columns:
            logging.info("添加batch_size列")
            cursor.execute("ALTER TABLE training_tasks ADD COLUMN batch_size INTEGER DEFAULT 16")
            
        # 确保 image_library 表存在（M3 新增）
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_library'")
        if not cursor.fetchone():
            logging.info("创建 image_library 表")
            cursor.execute("""
                CREATE TABLE image_library (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    source TEXT DEFAULT 'import',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_library_source ON image_library(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_library_created ON image_library(created_at)")

        # 提交更改
        conn.commit()

        # 再次检查表结构
        cursor.execute("PRAGMA table_info(training_tasks)")
        new_columns = [column[1] for column in cursor.fetchall()]
        logging.info(f"更新后的training_tasks表列: {new_columns}")

        conn.close()
        
        logging.info("数据库迁移成功")
        return True
        
    except Exception as e:
        logging.error(f"数据库迁移失败: {e}")
        import traceback
        logging.error(f"错误堆栈: {traceback.format_exc()}")
        return False

def test_database_query():
    """测试数据库查询"""
    try:
        # 连接到数据库
        from global_support.database import db_manager
        if db_manager.connect():
            # 测试基本查询
            with db_manager.get_session() as session:
                from global_support.database import TrainingTask
                count = session.query(TrainingTask).count()
                logging.info(f"训练任务数量: {count}")
                
                return True
        else:
            logging.error("数据库连接失败")
            return False
            
    except Exception as e:
        logging.error(f"数据库查询失败: {e}")
        import traceback
        logging.error(f"错误堆栈: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    logging.info("开始数据库迁移")
    
    # 检查并迁移数据库
    if check_and_migrate_database():
        logging.info("数据库迁移成功")
        
        # 测试查询
        if test_database_query():
            logging.info("数据库查询测试成功")
        else:
            logging.error("数据库查询测试失败")
    else:
        logging.error("数据库迁移失败")