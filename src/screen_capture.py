import mss
import numpy as np
import cv2
from threading import Thread, Event
import time

class ScreenCapture:
    def __init__(self, monitor_index=0, capture_interval=0.1):
        self.monitor_index = monitor_index
        self.capture_interval = capture_interval
        self.running = False
        self.current_frame = None
        self.stop_event = Event()
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        self.stop_event.set()
        if self.thread:
            self.thread.join()
    
    def _capture_loop(self):
        with mss.mss() as sct:
            monitor = sct.monitors[self.monitor_index]
            while self.running and not self.stop_event.is_set():
                screenshot = sct.grab(monitor)
                img = np.array(screenshot)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                self.current_frame = img
                time.sleep(self.capture_interval)
    
    def get_frame(self):
        return self.current_frame
    
    def get_monitor_info(self):
        with mss.mss() as sct:
            return sct.monitors
