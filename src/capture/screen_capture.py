import time
import numpy as np
from PIL import ImageGrab
import cv2
import pyautogui
import pygetwindow as gw
import mss
import mss.tools

class ScreenCapture:
    """屏幕捕获基类"""
    
    def __init__(self, fps=30):
        self.fps = fps
        self.interval = 1.0 / fps
        self.last_capture_time = 0
        self.is_capturing = False
    
    def capture(self):
        """捕获一帧图像，返回numpy数组 (H, W, C) RGB格式"""
        raise NotImplementedError("子类必须实现此方法")
    
    def start(self):
        """开始捕获"""
        self.is_capturing = True
    
    def stop(self):
        """停止捕获"""
        self.is_capturing = False
    
    def get_frame(self):
        """获取一帧图像，确保帧率控制"""
        current_time = time.time()
        if current_time - self.last_capture_time < self.interval:
            time.sleep(self.interval - (current_time - self.last_capture_time))
        
        frame = self.capture()
        self.last_capture_time = time.time()
        return frame

class FullScreenCapture(ScreenCapture):
    """全屏捕获"""
    
    def __init__(self, fps=30):
        super().__init__(fps)
        self.screen_size = pyautogui.size()
    
    def capture(self):
        # 使用PIL ImageGrab捕获全屏
        screenshot = ImageGrab.grab()
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

class WindowCapture(ScreenCapture):
    """指定窗口捕获"""
    
    def __init__(self, window_title=None, window_handle=None, fps=30):
        super().__init__(fps)
        self.window_title = window_title
        self.window_handle = window_handle
        self.window = None
        self._find_window()
    
    def _find_window(self):
        """查找目标窗口"""
        if self.window_handle:
            # 通过句柄查找窗口
            windows = gw.getAllWindows()
            for win in windows:
                if win._hWnd == self.window_handle:
                    self.window = win
                    break
        elif self.window_title:
            # 通过标题查找窗口
            try:
                self.window = gw.getWindowsWithTitle(self.window_title)[0]
            except (IndexError, Exception):
                raise ValueError(f"未找到标题为'{self.window_title}'的窗口")
        
        if not self.window:
            raise ValueError("无法找到指定窗口")
    
    def capture(self):
        if not self.window:
            self._find_window()
        
        # 获取窗口位置和大小
        left, top, right, bottom = self.window.left, self.window.top, self.window.right, self.window.bottom
        width = right - left
        height = bottom - top
        
        # 使用ImageGrab捕获窗口区域
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame
    
    def update_window(self, window_title=None, window_handle=None):
        """更新目标窗口"""
        if window_title:
            self.window_title = window_title
        if window_handle:
            self.window_handle = window_handle
        self._find_window()

class MssScreenCapture(ScreenCapture):
    """使用mss库进行高效屏幕捕获（适用于高帧率）"""
    
    def __init__(self, monitor=1, fps=30):
        super().__init__(fps)
        self.monitor = monitor
        self.sct = mss.mss()
    
    def capture(self):
        # 获取指定显示器的截图
        monitor_info = self.sct.monitors[self.monitor]
        screenshot = self.sct.grab(monitor_info)
        frame = np.array(screenshot)
        # mss返回BGRA格式，转换为BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame