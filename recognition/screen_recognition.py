#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别模块 - 屏幕识别

负责监控电脑屏幕、识别特定物体并自动触发鼠标点击。

主要功能：
- 屏幕截图和区域监控
- 使用YOLO模型进行目标检测
- 自动鼠标点击操作
- 识别任务管理
- 实时监控和统计
"""

import os
import sys
import logging
import time
import threading
import mss
import mss.tools
import numpy as np
import cv2
import pyautogui
from datetime import datetime, timedelta
from ultralytics import YOLO

# 日志配置
logger = logging.getLogger(__name__)

class ScreenRecognition:
    """屏幕识别类"""
    
    def __init__(self, model_path, confidence_threshold=0.7, click_cooldown=5, click_enabled=True, device="cpu"):
        """初始化屏幕识别

        Args:
            model_path: YOLO模型路径
            confidence_threshold: 置信度阈值（0-1）
            click_cooldown: 点击冷却时间（秒）
            click_enabled: 是否启用自动点击（测试模式下设为 False）
            device: 推理设备，如 "cpu" / "cuda:0"
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.click_cooldown = click_cooldown
        self.click_enabled = click_enabled
        self.device = device

        # 加载YOLO模型
        try:
            self.model = YOLO(model_path)
            logger.info(f"YOLO模型加载成功: {model_path} (设备: {device})")
        except Exception as e:
            logger.error(f"YOLO模型加载失败: {str(e)}")
            self.model = None
            
        # 识别任务状态
        self.is_running = False
        self.is_paused = False
        # 截图与推理解耦:两条独立线程
        self._capture_thread = None
        self._inference_thread = None

        # 统计信息
        self.recognitions_count = 0
        self.clicks_count = 0
        self.fps = 0           # 推理 FPS(YOLO 一秒能跑几次)
        self.preview_fps = 0   # 预览 FPS(截图/UI 一秒能刷几次)
        self.last_click_time = datetime.now()
        
        # 监控区域
        self.monitor_area = None  # (x, y, width, height)
        self.use_full_screen = True
        
        # 结果回调函数
        self.on_recognition_result = None
        self.on_frame_result = None  # (frame_bgr, detections) — 需要可视化时订阅
        self.on_click_event = None
        self.on_error = None

        # 预览帧率上限。30 对人眼足够顺滑,再高基本无收益、白吃 CPU
        self.preview_fps_cap = 30

        # 截图线程与推理线程之间的共享槽:
        # _latest_frame 由截图线程写、推理 + 预览读;_latest_detections 由推理线程写、预览读。
        # GIL 保证引用赋值原子,且每帧是新 ndarray、检测结果是新 list,所以不用 Lock。
        self._latest_frame = None
        self._latest_detections = []

        # mss 实例必须在使用它的线程创建(内部用 threading.local 存 GDI device context),
        # 跨线程访问会抛 "_thread._local object has no attribute 'srcdc'"。
        # 真正实例在 _capture_loop 里建。
        self.sct = None
        
    def set_monitor_area(self, x, y, width, height):
        """设置监控区域
        
        Args:
            x: 起始X坐标
            y: 起始Y坐标
            width: 宽度
            height: 高度
        """
        self.monitor_area = (x, y, width, height)
        self.use_full_screen = False
        logger.info(f"监控区域设置为: {x}, {y}, {width}, {height}")
        
    def use_full_screen_monitor(self):
        """使用全屏监控"""
        self.use_full_screen = True
        self.monitor_area = None
        logger.info("监控区域设置为: 全屏")
        
    def start_recognition(self):
        """开始识别任务"""
        if self.model is None:
            logger.error("无法开始识别任务：模型未加载")
            return False
            
        if self.is_running:
            logger.warning("识别任务已经在运行中")
            return False
            
        self.is_running = True
        self.is_paused = False
        self.recognitions_count = 0
        self.clicks_count = 0
        self.fps = 0
        self.preview_fps = 0
        self._latest_frame = None
        self._latest_detections = []
        self.last_click_time = datetime.now()

        # 双线程:截图/预览高频跑(~30 FPS),推理按 YOLO 实际速度跑(CPU ~10 FPS)
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._capture_thread.start()
        self._inference_thread.start()

        logger.info("识别任务启动成功(截图 + 推理双线程)")
        return True
        
    def pause_recognition(self):
        """暂停识别任务"""
        if not self.is_running:
            logger.warning("识别任务未在运行中")
            return False
            
        self.is_paused = True
        logger.info("识别任务已暂停")
        return True
        
    def resume_recognition(self):
        """恢复识别任务"""
        if not self.is_running:
            logger.warning("识别任务未在运行中")
            return False
            
        self.is_paused = False
        logger.info("识别任务已恢复")
        return True
        
    def stop_recognition(self):
        """停止识别任务"""
        if not self.is_running:
            logger.warning("识别任务未在运行中")
            return False
            
        self.is_running = False
        self.is_paused = False

        if self._capture_thread:
            self._capture_thread.join(timeout=1)
            self._capture_thread = None
        if self._inference_thread:
            self._inference_thread.join(timeout=1)
            self._inference_thread = None

        logger.info("识别任务已停止")
        return True
        
    def _capture_loop(self):
        """截图 + 预览线程。
        与推理解耦,所以即使 YOLO 一秒只跑 5 次,这里仍可以跑到 preview_fps_cap(默认 30 FPS)。
        每一轮:截图 → 写入共享 _latest_frame(供推理线程消费)→ emit on_frame_result(叠加推理线程
        最近一次的检测框,可能略滞后但不影响预览顺滑)。
        """
        # mss 必须在当前线程实例化(threading.local 限制)
        self.sct = mss.mss()
        target_interval = 1.0 / max(self.preview_fps_cap, 1)
        capture_start = datetime.now()
        capture_count = 0

        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue

            t0 = time.time()
            try:
                screenshot = self._capture_screen()
                if screenshot is None:
                    time.sleep(0.1)
                    continue

                # 写入共享槽给推理线程(GIL 原子,无需 Lock)
                self._latest_frame = screenshot

                # 统计预览 FPS
                capture_count += 1
                elapsed = (datetime.now() - capture_start).total_seconds()
                if elapsed >= 1:
                    self.preview_fps = capture_count / elapsed
                    capture_count = 0
                    capture_start = datetime.now()

                # emit 预览:叠加推理线程最近一次的检测结果(copy 一份,防下游枚举到一半被覆盖)
                if self.on_frame_result is not None:
                    try:
                        self.on_frame_result(screenshot, list(self._latest_detections))
                    except Exception as emit_err:
                        logger.error(f"帧回调出错: {emit_err}")

            except Exception as e:
                logger.error(f"截图循环出错: {str(e)}")
                if self.on_error:
                    self.on_error(e)

            # 节流到 preview_fps_cap,避免无谓的 CPU 占用
            elapsed = time.time() - t0
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)

    def _inference_loop(self):
        """推理线程。
        从 _latest_frame 拿最新一帧跑 YOLO,慢但稳定;推理结果写回 _latest_detections。
        与截图解耦,推理多慢都不会拖慢预览。
        """
        start_time = datetime.now()
        frame_count = 0

        # 等首帧到达再开始,避免空跑
        while self.is_running and self._latest_frame is None:
            time.sleep(0.02)

        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue

            # 拿最新一帧的引用快照(GIL 保证赋值原子;每次 mss.grab 返回新 ndarray,不存在"读到一半"问题)
            frame = self._latest_frame
            if frame is None:
                time.sleep(0.05)
                continue

            try:
                self.recognitions_count += 1

                # 统计推理 FPS(每秒能跑几次 YOLO)
                frame_count += 1
                elapsed_time = (datetime.now() - start_time).total_seconds()
                if elapsed_time >= 1:
                    self.fps = frame_count / elapsed_time
                    frame_count = 0
                    start_time = datetime.now()

                results = self._detect_objects(frame)
                # 写回检测结果给截图线程当下一次预览的叠加层
                self._latest_detections = results or []

                if results:
                    self._handle_detection_results(results)

            except Exception as e:
                logger.error(f"识别过程出错: {str(e)}")
                if self.on_error:
                    self.on_error(e)
            
    def _capture_screen(self):
        """捕获屏幕截图
        
        Returns:
            屏幕截图的numpy数组，BGR格式
        """
        try:
            if self.use_full_screen:
                # 全屏捕获
                monitor = self.sct.monitors[1]
            else:
                # 区域捕获
                x, y, width, height = self.monitor_area
                monitor = {
                    "top": y,
                    "left": x,
                    "width": width,
                    "height": height
                }
                
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            return img
            
        except Exception as e:
            logger.error(f"屏幕捕获出错: {str(e)}")
            return None
            
    def _detect_objects(self, image):
        """使用YOLO模型检测目标
        
        Args:
            image: 输入图像（BGR格式）
            
        Returns:
            检测结果列表
        """
        try:
            results = self.model.predict(
                source=image,
                conf=self.confidence_threshold,
                verbose=False,
                device=self.device,
            )
            
            detections = []
            
            for result in results:
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes
                    
                    for box in boxes:
                        # 获取边界框坐标
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        # 获取置信度
                        confidence = box.conf[0].cpu().numpy()
                        # 获取类别ID
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # 计算中心点坐标
                        center_x = int((x1 + x2) / 2)
                        center_y = int((y1 + y2) / 2)
                        
                        # 获取类别名称
                        class_name = result.names[class_id] if hasattr(result, 'names') else str(class_id)
                        
                        detections.append({
                            "bbox": (x1, y1, x2, y2),
                            "center": (center_x, center_y),
                            "confidence": confidence,
                            "class_id": class_id,
                            "class_name": class_name
                        })
                        
            return detections
            
        except Exception as e:
            logger.error(f"目标检测出错: {str(e)}")
            return []
            
    def _handle_detection_results(self, detections):
        """处理检测结果
        
        Args:
            detections: 检测结果列表
        """
        if self.on_recognition_result:
            self.on_recognition_result(detections)

        # 测试模式下禁用点击
        if not self.click_enabled:
            return

        # 检查是否需要点击
        current_time = datetime.now()
        if (current_time - self.last_click_time) >= timedelta(seconds=self.click_cooldown):
            # 计算最佳点击位置
            target_position = self._get_best_target_position(detections)

            if target_position:
                self._click_target(target_position)
                
    def _get_best_target_position(self, detections):
        """获取最佳目标位置
        
        Args:
            detections: 检测结果列表
            
        Returns:
            最佳点击位置 (x, y)
        """
        if not detections:
            return None
            
        # 简单策略：选择置信度最高的目标
        best_detection = max(detections, key=lambda x: x["confidence"])
        return best_detection["center"]
        
    def _click_target(self, position):
        """点击目标位置
        
        Args:
            position: 目标位置 (x, y)
        """
        try:
            # 计算实际屏幕坐标（如果是区域捕获）
            click_x, click_y = position
            if not self.use_full_screen:
                click_x += self.monitor_area[0]
                click_y += self.monitor_area[1]
                
            # 执行鼠标点击
            pyautogui.click(x=click_x, y=click_y)
            self.clicks_count += 1
            self.last_click_time = datetime.now()
            
            logger.info(f"自动点击: ({click_x}, {click_y})")
            
            if self.on_click_event:
                self.on_click_event(click_x, click_y)
                
        except Exception as e:
            logger.error(f"鼠标点击出错: {str(e)}")
            
    def get_statistics(self):
        """获取识别统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "recognitions_count": self.recognitions_count,
            "clicks_count": self.clicks_count,
            "fps": self.fps,
            "preview_fps": self.preview_fps,
            "last_click_time": self.last_click_time,
            "confidence_threshold": self.confidence_threshold,
            "click_cooldown": self.click_cooldown,
            "model_path": self.model_path
        }

    def set_confidence_threshold(self, threshold):
        """设置置信度阈值
        
        Args:
            threshold: 置信度阈值（0-1）
        """
        if 0 <= threshold <= 1:
            self.confidence_threshold = threshold
            logger.info(f"置信度阈值设置为: {threshold}")
            return True
            
        logger.warning("置信度阈值必须在0-1范围内")
        return False
        
    def set_click_cooldown(self, cooldown):
        """设置点击冷却时间
        
        Args:
            cooldown: 点击冷却时间（秒）
        """
        if cooldown > 0:
            self.click_cooldown = cooldown
            logger.info(f"点击冷却时间设置为: {cooldown}秒")
            return True
            
        logger.warning("点击冷却时间必须大于0")
        return False
        
    def get_model_info(self):
        """获取模型信息
        
        Returns:
            模型信息字典
        """
        if not self.model:
            return None
            
        try:
            # 获取模型基本信息
            model_info = {
                "path": self.model_path,
                "class_names": list(self.model.names.values()),
                "num_classes": len(self.model.names)
            }
            
            return model_info
            
        except Exception as e:
            logger.error(f"获取模型信息出错: {str(e)}")
            return None
            
class RecognitionManager:
    """识别管理器"""
    
    def __init__(self):
        """初始化识别管理器"""
        self.active_recognition = None
        
    def create_recognition_task(self, model_path, confidence_threshold=0.7, click_cooldown=5):
        """创建识别任务
        
        Args:
            model_path: 模型路径
            confidence_threshold: 置信度阈值
            click_cooldown: 点击冷却时间
            
        Returns:
            识别任务实例
        """
        try:
            recognition = ScreenRecognition(
                model_path,
                confidence_threshold,
                click_cooldown
            )
            
            return recognition
            
        except Exception as e:
            logger.error(f"创建识别任务出错: {str(e)}")
            return None
            
    def start_recognition_task(self, model_path, confidence_threshold=0.7, click_cooldown=5):
        """启动识别任务
        
        Args:
            model_path: 模型路径
            confidence_threshold: 置信度阈值
            click_cooldown: 点击冷却时间
            
        Returns:
            识别任务实例
        """
        # 停止之前的任务
        if self.active_recognition:
            self.stop_recognition_task()
            
        # 创建新任务
        self.active_recognition = self.create_recognition_task(
            model_path,
            confidence_threshold,
            click_cooldown
        )
        
        if self.active_recognition:
            self.active_recognition.start_recognition()
            logger.info(f"识别任务启动成功: {model_path}")
            
        return self.active_recognition
        
    def stop_recognition_task(self):
        """停止当前识别任务"""
        if self.active_recognition:
            self.active_recognition.stop_recognition()
            self.active_recognition = None
            logger.info("当前识别任务已停止")
            
    def pause_recognition_task(self):
        """暂停当前识别任务"""
        if self.active_recognition:
            self.active_recognition.pause_recognition()
            
    def resume_recognition_task(self):
        """恢复当前识别任务"""
        if self.active_recognition:
            self.active_recognition.resume_recognition()
            
    def get_active_recognition(self):
        """获取当前活动的识别任务
        
        Returns:
            识别任务实例或None
        """
        return self.active_recognition
        
    def is_recognition_active(self):
        """检查识别任务是否正在运行
        
        Returns:
            识别任务是否正在运行
        """
        if self.active_recognition:
            return self.active_recognition.is_running
            
        return False
        
    def get_statistics(self):
        """获取识别统计信息
        
        Returns:
            统计信息字典
        """
        if self.active_recognition:
            return self.active_recognition.get_statistics()
            
        return {
            "is_running": False,
            "is_paused": False,
            "recognitions_count": 0,
            "clicks_count": 0,
            "fps": 0,
            "preview_fps": 0,
            "last_click_time": None,
            "confidence_threshold": 0.7,
            "click_cooldown": 5,
            "model_path": None
        }
        
    def test_model(self, model_path):
        """测试模型是否可加载
        
        Args:
            model_path: 模型路径
            
        Returns:
            测试结果
        """
        try:
            model = YOLO(model_path)
            logger.info(f"模型测试成功: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"模型测试失败: {str(e)}")
            return False
            
# 全局识别管理器实例
recognition_manager = RecognitionManager()