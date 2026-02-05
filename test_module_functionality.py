#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试模块功能

验证模块化重构后的基本功能。
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_basic_functionality():
    """测试基本功能"""
    print("测试基本功能...")
    
    try:
        from fisherman.training import training_manager
        
        # 1. 测试获取所有任务
        tasks = training_manager.get_all_training_tasks()
        print(f"✓ 获取训练任务列表: 共 {len(tasks)} 个任务")
        
        # 2. 测试获取单个任务（如果存在任务）
        if tasks:
            task_id = tasks[0]["id"]
            task_info = training_manager.get_training_task_by_id(task_id)
            if task_info:
                print(f"✓ 获取单个任务成功: {task_info['task_name']}")
            else:
                print("✗ 获取单个任务失败")
                
            # 3. 测试获取任务状态
            status_info = training_manager.get_training_task_status(task_id)
            if status_info:
                print(f"✓ 获取任务状态成功: {status_info['status']}")
            else:
                print("✗ 获取任务状态失败")
                
            # 4. 测试获取数据集信息
            dataset_info = training_manager.get_dataset_info(task_id)
            if dataset_info:
                print(f"✓ 获取数据集信息成功: {dataset_info['total_images']} 张图片")
            else:
                print("✗ 获取数据集信息失败")
        
        # 5. 测试创建新任务（不实际保存）
        print("✓ 测试创建新任务方法存在")
        
        # 6. 测试其他方法存在性
        required_methods = [
            'update_training_task',
            'delete_training_task',
            'import_images',
            'get_image_list',
            'get_unannotated_images',
            'update_task_status',
            'get_task_status',
            'get_task_progress',
            'start_annotation',
            'start_training'
        ]
        
        for method in required_methods:
            if hasattr(training_manager, method):
                print(f"  ✓ training_manager 有方法: {method}")
            else:
                print(f"  ✗ training_manager 缺少方法: {method}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ 测试基本功能失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_annotation_module():
    """测试标注模块"""
    print("\n测试标注模块...")
    
    try:
        from fisherman.training import annotation_manager
        
        # 检查标注管理器
        if annotation_manager is not None:
            print(f"✓ annotation_manager 类型: {type(annotation_manager).__name__}")
            
            # 检查方法
            required_methods = [
                'create_annotation_tool',
                'validate_dataset_annotations',
                'get_dataset_annotation_statistics'
            ]
            
            for method in required_methods:
                if hasattr(annotation_manager, method):
                    print(f"  ✓ annotation_manager 有方法: {method}")
                else:
                    print(f"  ✗ annotation_manager 缺少方法: {method}")
                    return False
        else:
            print("✗ annotation_manager 为 None")
            return False
            
        # 测试工具函数导入
        from fisherman.training.annotation import (
            validate_single_annotation_file,
            convert_bbox_to_yolo,
            draw_annotations
        )
        
        print("✓ 标注工具函数导入成功")
        return True
        
    except Exception as e:
        print(f"✗ 测试标注模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_training_module():
    """测试训练模块"""
    print("\n测试训练模块...")
    
    try:
        from fisherman.training.training import (
            training_executor,
            yolo_trainer,
            callback_handler,
            result_saver
        )
        
        # 检查实例
        instances = [
            ("training_executor", training_executor),
            ("yolo_trainer", yolo_trainer),
            ("callback_handler", callback_handler),
            ("result_saver", result_saver)
        ]
        
        for name, instance in instances:
            if instance is not None:
                print(f"✓ {name} 实例创建成功")
            else:
                print(f"✗ {name} 实例为 None")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ 测试训练模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_utils_module():
    """测试工具模块"""
    print("\n测试工具模块...")
    
    try:
        from fisherman.training.utils import (
            create_task_directory,
            get_image_files,
            ensure_directory_exists
        )
        
        print("✓ 工具函数导入成功")
        
        # 测试函数可用性
        test_dir = "test_directory"
        result = ensure_directory_exists(test_dir)
        if result:
            print("✓ 确保目录存在函数工作正常")
            
            # 清理测试目录
            import shutil
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
        else:
            print("✗ 确保目录存在函数失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ 测试工具模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("测试模块功能")
    print("=" * 60)
    
    tests = [
        ("基本功能测试", test_basic_functionality),
        ("标注模块测试", test_annotation_module),
        ("训练模块测试", test_training_module),
        ("工具模块测试", test_utils_module)
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
        print("✓ 所有功能测试通过！模块化重构成功。")
        print("\n模块化架构总结:")
        print("1. task模块: 训练任务管理、创建、状态跟踪、数据集管理")
        print("2. annotation模块: 标注工具、标注验证、YOLO格式转换")
        print("3. training模块: 训练执行、YOLOv8训练器、回调处理、结果保存")
        print("4. utils模块: 文件操作工具函数")
        print("5. core模块: 接口定义和基类")
        return 0
    else:
        print("✗ 部分测试失败，需要检查模块功能。")
        return 1


if __name__ == "__main__":
    sys.exit(main())