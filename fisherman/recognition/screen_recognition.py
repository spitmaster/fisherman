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
    
    def __init__(self, model_path, confidence_threshold=0.7, click_cooldown=5):
        """初始化屏幕识别
        
        Args:
            model_path: YOLO模型路径
            confidence_threshold: 置信度阈值（0-1）
            click_cooldown: 点击冷却时间（秒）
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.click_cooldown = click_cooldown
        
        # 加载YOLO模型
        try:
            self.model = YOLO(model_path)
            # 强制使用CPU
            import torch
            self.model.to(torch.device("cpu"))
            logger.info(f"YOLO模型加载成功: {model_path} (使用CPU)")
        except Exception as e:
            logger.error(f"YOLO模型加载失败: {str(e)}")
            self.model = None
            
        # 识别任务状态
        self.is_running = False
        self.is_paused = False
        self.thread = None
        
        # 统计信息
        self.recognitions_count = 0
        self.clicks_count = 0
        self.fps = 0
        self.last_click_time = datetime.now()
        
        # 监控区域
        self.monitor_area = None  # (x, y, width, height)
        self.use_full_screen = True
        
        # 结果回调函数
        self.on_recognition_result = None
        self.on_click_event = None
        self.on_error = None
        
        # 初始化屏幕监控
        self.sct = mss.mss()
        
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
        self.last_click_time = datetime.now()
        
        # 创建识别线程
        self.thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.thread.start()
        
        logger.info("识别任务启动成功")
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
        
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
            
        logger.info("识别任务已停止")
        return True
        
    def _recognition_loop(self):
        """识别循环"""
        start_time = datetime.now()
        frame_count = 0
        
        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue
                
            # 计算FPS
            frame_count += 1
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if elapsed_time >= 1:
                self.fps = frame_count / elapsed_time
                frame_count = 0
                start_time = datetime.now()
                
            # 捕获屏幕
            try:
                screenshot = self._capture_screen()
                if screenshot is None:
                    continue
                    
                self.recognitions_count += 1
                
                # 目标检测
                results = self._detect_objects(screenshot)
                
                # 处理检测结果
                if results:
                    self._handle_detection_results(results)
                    
            except Exception as e:
                logger.error(f"识别过程出错: {str(e)}")
                if self.on_error:
                    self.on_error(e)
                    
            # 控制识别频率
            time.sleep(0.05)  # 约20帧/秒
            
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
                device="cpu"  # 强制使用CPU进行推理
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