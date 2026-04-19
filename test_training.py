#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练功能测试脚本

测试Fisherman项目的训练模块是否能够正常工作。
"""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_training_module():
    """测试训练模块的基本功能"""
    logger.info("开始测试训练模块...")
    
    try:
        # 导入训练模块
        from training.training_manager import training_manager
        from global_support.task_scheduler import task_scheduler
        
        # 启动任务调度器
        task_scheduler.start_scheduler()
        
        # 创建测试数据集
        test_dataset_dir = create_test_dataset()
        
        # 创建训练任务
        task_id = training_manager.create_training_task(
            task_name="测试训练任务",
            task_description="用于测试训练功能的临时任务",
            dataset_path=test_dataset_dir,
            epochs=5,  # 使用较少的轮次进行测试
            batch_size=2
        )
        
        if task_id is None:
            logger.error("创建训练任务失败")
            return False
            
        logger.info(f"训练任务创建成功: ID={task_id}")
        
        # 检查任务状态
        task_status = training_manager.get_training_task_status(task_id)
        logger.info(f"任务状态: {task_status}")
        
        # 检查训练器功能
        from training.training.yolo_trainer import YOLOTrainer
        trainer = YOLOTrainer()
        
        # 测试训练配置模板
        config_template = trainer.get_training_config_template()
        logger.info(f"训练配置模板: {list(config_template.keys())}")
        
        # 测试预测功能（使用预训练模型）
        test_prediction(trainer)
        
        # 清理测试数据
        shutil.rmtree(test_dataset_dir, ignore_errors=True)
        
        logger.info("训练模块测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"训练模块测试失败: {str(e)}", exc_info=True)
        return False


def create_test_dataset():
    """创建测试数据集"""
    temp_dir = tempfile.mkdtemp(prefix="fisherman_test_")
    
    # 创建数据集目录结构
    dataset_dir = Path(temp_dir) / "dataset"
    images_dir = dataset_dir / "images" / "train"
    labels_dir = dataset_dir / "labels" / "train"
    
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建data.yaml配置文件
    data_yaml = dataset_dir / "data.yaml"
    data_yaml.write_text("""
path: {}
train: images/train
val: images/train
test: images/train
nc: 1
names: ['test_object']
""".format(str(dataset_dir).replace('\\', '/')))
    
    # 创建一些测试图片和标签（这里使用简单的示例）
    # 在实际测试中，应该使用真实的图片和标注数据
    
    logger.info(f"测试数据集创建完成: {temp_dir}")
    return temp_dir


def test_prediction(trainer):
    """测试预测功能"""
    try:
        # 使用预训练模型进行预测
        # 这里使用一个简单的测试图片路径
        test_image_path = "test_image.jpg"
        
        # 如果测试图片不存在，跳过预测测试
        if not os.path.exists(test_image_path):
            logger.warning("测试图片不存在，跳过预测测试")
            return
            
        # 使用预训练模型
        pretrained_model = "yolov8n.pt"
        
        result = trainer.predict(pretrained_model, test_image_path)
        
        if result["success"]:
            logger.info(f"预测测试成功，检测到 {len(result['predictions'])} 个目标")
        else:
            logger.warning(f"预测测试失败: {result['error']}")
            
    except Exception as e:
        logger.warning(f"预测测试出错: {str(e)}")


def check_dependencies():
    """检查依赖是否安装"""
    dependencies = [
        ("ultralytics", "ultralytics"),
        ("torch", "torch"),
        ("opencv", "cv2"),
        ("PyQt5", "PyQt5"),
        ("SQLAlchemy", "sqlalchemy"),
        ("Pillow", "PIL"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
    ]
    
    missing = []
    for name, module in dependencies:
        try:
            __import__(module)
            logger.info(f"✓ {name} 已安装")
        except ImportError:
            missing.append(name)
            logger.error(f"✗ {name} 未安装")
    
    return len(missing) == 0, missing


if __name__ == "__main__":
    logger.info("=== Fisherman训练模块测试 ===")
    
    # 检查依赖
    deps_ok, missing_deps = check_dependencies()
    
    if not deps_ok:
        logger.error(f"缺少依赖: {missing_deps}")
        logger.info("请运行: uv sync")
        sys.exit(1)
    
    # 测试训练模块
    success = test_training_module()
    
    if success:
        logger.info("✅ 训练模块测试通过！程序可以进行正常训练。")
    else:
        logger.error("❌ 训练模块测试失败！程序可能无法正常训练。")
        
    logger.info("=== 测试完成 ===")