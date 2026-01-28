import numpy as np
from collections import deque
import time

class ShakeDetector:
    def __init__(self, history_length=5, distance_threshold=20, time_window=1.0):
        self.history_length = history_length
        self.distance_threshold = distance_threshold
        self.time_window = time_window
        self.object_history = {}
    
    def update(self, object_id, position):
        if object_id not in self.object_history:
            self.object_history[object_id] = deque(maxlen=self.history_length)
        
        timestamp = time.time()
        self.object_history[object_id].append((timestamp, position))
    
    def check_shake(self, object_id):
        if object_id not in self.object_history or len(self.object_history[object_id]) < 2:
            return False
        
        # 计算最近位置与上一位置的距离
        recent_positions = [pos for _, pos in self.object_history[object_id]]
        current_pos = recent_positions[-1]
        prev_pos = recent_positions[-2]
        
        distance = np.sqrt((current_pos[0] - prev_pos[0])**2 + (current_pos[1] - prev_pos[1])**2)
        
        # 检查是否超过距离阈值
        if distance > self.distance_threshold:
            return True
        
        return False
    
    def get_recent_movement(self, object_id):
        if object_id not in self.object_history or len(self.object_history[object_id]) < 2:
            return 0.0
        
        recent_positions = [pos for _, pos in self.object_history[object_id]]
        total_movement = 0.0
        
        for i in range(1, len(recent_positions)):
            prev_pos = recent_positions[i-1]
            current_pos = recent_positions[i]
            distance = np.sqrt((current_pos[0] - prev_pos[0])**2 + (current_pos[1] - prev_pos[1])**2)
            total_movement += distance
        
        return total_movement
    
    def reset(self, object_id=None):
        if object_id:
            if object_id in self.object_history:
                del self.object_history[object_id]
        else:
            self.object_history.clear()
