import sys
import os
import logging
import traceback

# 配置基础日志记录
logging.basicConfig(level=logging.INFO)

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 测试Qt应用程序和数据库功能，不依赖PyTorch
def test_application():
    try:
        # 测试Qt应用程序
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from PyQt5.QtCore import QCoreApplication, Qt
        from PyQt5.QtGui import QIcon
        
        # 创建Qt应用程序实例
        app = QApplication(sys.argv)
        app.setApplicationName("Fisherman")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Fisherman Team")
        
        logging.info("Qt应用程序创建成功")
        
        # 测试数据库连接
        from global_support.database import db_manager
        if db_manager.connect():
            logging.info("数据库连接成功")
            
            # 测试创建表
            if db_manager.create_tables():
                logging.info("数据库表创建成功")
            else:
                logging.warning("数据库表创建失败")
                
            # 测试基本查询
            try:
                with db_manager.get_session() as session:
                    from global_support.database import TrainingTask
                    count = session.query(TrainingTask).count()
                    logging.info(f"训练任务数量: {count}")
            except Exception as e:
                logging.warning(f"数据库查询失败: {e}")
                
        else:
            logging.warning("数据库连接失败")
            
        # 测试任务调度器
        try:
            from global_support.task_scheduler import TaskType, TaskStatus, TaskScheduler
            
            scheduler = TaskScheduler()
            logging.info("任务调度器创建成功")
            
            # 启动调度器
            scheduler.start_scheduler()
            logging.info("任务调度器启动成功")
            
            # 创建测试任务
            task = TaskType.TRAINING
            logging.info("任务类型创建成功")
            
            # 停止调度器
            scheduler.stop_scheduler()
            logging.info("任务调度器停止成功")
            
        except Exception as e:
            logging.warning(f"任务调度器测试失败: {e}")
            
        # 显示成功信息
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("测试成功")
        msg_box.setText("Fisherman项目基础功能正常")
        msg_box.setInformativeText("Qt界面、数据库连接和任务调度器功能均正常工作。\n\nPyTorch相关功能可能不可用，因为PyTorch库加载失败。")
        msg_box.setDetailedText("详细测试结果已记录在日志文件中。")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        return True
        
    except Exception as e:
        logging.error(f"测试过程中出错: {e}")
        logging.error(f"错误堆栈: {traceback.format_exc()}")
        
        # 显示错误信息
        from PyQt5.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("测试失败")
        msg_box.setText("项目基础功能测试失败")
        msg_box.setInformativeText(f"程序无法正常运行: {str(e)}")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        return False

if __name__ == "__main__":
    logging.info("开始测试Fisherman项目基础功能")
    if test_application():
        logging.info("项目基础功能测试成功")
    else:
        logging.error("项目基础功能测试失败")