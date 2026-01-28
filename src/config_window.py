from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QGroupBox, QGridLayout, QCheckBox, QSpinBox, QDoubleSpinBox, QMessageBox
from PyQt5.QtCore import Qt
import os
import sys
import json

# 添加项目根目录到导入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ConfigWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('配置设置')
        self.setGeometry(200, 200, 800, 600)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 创建目标物品配置区域
        objects_group = QGroupBox('目标检测物品')
        objects_layout = QVBoxLayout()
        
        # 物品列表
        self.objects_list = QListWidget()
        objects_layout.addWidget(self.objects_list)
        
        # 添加/删除物品按钮
        buttons_layout = QHBoxLayout()
        self.object_input = QLineEdit()
        self.object_input.setPlaceholderText('输入物品名称')
        add_button = QPushButton('添加')
        remove_button = QPushButton('删除')
        
        add_button.clicked.connect(self.add_object)
        remove_button.clicked.connect(self.remove_object)
        
        buttons_layout.addWidget(self.object_input)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(remove_button)
        
        objects_layout.addLayout(buttons_layout)
        objects_group.setLayout(objects_layout)
        
        # 创建YOLO配置区域
        yolo_group = QGroupBox('YOLO模型配置')
        yolo_layout = QGridLayout()
        
        yolo_layout.addWidget(QLabel('模型路径:'), 0, 0)
        self.model_path = QLineEdit('yolov8n.pt')
        yolo_layout.addWidget(self.model_path, 0, 1)
        
        yolo_layout.addWidget(QLabel('置信度阈值:'), 1, 0)
        self.conf_threshold = QDoubleSpinBox()
        self.conf_threshold.setRange(0.1, 1.0)
        self.conf_threshold.setValue(0.5)
        self.conf_threshold.setSingleStep(0.1)
        yolo_layout.addWidget(self.conf_threshold, 1, 1)
        
        yolo_group.setLayout(yolo_layout)
        
        # 创建屏幕捕获配置区域
        screen_group = QGroupBox('屏幕捕获配置')
        screen_layout = QGridLayout()
        
        screen_layout.addWidget(QLabel('显示器索引:'), 0, 0)
        self.monitor_index = QSpinBox()
        self.monitor_index.setRange(0, 10)
        self.monitor_index.setValue(0)
        screen_layout.addWidget(self.monitor_index, 0, 1)
        
        screen_layout.addWidget(QLabel('捕获间隔(秒):'), 1, 0)
        self.capture_interval = QDoubleSpinBox()
        self.capture_interval.setRange(0.01, 1.0)
        self.capture_interval.setValue(0.1)
        self.capture_interval.setSingleStep(0.01)
        screen_layout.addWidget(self.capture_interval, 1, 1)
        
        screen_group.setLayout(screen_layout)
        
        # 创建摇晃检测配置区域
        shake_group = QGroupBox('摇晃检测配置')
        shake_layout = QGridLayout()
        
        shake_layout.addWidget(QLabel('历史位置记录长度:'), 0, 0)
        self.history_length = QSpinBox()
        self.history_length.setRange(2, 20)
        self.history_length.setValue(5)
        shake_layout.addWidget(self.history_length, 0, 1)
        
        shake_layout.addWidget(QLabel('距离阈值(像素):'), 1, 0)
        self.distance_threshold = QSpinBox()
        self.distance_threshold.setRange(5, 100)
        self.distance_threshold.setValue(20)
        shake_layout.addWidget(self.distance_threshold, 1, 1)
        
        shake_group.setLayout(shake_layout)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        save_button = QPushButton('保存配置')
        cancel_button = QPushButton('取消')
        
        save_button.clicked.connect(self.save_config)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        # 添加所有组件到主布局
        main_layout.addWidget(objects_group)
        main_layout.addWidget(yolo_group)
        main_layout.addWidget(screen_group)
        main_layout.addWidget(shake_group)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 加载现有配置
        self.load_config()
    
    def load_config(self):
        # 加载配置文件
        try:
            from config.config import TARGET_OBJECTS, YOLO_CONFIG, SCREEN_CONFIG, SHAKE_CONFIG
            
            # 加载目标物品
            for obj in TARGET_OBJECTS:
                item = QListWidgetItem(obj)
                self.objects_list.addItem(item)
            
            # 加载YOLO配置
            self.model_path.setText(YOLO_CONFIG['model_path'])
            self.conf_threshold.setValue(YOLO_CONFIG['confidence_threshold'])
            
            # 加载屏幕捕获配置
            self.monitor_index.setValue(SCREEN_CONFIG['monitor_index'])
            self.capture_interval.setValue(SCREEN_CONFIG['capture_interval'])
            
            # 加载摇晃检测配置
            self.history_length.setValue(SHAKE_CONFIG['history_length'])
            self.distance_threshold.setValue(SHAKE_CONFIG['distance_threshold'])
        except Exception as e:
            QMessageBox.warning(self, '警告', f'加载配置失败: {e}')
    
    def add_object(self):
        obj_name = self.object_input.text().strip()
        if obj_name:
            item = QListWidgetItem(obj_name)
            self.objects_list.addItem(item)
            self.object_input.clear()
    
    def remove_object(self):
        selected_items = self.objects_list.selectedItems()
        for item in selected_items:
            self.objects_list.takeItem(self.objects_list.row(item))
    
    def save_config(self):
        # 收集配置信息
        objects = [self.objects_list.item(i).text() for i in range(self.objects_list.count())]
        
        config = {
            'TARGET_OBJECTS': objects,
            'YOLO_CONFIG': {
                'model_path': self.model_path.text(),
                'confidence_threshold': self.conf_threshold.value(),
                'iou_threshold': 0.45
            },
            'SCREEN_CONFIG': {
                'monitor_index': self.monitor_index.value(),
                'capture_interval': self.capture_interval.value()
            },
            'SHAKE_CONFIG': {
                'history_length': self.history_length.value(),
                'distance_threshold': self.distance_threshold.value(),
                'time_window': 1.0
            }
        }
        
        # 保存配置到文件
        try:
            config_content = f"""# 配置文件

# 检测物品列表
TARGET_OBJECTS = {config['TARGET_OBJECTS']}

# YOLO模型配置
YOLO_CONFIG = {
    'model_path': '{config['YOLO_CONFIG']['model_path']}',  # 模型路径
    'confidence_threshold': {config['YOLO_CONFIG']['confidence_threshold']},  # 置信度阈值
    'iou_threshold': {config['YOLO_CONFIG']['iou_threshold']}  # IOU阈值
}

# 屏幕捕获配置
SCREEN_CONFIG = {
    'monitor_index': {config['SCREEN_CONFIG']['monitor_index']},  # 显示器索引
    'capture_interval': {config['SCREEN_CONFIG']['capture_interval']}  # 捕获间隔（秒）
}

# 摇晃检测配置
SHAKE_CONFIG = {
    'history_length': {config['SHAKE_CONFIG']['history_length']},  # 历史位置记录长度
    'distance_threshold': {config['SHAKE_CONFIG']['distance_threshold']},  # 距离阈值（像素）
    'time_window': {config['SHAKE_CONFIG']['time_window']}  # 时间窗口（秒）
}

# 数据记录配置
RECORDER_CONFIG = {
    'output_dir': 'data'  # 输出目录
}
"""
            
            with open('config/config.py', 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            QMessageBox.information(self, '信息', '配置保存成功')
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, '警告', f'保存配置失败: {e}')
