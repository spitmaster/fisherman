import numpy as np
import cv2
from typing import List, Tuple, Dict, Any

class YOLODetector:
    """YOLO物体检测器"""
    
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.5):
        """
        初始化YOLO检测器
        
        Args:
            model_path: 模型文件路径，如果为None则使用预训练模型
            confidence_threshold: 置信度阈值
        """
        self.confidence_threshold = confidence_threshold
        self.model_path = model_path
        self.model = None
        
    def _lazy_init(self):
        """延迟初始化YOLO模型"""
        if self.model is None:
            from ultralytics import YOLO
            if self.model_path:
                self.model = YOLO(self.model_path)
            else:
                # 使用预训练的YOLOv8n模型
                self.model = YOLO('yolov8n.pt')
    
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        检测图像中的物体
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            检测结果列表，每个元素为包含以下键的字典：
            - 'bbox': 边界框 [x1, y1, x2, y2]
            - 'confidence': 置信度
            - 'class_id': 类别ID
            - 'class_name': 类别名称
            - 'center': 中心点坐标 (x, y)
        """
        self._lazy_init()
        
        # 将BGR转换为RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 运行推理
        results = self.model(image_rgb, conf=self.confidence_threshold, verbose=False)
        
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # 获取边界框坐标
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = self.model.names[class_id]
                    
                    # 计算中心点
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    detection = {
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                        'confidence': float(confidence),
                        'class_id': class_id,
                        'class_name': class_name,
                        'center': (float(center_x), float(center_y))
                    }
                    detections.append(detection)
        
        return detections
    
    def detect_custom(self, image: np.ndarray, class_filter: List[str] = None) -> List[Dict[str, Any]]:
        """
        检测自定义类别的物体
        
        Args:
            image: 输入图像
            class_filter: 要检测的类别名称列表，如果为None则检测所有类别
            
        Returns:
            检测结果列表
        """
        all_detections = self.detect(image)
        
        if class_filter is None:
            return all_detections
        
        # 过滤指定类别的检测结果
        filtered_detections = []
        for detection in all_detections:
            if detection['class_name'] in class_filter:
                filtered_detections.append(detection)
        
        return filtered_detections
    
    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值"""
        self.confidence_threshold = threshold
    
    def load_model(self, model_path: str):
        """加载自定义模型"""
        from ultralytics import YOLO
        self.model_path = model_path
        self.model = YOLO(model_path)