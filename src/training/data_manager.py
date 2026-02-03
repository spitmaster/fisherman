import os
import json
import shutil
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from PIL import Image

class DataManager:
    """训练数据管理器"""
    
    def __init__(self, data_dir: str = "train_data"):
        """
        初始化数据管理器
        
        Args:
            data_dir: 训练数据目录
        """
        self.data_dir = data_dir
        self.images_dir = os.path.join(data_dir, "images")
        self.labels_dir = os.path.join(data_dir, "labels")
        self.classes_file = os.path.join(data_dir, "classes.txt")
        
        # 创建目录结构
        self._create_directories()
        
        # 加载类别信息
        self.classes = self._load_classes()
    
    def _create_directories(self):
        """创建必要的目录"""
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)
    
    def _load_classes(self) -> List[str]:
        """加载类别列表"""
        if os.path.exists(self.classes_file):
            with open(self.classes_file, 'r', encoding='utf-8') as f:
                classes = [line.strip() for line in f if line.strip()]
            return classes
        else:
            return []
    
    def save_classes(self, classes: List[str]):
        """保存类别列表"""
        with open(self.classes_file, 'w', encoding='utf-8') as f:
            for class_name in classes:
                f.write(f"{class_name}\n")
        self.classes = classes
    
    def add_class(self, class_name: str) -> int:
        """
        添加新类别
        
        Args:
            class_name: 类别名称
            
        Returns:
            类别ID
        """
        if class_name not in self.classes:
            self.classes.append(class_name)
            self.save_classes(self.classes)
        
        return self.classes.index(class_name)
    
    def import_image(self, image_path: str, copy: bool = True) -> str:
        """
        导入图像到训练数据集
        
        Args:
            image_path: 源图像路径
            copy: 是否复制图像（True为复制，False为移动）
            
        Returns:
            导入后的图像文件名
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        # 生成唯一文件名
        filename = os.path.basename(image_path)
        base_name, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        
        while os.path.exists(os.path.join(self.images_dir, new_filename)):
            new_filename = f"{base_name}_{counter}{ext}"
            counter += 1
        
        dest_path = os.path.join(self.images_dir, new_filename)
        
        if copy:
            shutil.copy2(image_path, dest_path)
        else:
            shutil.move(image_path, dest_path)
        
        return new_filename
    
    def import_images(self, image_paths: List[str], copy: bool = True) -> List[str]:
        """批量导入图像"""
        imported_files = []
        for image_path in image_paths:
            try:
                filename = self.import_image(image_path, copy)
                imported_files.append(filename)
            except Exception as e:
                print(f"导入图像失败 {image_path}: {e}")
        
        return imported_files
    
    def save_annotation(self, image_filename: str, annotations: List[Dict[str, Any]]):
        """
        保存标注信息
        
        Args:
            image_filename: 图像文件名
            annotations: 标注列表，每个标注包含：
                - 'class_id': 类别ID
                - 'bbox': 边界框 [x1, y1, x2, y2] 或 [x_center, y_center, width, height]
                - 'format': 'xyxy' 或 'yolo'（默认'xyxy'）
        """
        # 获取图像尺寸
        image_path = os.path.join(self.images_dir, image_filename)
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        # 使用PIL获取图像尺寸
        with Image.open(image_path) as img:
            img_width, img_height = img.size
        
        # 生成标注文件名（与图像同名，扩展名为.txt）
        base_name = os.path.splitext(image_filename)[0]
        label_filename = f"{base_name}.txt"
        label_path = os.path.join(self.labels_dir, label_filename)
        
        with open(label_path, 'w', encoding='utf-8') as f:
            for ann in annotations:
                class_id = ann.get('class_id', 0)
                bbox = ann.get('bbox', [])
                format_type = ann.get('format', 'xyxy')
                
                if not bbox or len(bbox) != 4:
                    continue
                
                if format_type == 'xyxy':
                    # 转换为YOLO格式（归一化中心坐标和宽高）
                    x1, y1, x2, y2 = bbox
                    x_center = (x1 + x2) / 2 / img_width
                    y_center = (y1 + y2) / 2 / img_height
                    width = (x2 - x1) / img_width
                    height = (y2 - y1) / img_height
                elif format_type == 'yolo':
                    x_center, y_center, width, height = bbox
                else:
                    raise ValueError(f"不支持的边界框格式: {format_type}")
                
                # 写入YOLO格式标注
                line = f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                f.write(line + "\n")
    
    def load_annotation(self, image_filename: str, format_type: str = 'xyxy') -> List[Dict[str, Any]]:
        """
        加载标注信息
        
        Args:
            image_filename: 图像文件名
            format_type: 返回的边界框格式 'xyxy' 或 'yolo'
            
        Returns:
            标注列表
        """
        base_name = os.path.splitext(image_filename)[0]
        label_filename = f"{base_name}.txt"
        label_path = os.path.join(self.labels_dir, label_filename)
        
        if not os.path.exists(label_path):
            return []
        
        # 获取图像尺寸
        image_path = os.path.join(self.images_dir, image_filename)
        with Image.open(image_path) as img:
            img_width, img_height = img.size
        
        annotations = []
        with open(label_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) != 5:
                    continue
                
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                if format_type == 'yolo':
                    bbox = [x_center, y_center, width, height]
                else:  # 'xyxy'
                    x1 = (x_center - width / 2) * img_width
                    y1 = (y_center - height / 2) * img_height
                    x2 = (x_center + width / 2) * img_width
                    y2 = (y_center + height / 2) * img_height
                    bbox = [x1, y1, x2, y2]
                
                annotation = {
                    'class_id': class_id,
                    'class_name': self.classes[class_id] if class_id < len(self.classes) else f"class_{class_id}",
                    'bbox': bbox,
                    'format': format_type
                }
                annotations.append(annotation)
        
        return annotations
    
    def get_image_list(self) -> List[str]:
        """获取所有图像文件名"""
        if not os.path.exists(self.images_dir):
            return []
        
        image_files = []
        for filename in os.listdir(self.images_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                image_files.append(filename)
        
        return sorted(image_files)
    
    def get_annotation_status(self) -> Dict[str, bool]:
        """获取所有图像的标注状态"""
        image_files = self.get_image_list()
        status = {}
        
        for image_file in image_files:
            base_name = os.path.splitext(image_file)[0]
            label_file = f"{base_name}.txt"
            label_path = os.path.join(self.labels_dir, label_file)
            status[image_file] = os.path.exists(label_path)
        
        return status
    
    def split_dataset(self, train_ratio: float = 0.8, val_ratio: float = 0.2):
        """
        分割数据集为训练集和验证集
        
        Args:
            train_ratio: 训练集比例
            val_ratio: 验证集比例
        """
        if train_ratio + val_ratio != 1.0:
            raise ValueError("训练集和验证集比例之和必须为1.0")
        
        image_files = self.get_image_list()
        if not image_files:
            return
        
        # 打乱顺序
        np.random.shuffle(image_files)
        
        # 计算分割点
        train_count = int(len(image_files) * train_ratio)
        train_files = image_files[:train_count]
        val_files = image_files[train_count:]
        
        # 创建数据集配置文件
        self._create_dataset_yaml(train_files, val_files)
    
    def _create_dataset_yaml(self, train_files: List[str], val_files: List[str]):
        """创建数据集YAML配置文件"""
        dataset_yaml = os.path.join(self.data_dir, "dataset.yaml")
        
        # 获取绝对路径
        data_dir_abs = os.path.abspath(self.data_dir)
        
        config = {
            'path': data_dir_abs,
            'train': os.path.join(data_dir_abs, "train.txt"),
            'val': os.path.join(data_dir_abs, "val.txt"),
            'nc': len(self.classes),
            'names': {i: name for i, name in enumerate(self.classes)}
        }
        
        # 写入训练集文件列表
        with open(config['train'], 'w', encoding='utf-8') as f:
            for img_file in train_files:
                img_path = os.path.join(self.images_dir, img_file)
                f.write(f"{img_path}\n")
        
        # 写入验证集文件列表
        with open(config['val'], 'w', encoding='utf-8') as f:
            for img_file in val_files:
                img_path = os.path.join(self.images_dir, img_file)
                f.write(f"{img_path}\n")
        
        # 写入YAML配置文件
        with open(dataset_yaml, 'w', encoding='utf-8') as f:
            f.write(f"path: {config['path']}\n")
            f.write(f"train: {config['train']}\n")
            f.write(f"val: {config['val']}\n")
            f.write(f"nc: {config['nc']}\n")
            f.write("names:\n")
            for i, name in enumerate(self.classes):
                f.write(f"  {i}: {name}\n")
        
        return dataset_yaml
    
    def get_dataset_info(self) -> Dict[str, Any]:
        """获取数据集信息"""
        image_files = self.get_image_list()
        status = self.get_annotation_status()
        
        annotated_count = sum(1 for s in status.values() if s)
        unannotated_count = len(image_files) - annotated_count
        
        return {
            'total_images': len(image_files),
            'annotated_images': annotated_count,
            'unannotated_images': unannotated_count,
            'classes_count': len(self.classes),
            'classes': self.classes.copy()
        }