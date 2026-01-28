import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from screen_capture import ScreenCapture
from object_detector import ObjectDetector
from shake_detector import ShakeDetector
from data_recorder import DataRecorder

print('开始测试各个模块...')

# 测试屏幕捕获
try:
    print('\n测试屏幕捕获模块...')
    screen_capture = ScreenCapture(monitor_index=0, capture_interval=0.1)
    screen_capture.start()
    # 等待一段时间获取屏幕图像
    import time
    time.sleep(1)
    frame = screen_capture.get_frame()
    if frame is not None:
        print(f'成功获取屏幕图像，尺寸: {frame.shape}')
    else:
        print('未能获取屏幕图像')
    screen_capture.stop()
except Exception as e:
    print(f'屏幕捕获测试失败: {e}')

# 测试目标检测
try:
    print('\n测试目标检测模块...')
    detector = ObjectDetector()
    print('YOLO模型加载成功')
except Exception as e:
    print(f'目标检测测试失败: {e}')

# 测试摇晃检测
try:
    print('\n测试摇晃检测模块...')
    shake_detector = ShakeDetector()
    # 模拟物品移动
    for i in range(10):
        position = [100 + i * 5, 200 + i * 3]
        shake_detector.update(1, position)
    # 检查是否检测到摇晃
    is_shaking = shake_detector.check_shake(1)
    print(f'摇晃检测测试完成，检测结果: {is_shaking}')
except Exception as e:
    print(f'摇晃检测测试失败: {e}')

# 测试数据记录
try:
    print('\n测试数据记录模块...')
    recorder = DataRecorder()
    # 记录测试数据
    recorder.record(1, 'test_object', [100, 200], time.time(), is_shaking=True)
    saved_file = recorder.save()
    if saved_file:
        print(f'数据记录测试完成，文件保存到: {saved_file}')
    else:
        print('数据记录测试失败')
except Exception as e:
    print(f'数据记录测试失败: {e}')

print('\n所有模块测试完成！')
