# 屏幕监控软件

## 项目概述

这是一个基于YOLO目标检测的屏幕监控软件，用于检测屏幕上出现的特定物品（如发卡、路由器、羽毛、拖鞋等），并当物品发生摇晃时记录其位置信息和摇晃时间点。

## 功能特点

- 自动屏幕捕获，定期获取屏幕图像
- 使用YOLOv8模型进行目标检测
- 支持自定义检测物品列表
- 实时检测物品摇晃情况
- 自动记录物品位置和摇晃时间
- 可视化显示检测结果

## 安装说明

### 1. 克隆项目

```bash
git clone <项目地址>
cd fisherman
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 下载YOLO模型

第一次运行时，系统会自动下载YOLOv8模型文件（yolov8n.pt）。

## 配置说明

### 配置文件位置

`config/config.py`

### 可配置项

1. **检测物品列表**
   ```python
   TARGET_OBJECTS = ['hairpin', 'router', 'feather', 'slipper']
   ```

2. **YOLO模型配置**
   ```python
   YOLO_CONFIG = {
       'model_path': 'yolov8n.pt',  # 模型路径
       'confidence_threshold': 0.5,  # 置信度阈值
       'iou_threshold': 0.45  # IOU阈值
   }
   ```

3. **屏幕捕获配置**
   ```python
   SCREEN_CONFIG = {
       'monitor_index': 0,  # 显示器索引
       'capture_interval': 0.1  # 捕获间隔（秒）
   }
   ```

4. **摇晃检测配置**
   ```python
   SHAKE_CONFIG = {
       'history_length': 5,  # 历史位置记录长度
       'distance_threshold': 20,  # 距离阈值（像素）
       'time_window': 1.0  # 时间窗口（秒）
   }
   ```

5. **数据记录配置**
   ```python
   RECORDER_CONFIG = {
       'output_dir': 'data'  # 输出目录
   }
   ```

## 使用方法

### 运行命令行版本

```bash
python src/main.py
```

### 运行图形化界面版本

```bash
python src/main_gui.py
```

### 命令行版本操作说明

1. 程序启动后会自动开始屏幕监控
2. 检测到目标物品时，会在屏幕上显示 bounding box
3. 当物品发生摇晃时，会在控制台打印摇晃信息
4. 数据会每10秒自动保存到 `data` 目录下的CSV文件
5. 按 `ESC` 键退出程序

### 图形化界面操作说明

1. **主窗口**：
   - 左侧显示监控画面，实时展示屏幕内容和检测结果
   - 右侧显示识别信息，包括物品名称、位置和摇晃状态
   - 顶部有控制按钮：开始监控、停止监控、配置、模型训练

2. **配置页面**：
   - 目标检测物品：添加或删除需要检测的物品
   - YOLO模型配置：设置模型路径和置信度阈值
   - 屏幕捕获配置：设置显示器索引和捕获间隔
   - 摇晃检测配置：设置历史记录长度和距离阈值

3. **模型训练页面**：
   - 选择标注数据目录（需包含 data.yaml 配置文件）
   - 设置训练参数：基础模型、训练轮数、批量大小、图像尺寸
   - 点击开始训练按钮启动模型训练
   - 训练过程中会显示训练日志和进度条

## 模型训练说明

由于YOLOv8n模型可能无法识别一些特定物品（如发卡、羽毛等），需要使用标注好的图片进行模型微调：

1. **数据准备**：
   - 收集包含目标物品的图片
   - 使用标注工具（如 LabelImg）对图片进行标注
   - 创建 data.yaml 配置文件，指定训练集和验证集路径

2. **模型训练**：
   - 在图形化界面中打开模型训练页面
   - 选择标注数据目录
   - 设置训练参数
   - 点击开始训练按钮

3. **模型使用**：
   - 训练完成后，在 runs/train/exp/weights 目录下找到训练好的模型
   - 在配置页面中设置模型路径为训练好的模型路径
   - 重新启动监控程序

## 数据记录格式

CSV文件包含以下字段：

- `timestamp`: 时间戳
- `datetime`: 格式化的日期时间
- `object_id`: 物品ID
- `object_name`: 物品名称
- `position_x`: 物品X坐标
- `position_y`: 物品Y坐标
- `is_shaking`: 是否摇晃

## 常见问题

### 1. 检测不到物品

- 检查物品是否在 `TARGET_OBJECTS` 列表中
- 调整 `confidence_threshold` 阈值
- 确保物品在屏幕上清晰可见

### 2. 摇晃检测不灵敏

- 调整 `distance_threshold` 阈值
- 调整 `history_length` 参数

### 3. 性能问题

- 可以使用更轻量级的YOLO模型（如yolov8n.pt）
- 增加 `capture_interval` 间隔时间

## 技术栈

- Python 3.8+
- OpenCV
- Ultralytics YOLOv8
- MSS (屏幕捕获)
- NumPy
- Pandas

## 许可证

MIT
