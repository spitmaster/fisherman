import cv2
import time
import sys
import os

# 添加项目根目录到导入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screen_capture import ScreenCapture
from object_detector import ObjectDetector
from shake_detector import ShakeDetector
from data_recorder import DataRecorder
from config.config import TARGET_OBJECTS, YOLO_CONFIG, SCREEN_CONFIG, SHAKE_CONFIG, RECORDER_CONFIG

class ScreenMonitor:
    def __init__(self):
        # 初始化组件
        self.screen_capture = ScreenCapture(
            monitor_index=SCREEN_CONFIG['monitor_index'],
            capture_interval=SCREEN_CONFIG['capture_interval']
        )
        
        self.object_detector = ObjectDetector(
            model_path=YOLO_CONFIG['model_path'],
            confidence_threshold=YOLO_CONFIG['confidence_threshold']
        )
        
        self.shake_detector = ShakeDetector(
            history_length=SHAKE_CONFIG['history_length'],
            distance_threshold=SHAKE_CONFIG['distance_threshold'],
            time_window=SHAKE_CONFIG['time_window']
        )
        
        self.data_recorder = DataRecorder(output_dir=RECORDER_CONFIG['output_dir'])
        
        self.running = False
        self.object_counter = 0
        self.object_ids = {}
        self.gui = None  # GUI实例
    
    def start(self):
        print('开始屏幕监控...')
        print(f'目标检测物品: {TARGET_OBJECTS}')
        
        self.running = True
        self.screen_capture.start()
        
        try:
            while self.running:
                # 获取屏幕图像
                frame = self.screen_capture.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                
                # 检测物品
                detections = self.object_detector.detect(frame)
                
                # 处理检测结果
                for detection in detections:
                    class_name = detection['class_name']
                    # 只处理目标物品
                    if class_name not in TARGET_OBJECTS:
                        continue
                    
                    # 为物品分配ID
                    object_key = f'{class_name}_{detection["center"][0]}_{detection["center"][1]}'
                    if object_key not in self.object_ids:
                        self.object_ids[object_key] = self.object_counter
                        self.object_counter += 1
                    
                    object_id = self.object_ids[object_key]
                    position = detection['center']
                    timestamp = time.time()
                    
                    # 更新摇晃检测器
                    self.shake_detector.update(object_id, position)
                    
                    # 检查是否摇晃
                    is_shaking = self.shake_detector.check_shake(object_id)
                    
                    # 记录数据
                    self.data_recorder.record(
                        object_id=object_id,
                        object_name=class_name,
                        position=position,
                        timestamp=timestamp,
                        is_shaking=is_shaking
                    )
                    
                    # 如果摇晃，打印消息并发送到GUI
                    if is_shaking:
                        message = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] 检测到 {class_name} 摇晃！位置: {position}'
                        print(message)
                        # 如果有GUI实例，更新信息
                        if hasattr(self, 'gui') and self.gui:
                            self.gui.update_info(message)
                
                # 每10秒保存一次数据
                if int(time.time()) % 10 == 0:
                    saved_file = self.data_recorder.save()
                    if saved_file:
                        print(f'数据已保存到: {saved_file}')
                
                # 显示结果
                annotated_frame = self.object_detector.draw_detections(frame, detections)
                # 尝试显示结果，但捕获可能的OpenCV错误
                try:
                    if annotated_frame is not None:
                        cv2.imshow('Screen Monitor', annotated_frame)
                        
                        # 按ESC键退出
                        if cv2.waitKey(1) == 27:
                            break
                except cv2.error as e:
                    # 如果OpenCV无法显示窗口，跳过显示步骤
                    print('警告: OpenCV无法显示窗口，将只在控制台输出结果')
                    # 只打印一次警告
                    if not hasattr(self, 'show_warning'):
                        self.show_warning = True
                        print(f'错误详情: {e}')
                
        except KeyboardInterrupt:
            print('\n监控已手动停止')
        finally:
            self.stop()
    
    def stop(self):
        print('停止屏幕监控...')
        self.running = False
        self.screen_capture.stop()
        
        # 保存剩余数据
        saved_file = self.data_recorder.save()
        if saved_file:
            print(f'最终数据已保存到: {saved_file}')
        
        # 尝试销毁窗口，但捕获可能的OpenCV错误
        try:
            cv2.destroyAllWindows()
        except cv2.error as e:
            # 如果OpenCV无法销毁窗口，跳过此步骤
            pass
        
        print('监控已停止')

if __name__ == '__main__':
    monitor = ScreenMonitor()
    monitor.start()
