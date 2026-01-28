import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox

# 添加项目根目录到导入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == '__main__':
    # 创建应用程序实例
    app = QApplication(sys.argv)
    
    try:
        # 尝试导入和创建监控实例
        from gui import MainWindow
        from main import ScreenMonitor
        
        # 创建监控实例
        monitor = ScreenMonitor()
        
        # 创建主窗口
        window = MainWindow(monitor)
        window.show()
        
        # 运行应用程序
        sys.exit(app.exec_())
    except ImportError as e:
        # 处理导入错误
        error_msg = f"导入模块时出错: {e}\n\n"
        if "config" in str(e):
            error_msg += "找不到config模块，请检查目录结构是否正确。\n"
        elif "torch" in str(e):
            error_msg += "这可能是由于PyTorch环境问题导致的。\n"
            error_msg += "解决方案: 1. 确保安装了兼容的PyTorch版本\n"
            error_msg += "2. 尝试使用Python 3.9或3.10版本\n"
        error_msg += "3. 重新安装依赖: pip install -r requirements.txt"
        
        QMessageBox.critical(None, "错误", error_msg)
        sys.exit(1)
    except Exception as e:
        # 处理其他错误
        error_msg = f"启动程序时出错: {e}"
        QMessageBox.critical(None, "错误", error_msg)
        sys.exit(1)
