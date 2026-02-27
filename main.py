#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fisherman - 视觉自动化程序主入口

这是 Fisherman 程序的主入口文件，负责初始化应用程序并启动主界面。

程序架构：
- 训练模块：管理训练任务、数据集、标注和训练过程
- 训练结果管理模块：管理模型文件、版本对比
- 识别模块：实时屏幕监控、目标识别、自动点击
- 全局支撑模块：任务调度、日志系统
- GUI界面：PyQt5实现的用户交互界面
"""

import sys
import os
import logging

# 配置基础日志记录
logging.basicConfig(level=logging.INFO)

# 简化PyTorch导入检查，不处理DLL路径
pytorch_available = False
try:
    import torch
    pytorch_available = True
    logging.info("PyTorch库导入成功")
except Exception as e:
    logging.warning(f"PyTorch导入失败: {e}")
    logging.warning("程序将继续运行，但PyTorch相关功能可能不可用")

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入其他依赖项
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtGui import QIcon

# 导入主窗口模块
from gui.main_window import MainWindow
logging.info("成功导入主窗口模块")

# 配置日志系统
def setup_logging():
    """设置程序的日志系统"""
    log_dir = os.path.join(project_root, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, "fisherman.log")
    
    # 配置根日志记录器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """程序主函数"""
    logger = setup_logging()
    logger.info("Starting Fisherman application...")
    
    try:
        # 创建Qt应用程序实例
        app = QApplication(sys.argv)
        app.setApplicationName("Fisherman")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Fisherman Team")
        
        # 设置应用程序图标（如果有）
        # icon_path = os.path.join(project_root, "resources", "icon.png")
        # if os.path.exists(icon_path):
        #     app.setWindowIcon(QIcon(icon_path))
        
        # 创建并显示主窗口
        logger.info("Creating main window...")
        window = MainWindow()
        window.show()
        logger.info("Fisherman application started successfully")

        # 运行应用程序事件循环
        sys.exit(app.exec_())
            
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}", exc_info=True)
        print(f"启动程序时出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()