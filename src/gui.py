from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel, QGroupBox, QGridLayout, QListWidget, QListWidgetItem, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
import cv2
import numpy as np
import os
import sys

# 添加项目根目录到导入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MainWindow(QMainWindow):
    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        # 将GUI实例传递给monitor
        self.monitor.gui = self
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('屏幕监控系统')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部控制栏
        control_layout = QHBoxLayout()
        self.start_button = QPushButton('开始监控')
        self.stop_button = QPushButton('停止监控')
        self.config_button = QPushButton('配置')
        self.train_button = QPushButton('模型训练')
        
        self.start_button.clicked.connect(self.start_monitoring)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.config_button.clicked.connect(self.open_config)
        self.train_button.clicked.connect(self.open_train)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.config_button)
        control_layout.addWidget(self.train_button)
        
        main_layout.addLayout(control_layout)
        
        # 创建中间内容区域
        content_layout = QHBoxLayout()
        
        # 创建左侧监控区域
        monitor_group = QGroupBox('监控画面')
        monitor_layout = QVBoxLayout()
        self.monitor_label = QLabel()
        self.monitor_label.setFixedSize(800, 600)
        self.monitor_label.setAlignment(Qt.AlignCenter)
        monitor_layout.addWidget(self.monitor_label)
        monitor_group.setLayout(monitor_layout)
        
        # 创建右侧信息区域
        info_group = QGroupBox('识别信息')
        info_layout = QVBoxLayout()
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        info_group.setLayout(info_layout)
        
        content_layout.addWidget(monitor_group)
        content_layout.addWidget(info_group)
        
        main_layout.addLayout(content_layout)
        
        # 创建底部状态栏
        self.status_label = QLabel('就绪')
        main_layout.addWidget(self.status_label)
        
        # 创建定时器，用于更新监控画面
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_monitor)
    
    def start_monitoring(self):
        if not self.monitor.running:
            self.monitor.start()
            self.timer.start(100)  # 每100毫秒更新一次
            self.status_label.setText('监控中...')
            QMessageBox.information(self, '信息', '监控已开始')
    
    def stop_monitoring(self):
        if self.monitor.running:
            self.monitor.stop()
            self.timer.stop()
            self.status_label.setText('已停止')
            QMessageBox.information(self, '信息', '监控已停止')
    
    def open_config(self):
        # 打开配置窗口
        from config_window import ConfigWindow
        config_window = ConfigWindow(self)
        config_window.exec_()
    
    def open_train(self):
        # 打开模型训练窗口
        from train_window import TrainWindow
        train_window = TrainWindow(self)
        train_window.exec_()
    
    def update_monitor(self):
        # 更新监控画面
        if hasattr(self.monitor, 'screen_capture') and self.monitor.screen_capture:
            frame = self.monitor.screen_capture.get_frame()
            if frame is not None:
                # 绘制检测结果
                if hasattr(self.monitor, 'object_detector') and self.monitor.object_detector:
                    detections = self.monitor.object_detector.detect(frame)
                    annotated_frame = self.monitor.object_detector.draw_detections(frame, detections)
                else:
                    annotated_frame = frame
                
                # 转换为Qt图像
                height, width, channel = annotated_frame.shape
                bytes_per_line = 3 * width
                q_image = QImage(annotated_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                self.monitor_label.setPixmap(pixmap.scaled(self.monitor_label.size(), Qt.KeepAspectRatio))
    
    def update_info(self, info):
        # 更新识别信息
        self.info_text.append(info)
