# 配置文件

# 检测物品列表
TARGET_OBJECTS = ['hairpin', 'router', 'feather', 'slipper']

# YOLO模型配置
YOLO_CONFIG = {
    'model_path': 'yolov8n.pt',  # 模型路径
    'confidence_threshold': 0.5,  # 置信度阈值
    'iou_threshold': 0.45  # IOU阈值
}

# 屏幕捕获配置
SCREEN_CONFIG = {
    'monitor_index': 0,  # 显示器索引
    'capture_interval': 0.1  # 捕获间隔（秒）
}

# 摇晃检测配置
SHAKE_CONFIG = {
    'history_length': 5,  # 历史位置记录长度
    'distance_threshold': 20,  # 距离阈值（像素）
    'time_window': 1.0  # 时间窗口（秒）
}

# 数据记录配置
RECORDER_CONFIG = {
    'output_dir': 'data'  # 输出目录
}
