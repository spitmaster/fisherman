#!/usr/bin/env python3
"""测试所有模块的导入"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_import(module_name, class_name=None):
    """测试导入模块"""
    try:
        module = __import__(module_name, fromlist=[''])
        if class_name:
            getattr(module, class_name)
        print(f"✓ {module_name}" + (f".{class_name}" if class_name else ""))
        return True
    except ImportError as e:
        print(f"✗ {module_name}: {e}")
        return False
    except AttributeError as e:
        print(f"✗ {module_name}.{class_name}: {e}")
        return False

def main():
    print("测试模块导入...")
    
    # 测试核心模块
    modules_to_test = [
        ('capture.screen_capture', 'ScreenCapture'),
        ('detection.yolo_detector', 'YOLODetector'),
        ('detection.shake_detector', 'ShakeDetector'),
        ('storage.data_storage', 'DataStorage'),
        ('training.data_manager', 'DataManager'),
        ('training.model_trainer', 'ModelTrainer'),
        ('monitoring.monitor', 'Monitor'),
        ('gui.main_window', 'MainWindow'),
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    for module_name, class_name in modules_to_test:
        if test_import(module_name, class_name):
            success_count += 1
    
    print(f"\n导入测试完成: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("所有模块导入成功！")
        return 0
    else:
        print("部分模块导入失败，请检查依赖项。")
        return 1

if __name__ == "__main__":
    sys.exit(main())