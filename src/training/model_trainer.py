import os
import time
import yaml
from typing import Dict, Any, Optional, Callable

class ModelTrainer:
    """模型训练器"""
    
    def __init__(self, model_name: str = "custom_object_detector"):
        """
        初始化模型训练器
        
        Args:
            model_name: 模型名称
        """
        self.model_name = model_name
        self.model = None
        self.training_config = self._get_default_config()
        self.training_callback = None
        self.is_training = False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认训练配置"""
        return {
            'epochs': 50,
            'imgsz': 640,
            'batch': 16,
            'workers': 4,
            'device': 'cpu',  # 可以是 'cpu', '0', '0,1,2,3'
            'patience': 10,
            'save': True,
            'save_period': 5,
            'cache': False,
            'project': 'runs/train',
            'name': self.model_name,
            'exist_ok': True,
            'pretrained': True,
            'optimizer': 'auto',
            'verbose': False,
            'seed': 42,
            'deterministic': True,
            'single_cls': False,
            'rect': False,
            'cos_lr': False,
            'close_mosaic': 10,
            'resume': False,
            'amp': True,
            'fraction': 1.0,
            'profile': False,
            'freeze': None,
            'lr0': 0.01,
            'lrf': 0.01,
            'momentum': 0.937,
            'weight_decay': 0.0005,
            'warmup_epochs': 3.0,
            'warmup_momentum': 0.8,
            'warmup_bias_lr': 0.1,
            'box': 7.5,
            'cls': 0.5,
            'dfl': 1.5,
            'pose': 12.0,
            'kobj': 1.0,
            'label_smoothing': 0.0,
            'nbs': 64,
            'overlap_mask': True,
            'mask_ratio': 4,
            'dropout': 0.0,
            'val': True,
            'plots': True
        }
    
    def set_config(self, config: Dict[str, Any]):
        """设置训练配置"""
        self.training_config.update(config)
    
    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置训练回调函数"""
        self.training_callback = callback
    
    def prepare_dataset(self, dataset_yaml_path: str) -> str:
        """
        准备数据集
        
        Args:
            dataset_yaml_path: 数据集YAML配置文件路径
            
        Returns:
            数据集配置路径
        """
        if not os.path.exists(dataset_yaml_path):
            raise FileNotFoundError(f"数据集配置文件不存在: {dataset_yaml_path}")
        
        # 验证YAML文件格式
        with open(dataset_yaml_path, 'r', encoding='utf-8') as f:
            dataset_config = yaml.safe_load(f)
        
        required_keys = ['path', 'train', 'val', 'nc', 'names']
        for key in required_keys:
            if key not in dataset_config:
                raise ValueError(f"数据集配置文件缺少必要的键: {key}")
        
        return dataset_yaml_path
    
    def train(self, dataset_yaml_path: str, base_model: str = 'yolov8n.pt') -> Dict[str, Any]:
        """
        训练模型
        
        Args:
            dataset_yaml_path: 数据集YAML配置文件路径
            base_model: 基础模型路径或名称
            
        Returns:
            训练结果
        """
        if self.is_training:
            raise RuntimeError("训练正在进行中")
        
        self.is_training = True
        
        try:
            # 准备数据集
            dataset_yaml_path = self.prepare_dataset(dataset_yaml_path)
            
            # 延迟导入YOLO
            from ultralytics import YOLO
            
            # 加载模型
            if os.path.exists(base_model):
                self.model = YOLO(base_model)
            else:
                # 使用预训练模型
                self.model = YOLO(base_model)
            
            # 准备训练参数
            train_args = self.training_config.copy()
            train_args['data'] = dataset_yaml_path
            
            # 添加回调函数包装器
            if self.training_callback:
                original_train = self.model.train
                
                def train_with_callback(**kwargs):
                    result = original_train(**kwargs)
                    if self.training_callback:
                        self.training_callback({'status': 'training_completed', 'result': result})
                    return result
                
                self.model.train = train_with_callback
            
            # 开始训练
            start_time = time.time()
            
            if self.training_callback:
                self.training_callback({'status': 'training_started', 'config': train_args})
            
            results = self.model.train(**train_args)
            
            end_time = time.time()
            training_time = end_time - start_time
            
            # 获取最佳模型路径
            best_model_path = self.model.trainer.best if hasattr(self.model.trainer, 'best') else None
            if not best_model_path and hasattr(self.model.trainer, 'save_dir'):
                # 尝试在保存目录中查找最佳模型
                save_dir = self.model.trainer.save_dir
                weights_dir = os.path.join(save_dir, 'weights')
                if os.path.exists(weights_dir):
                    best_model = os.path.join(weights_dir, 'best.pt')
                    if os.path.exists(best_model):
                        best_model_path = best_model
            
            # 收集训练结果
            result = {
                'status': 'completed',
                'success': True,
                'training_time': training_time,
                'results': results,
                'best_model_path': best_model_path,
                'config': train_args
            }
            
            if self.training_callback:
                self.training_callback({'status': 'training_completed', 'result': result})
            
            return result
            
        except Exception as e:
            error_result = {
                'status': 'failed',
                'success': False,
                'error': str(e),
                'training_time': time.time() - start_time if 'start_time' in locals() else 0
            }
            
            if self.training_callback:
                self.training_callback({'status': 'training_failed', 'error': str(e)})
            
            raise e
        
        finally:
            self.is_training = False
    
    def resume_training(self, checkpoint_path: str) -> Dict[str, Any]:
        """
        从检查点恢复训练
        
        Args:
            checkpoint_path: 检查点文件路径
            
        Returns:
            训练结果
        """
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"检查点文件不存在: {checkpoint_path}")
        
        # 加载检查点
        from ultralytics import YOLO
        self.model = YOLO(checkpoint_path)
        
        # 更新配置以恢复训练
        resume_config = self.training_config.copy()
        resume_config['resume'] = True
        
        # 开始训练
        return self.train(resume_config)
    
    def validate(self, model_path: str, dataset_yaml_path: str) -> Dict[str, Any]:
        """
        验证模型
        
        Args:
            model_path: 模型文件路径
            dataset_yaml_path: 数据集YAML配置文件路径
            
        Returns:
            验证结果
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        # 加载模型
        from ultralytics import YOLO
        model = YOLO(model_path)
        
        # 验证数据集
        dataset_yaml_path = self.prepare_dataset(dataset_yaml_path)
        
        # 运行验证
        results = model.val(data=dataset_yaml_path)
        
        # 提取验证指标
        metrics = {}
        if hasattr(results, 'box'):
            metrics['map50'] = results.box.map50
            metrics['map50_95'] = results.box.map
            metrics['precision'] = results.box.p
            metrics['recall'] = results.box.r
        
        return {
            'success': True,
            'metrics': metrics,
            'results': results
        }
    
    def export_model(self, model_path: str, format: str = 'onnx') -> str:
        """
        导出模型为其他格式
        
        Args:
            model_path: 模型文件路径
            format: 导出格式，如 'onnx', 'torchscript', 'tflite', 'coreml', 'saved_model'
            
        Returns:
            导出模型路径
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        from ultralytics import YOLO
        model = YOLO(model_path)
        
        # 导出模型
        exported_path = model.export(format=format)
        
        return exported_path
    
    def get_training_progress(self) -> Optional[Dict[str, Any]]:
        """获取训练进度"""
        if not self.is_training or not hasattr(self.model, 'trainer'):
            return None
        
        trainer = self.model.trainer
        
        progress = {
            'epoch': getattr(trainer, 'epoch', 0),
            'epochs': getattr(trainer, 'epochs', 0),
            'iter': getattr(trainer, 'iter', 0),
            'nl': getattr(trainer, 'nl', 0),
            'progress': 0.0
        }
        
        if progress['epochs'] > 0:
            progress['progress'] = progress['epoch'] / progress['epochs']
        
        # 获取损失值
        if hasattr(trainer, 'loss_names'):
            loss_names = trainer.loss_names
            losses = {}
            for loss_name in loss_names:
                loss_value = getattr(trainer, f'{loss_name}_loss', None)
                if loss_value is not None:
                    losses[loss_name] = float(loss_value)
            progress['losses'] = losses
        
        # 获取学习率
        if hasattr(trainer, 'optimizer'):
            optimizer = trainer.optimizer
            if optimizer and hasattr(optimizer, 'param_groups'):
                lr = optimizer.param_groups[0].get('lr', 0)
                progress['learning_rate'] = float(lr)
        
        return progress
    
    def stop_training(self):
        """停止训练"""
        if self.is_training and hasattr(self.model, 'trainer'):
            # Ultralytics目前没有直接的停止训练API
            # 这里我们设置一个标志，在回调中处理
            self.is_training = False
            if self.training_callback:
                self.training_callback({'status': 'training_stopped'})