import threading
import time
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from capture.screen_capture import ScreenCapture, FullScreenCapture, WindowCapture
from detection.shake_detector import ShakeDetector
from storage.data_storage import DataStorage

class Monitor:
    """监控管理器"""
    
    def __init__(self):
        self.capture = None
        self.detector = None
        self.shake_detector = None
        self.storage = DataStorage()
        
        self.is_monitoring = False
        self.monitor_thread = None
        self.frame_count = 0
        self.frame_skip = 1  # 跳帧检测，1表示每帧都检测
        self.detection_interval = 0  # 检测间隔（秒）
        self.last_detection_time = 0
        
        self.callback = None
        self.preview_callback = None
        
        # 监控参数
        self.monitor_params = {
            'capture_type': 'fullscreen',  # 'fullscreen', 'window'
            'window_title': '',
            'model_path': None,
            'confidence_threshold': 0.5,
            'class_filter': [],
            'shake_threshold': 5.0,
            'fps': 30,
            'frame_skip': 1,
            'detection_interval': 0.1
        }
    
    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置回调函数"""
        self.callback = callback
    
    def set_preview_callback(self, callback: Callable[[np.ndarray], None]):
        """设置预览回调函数"""
        self.preview_callback = callback
    
    def set_params(self, params: Dict[str, Any]):
        """设置监控参数"""
        self.monitor_params.update(params)
        
        # 更新组件参数
        if self.detector:
            self.detector.set_confidence_threshold(params.get('confidence_threshold', 0.5))
        
        if self.shake_detector:
            self.shake_detector.displacement_threshold = params.get('shake_threshold', 5.0)
    
    def setup_capture(self):
        """设置捕获器"""
        capture_type = self.monitor_params.get('capture_type', 'fullscreen')
        fps = self.monitor_params.get('fps', 30)
        
        if capture_type == 'fullscreen':
            self.capture = FullScreenCapture(fps=fps)
        elif capture_type == 'window':
            window_title = self.monitor_params.get('window_title', '')
            if not window_title:
                raise ValueError("窗口捕获需要指定窗口标题")
            self.capture = WindowCapture(window_title=window_title, fps=fps)
        else:
            raise ValueError(f"不支持的捕获类型: {capture_type}")
    
    def setup_detector(self):
        """设置检测器"""
        from detection.yolo_detector import YOLODetector
        
        model_path = self.monitor_params.get('model_path')
        confidence_threshold = self.monitor_params.get('confidence_threshold', 0.5)
        
        self.detector = YOLODetector(model_path=model_path, 
                                    confidence_threshold=confidence_threshold)
        
        # 设置晃动检测器
        shake_threshold = self.monitor_params.get('shake_threshold', 5.0)
        self.shake_detector = ShakeDetector(displacement_threshold=shake_threshold)
        
        # 更新帧跳过和检测间隔
        self.frame_skip = self.monitor_params.get('frame_skip', 1)
        self.detection_interval = self.monitor_params.get('detection_interval', 0.1)
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            return
        
        # 设置组件
        self.setup_capture()
        self.setup_detector()
        
        # 启动监控线程
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        if self.callback:
            self.callback({'status': 'monitoring_started', 'params': self.monitor_params})
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
            self.monitor_thread = None
        
        # 清理资源
        if self.capture:
            self.capture.stop()
        
        if self.callback:
            self.callback({'status': 'monitoring_stopped'})
    
    def _monitoring_loop(self):
        """监控循环"""
        self.frame_count = 0
        self.last_detection_time = time.time()
        
        while self.is_monitoring:
            try:
                # 捕获帧
                frame = self.capture.get_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                current_time = time.time()
                
                # 检查是否需要进行检测
                should_detect = (
                    self.frame_count % self.frame_skip == 0 and
                    current_time - self.last_detection_time >= self.detection_interval
                )
                
                detections = []
                shake_detections = []
                
                if should_detect:
                    # 运行物体检测
                    class_filter = self.monitor_params.get('class_filter', [])
                    if class_filter:
                        detections = self.detector.detect_custom(frame, class_filter)
                    else:
                        detections = self.detector.detect(frame)
                    
                    # 运行晃动检测
                    shake_detections = self.shake_detector.update_detections(detections)
                    
                    # 保存检测记录
                    for detection in shake_detections:
                        self.storage.save_detection_record(detection, self.frame_count)
                    
                    # 检查晃动事件
                    shake_events = self.shake_detector.get_shake_events(recent_only=True)
                    for event in shake_events:
                        if 'end_time' not in event:
                            # 这是一个新的晃动事件
                            self.storage.save_shake_event(event)
                    
                    self.last_detection_time = current_time
                
                # 发送预览帧
                if self.preview_callback:
                    preview_frame = self._create_preview_frame(frame, shake_detections)
                    self.preview_callback(preview_frame)
                
                # 发送状态更新
                if self.callback and should_detect:
                    status_update = {
                        'status': 'monitoring_update',
                        'frame_count': self.frame_count,
                        'detection_count': len(detections),
                        'shake_count': len([d for d in shake_detections if d.get('shake_status', False)]),
                        'detections': shake_detections,
                        'timestamp': current_time
                    }
                    self.callback(status_update)
                
                self.frame_count += 1
                
            except Exception as e:
                print(f"监控循环错误: {e}")
                if self.callback:
                    self.callback({'status': 'monitoring_error', 'error': str(e)})
                time.sleep(0.1)
    
    def _create_preview_frame(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """创建预览帧，绘制检测框和晃动状态"""
        preview = frame.copy()
        
        for detection in detections:
            bbox = detection.get('bbox', [])
            class_name = detection.get('class_name', '')
            confidence = detection.get('confidence', 0)
            shake_status = detection.get('shake_status', False)
            tracking_id = detection.get('tracking_id', -1)
            
            if len(bbox) == 4:
                x1, y1, x2, y2 = map(int, bbox)
                
                # 根据晃动状态选择颜色
                if shake_status:
                    color = (0, 0, 255)  # 红色表示晃动
                else:
                    color = (0, 255, 0)  # 绿色表示静止
                
                # 绘制边界框
                cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
                
                # 绘制标签
                label = f"{class_name} {confidence:.2f}"
                if tracking_id >= 0:
                    label = f"ID:{tracking_id} {label}"
                
                # 标签背景
                label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(preview, (x1, y1 - label_size[1] - 5), 
                            (x1 + label_size[0], y1), color, -1)
                
                # 标签文本
                cv2.putText(preview, label, (x1, y1 - 5), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # 绘制中心点
                center = detection.get('center', (0, 0))
                if center:
                    cx, cy = map(int, center)
                    cv2.circle(preview, (cx, cy), 3, color, -1)
        
        # 添加状态信息
        status_text = f"帧: {self.frame_count} 检测: {len(detections)} 晃动: {sum(1 for d in detections if d.get('shake_status', False))}"
        cv2.putText(preview, status_text, (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return preview
    
    def get_shake_events(self, recent_only: bool = True) -> List[Dict[str, Any]]:
        """获取晃动事件"""
        if self.shake_detector:
            return self.shake_detector.get_shake_events(recent_only)
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.storage.get_statistics()
        
        # 添加运行时统计
        stats.update({
            'frame_count': self.frame_count,
            'is_monitoring': self.is_monitoring,
            'monitor_params': self.monitor_params.copy()
        })
        
        return stats
    
    def export_data(self, export_format: str = 'csv', file_path: str = None):
        """导出数据"""
        if not file_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if export_format == 'csv':
                file_path = f"shake_events_{timestamp}.csv"
            else:
                file_path = f"shake_events_{timestamp}.json"
        
        if export_format == 'csv':
            self.storage.export_to_csv(file_path)
        else:
            self.storage.export_to_json(file_path)
        
        return file_path
    
    def get_window_list(self) -> List[Dict[str, Any]]:
        """获取窗口列表"""
        import pygetwindow as gw
        
        windows = []
        for win in gw.getAllWindows():
            if win.title:  # 只包括有标题的窗口
                windows.append({
                    'title': win.title,
                    'handle': win._hWnd,
                    'position': (win.left, win.top, win.right, win.bottom)
                })
        
        return windows