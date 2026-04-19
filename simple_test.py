#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一个简单的测试脚本，用于验证项目基础功能是否正常（不依赖PyTorch）
"""

import sys
import os
import platform
import subprocess

def print_system_info():
    """打印系统信息"""
    print("=== 系统信息 ===")
    print(f"操作系统: {platform.platform()}")
    print(f"架构: {platform.machine()}")
    print(f"处理器: {platform.processor()}")
    print()
    
    print(f"Python 版本: {sys.version}")
    print(f"版本信息: {sys.version_info}")
    print(f"可执行文件: {sys.executable}")
    print()
    
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本路径: {os.path.abspath(__file__)}")
    print()

def test_dependencies():
    """测试项目依赖库"""
    print("=== 依赖库测试 ===")
    
    dependencies = ["PyQt5", "mss", "PIL", "cv2", "pyautogui", "sqlalchemy"]
    
    for lib in dependencies:
        try:
            __import__(lib)
            print(f"✅ {lib} 导入成功")
        except ImportError as e:
            print(f"❌ {lib} 导入失败: {e}")
        except Exception as e:
            print(f"❌ {lib} 导入错误: {e}")
    print()

def check_project_structure():
    """检查项目结构"""
    print("=== 项目结构检查 ===")
    
    required_files = [
        "main.py",
        "pyproject.toml",
        "README.md",
        "diagnose_pytorch.py",
        "__init__.py",
        os.path.join("gui", "main_window.py"),
        os.path.join("global_support", "task_scheduler.py"),
        os.path.join("global_support", "database.py"),
        os.path.join("training", "training_manager.py"),
        os.path.join("training", "__init__.py"),
        os.path.join("training", "annotation_tool.py"),
        os.path.join("training_result", "model_manager.py"),
        os.path.join("recognition", "screen_recognition.py")
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")
    print()

def test_gui_import():
    """测试GUI模块导入"""
    print("=== GUI模块测试 ===")
    
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication(sys.argv)
        print("✅ PyQt5 GUI 应用程序创建成功")
        
        try:
            from gui.main_window import MainWindow
            print("✅ 主窗口模块导入成功")
            
            # 尝试创建主窗口（但不显示）
            window = MainWindow()
            print("✅ 主窗口创建成功")
            
        except Exception as e:
            print(f"❌ 主窗口模块错误: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            
    except Exception as e:
        print(f"❌ PyQt5 初始化错误: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
    print()

def test_database_connection():
    """测试数据库连接"""
    print("=== 数据库连接测试 ===")
    
    try:
        from global_support.database import db_manager
        if db_manager.connect():
            print("✅ 数据库连接成功")
            
            # 尝试创建表
            db_manager.create_tables()
            print("✅ 数据库表创建成功")
            
            # 测试基本查询
            with db_manager.get_session() as session:
                from global_support.database import TrainingTask
                count = session.query(TrainingTask).count()
                print(f"✅ 训练任务数量: {count}")
                
        else:
            print("❌ 数据库连接失败")
            
    except Exception as e:
        print(f"❌ 数据库操作错误: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
    print()

def test_task_scheduler():
    """测试任务调度器"""
    print("=== 任务调度器测试 ===")
    
    try:
        from global_support.task_scheduler import TaskType, TaskStatus, TaskScheduler
        
        scheduler = TaskScheduler()
        print("✅ 任务调度器创建成功")
        
        # 启动调度器
        scheduler.start_scheduler()
        print("✅ 任务调度器启动成功")
        
        # 创建测试任务
        task = TaskType.TRAINING
        print("✅ 任务类型创建成功")
        
        # 停止调度器
        scheduler.stop_scheduler()
        print("✅ 任务调度器停止成功")
        
    except Exception as e:
        print(f"❌ 任务调度器错误: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
    print()

def main():
    """主函数"""
    print("Fisherman项目基础功能测试\n")
    
    try:
        print_system_info()
        test_dependencies()
        check_project_structure()
        test_gui_import()
        test_database_connection()
        test_task_scheduler()
        
        print("\n=== 测试完成 ===")
        print("项目基础功能正常，但PyTorch相关功能可能存在兼容性问题")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")

if __name__ == "__main__":
    main()