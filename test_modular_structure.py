#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试重构后的模块化结构

验证模块是否能够正确导入和基本功能是否正常。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    
    try:
        # 测试导入新模块
        from training import training_manager, annotation_manager
        print("✓ 成功导入 training_manager 和 annotation_manager")
        
        from training.task import TaskCreator, TaskStatusTracker, DatasetManager
        print("✓ 成功导入 task 模块")
        
        from training.annotation import AnnotationTool, AnnotationManager
        print("✓ 成功导入 annotation 模块")
        
        from training.training import TrainingExecutor, YOLOTrainer
        print("✓ 成功导入 training 模块")
        
        from training.utils import create_task_directory, get_image_files
        print("✓ 成功导入 utils 模块")
        
        from training.core import BaseManager, ITrainingManager
        print("✓ 成功导入 core 模块")
        
        return True
        
    except Exception as e:
        print(f"✗ 导入模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manager_creation():
    """测试管理器创建"""
    print("\n测试管理器创建...")
    
    try:
        from training import training_manager, annotation_manager
        
        # 检查管理器实例
        if training_manager is not None:
            print(f"✓ training_manager 类型: {type(training_manager).__name__}")
            
            # 检查是否有必要的方法
            required_methods = [
                'get_all_training_tasks',
                'create_training_task',
                'get_training_task_by_id'
            ]
            
            for method in required_methods:
                if hasattr(training_manager, method):
                    print(f"  ✓ training_manager 有方法: {method}")
                else:
                    print(f"  ✗ training_manager 缺少方法: {method}")
                    return False
                    
        else:
            print("✗ training_manager 为 None")
            return False
            
        if annotation_manager is not None:
            print(f"✓ annotation_manager 类型: {type(annotation_manager).__name__}")
        else:
            print("✗ annotation_manager 为 None")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ 测试管理器创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_module_structure():
    """测试模块结构"""
    print("\n测试模块结构...")
    
    try:
        # 检查模块结构
        import training as training_module
        
        # 检查子模块是否存在
        submodules = ['task', 'annotation', 'training', 'utils', 'core']
        
        for submodule in submodules:
            try:
                module = getattr(training_module, submodule, None)
                if module is not None:
                    print(f"✓ 子模块存在: {submodule}")
                else:
                    print(f"✗ 子模块不存在: {submodule}")
                    return False
            except Exception:
                print(f"✗ 子模块访问失败: {submodule}")
                return False
                
        return True
        
    except Exception as e:
        print(f"✗ 测试模块结构失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("测试重构后的模块化结构")
    print("=" * 60)
    
    tests = [
        ("模块导入测试", test_imports),
        ("管理器创建测试", test_manager_creation),
        ("模块结构测试", test_module_structure)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        if test_func():
            passed_tests += 1
            print(f"✓ {test_name} 通过")
        else:
            print(f"✗ {test_name} 失败")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("✓ 所有测试通过！模块化结构工作正常。")
        return 0
    else:
        print("✗ 部分测试失败，需要检查模块结构。")
        return 1


if __name__ == "__main__":
    sys.exit(main())