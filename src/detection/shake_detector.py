import numpy as np
from typing import List, Dict, Any, Tuple
from collections import deque
import time

class ObjectTracker:
    """单个物体跟踪器"""
    
    def __init__(self, object_id: int, initial_position: Tuple[float, float], 
                 max_history: int = 30):
        """
        初始化物体跟踪器
        
        Args:
            object_id: 物体唯一ID
            initial_position: 初始位置 (x, y)
            max_history: 最大历史记录长度
        """
        self.object_id = object_id
        self.position_history = deque(maxlen=max_history)
        self.position_history.append(initial_position)
        self.last_update_time = time.time()
        self.shake_count = 0
        self.last_shake_time = 0
        self.is_shaking = False
    
    def update_position(self, position: Tuple[float, float]):
        """更新物体位置"""
        self.position_history.append(position)
        self.last_update_time = time.time()
    
    def get_current_position(self) -> Tuple[float, float]:
        """获取当前位置"""
        return self.position_history[-1]
    
    def get_position_history(self) -> List[Tuple[float, float]]:
        """获取位置历史"""
        return list(self.position_history)
    
    def get_displacement(self) -> float:
        """计算最近位移（与历史平均位置的偏差）"""
        if len(self.position_history) < 2:
            return 0.0
        
        recent_positions = list(self.position_history)[-5:] if len(self.position_history) >= 5 else list(self.position_history)
        current_pos = np.array(self.position_history[-1])
        avg_pos = np.mean([np.array(p) for p in recent_positions], axis=0)
        
        displacement = np.linalg.norm(current_pos - avg_pos)
        return displacement
    
    def get_velocity(self) -> float:
        """计算当前速度"""
        if len(self.position_history) < 2:
            return 0.0
        
        pos1 = np.array(self.position_history[-2])
        pos2 = np.array(self.position_history[-1])
        time_diff = 1.0  # 假设每帧时间间隔为1个单位
        
        velocity = np.linalg.norm(pos2 - pos1) / time_diff
        return velocity
    
    def get_acceleration(self) -> float:
        """计算当前加速度"""
        if len(self.position_history) < 3:
            return 0.0
        
        pos1 = np.array(self.position_history[-3])
        pos2 = np.array(self.position_history[-2])
        pos3 = np.array(self.position_history[-1])
        time_diff = 1.0  # 假设每帧时间间隔为1个单位
        
        v1 = (pos2 - pos1) / time_diff
        v2 = (pos3 - pos2) / time_diff
        
        acceleration = np.linalg.norm(v2 - v1) / time_diff
        return acceleration

class ShakeDetector:
    """物体晃动检测器"""
    
    def __init__(self, 
                 displacement_threshold: float = 5.0,
                 velocity_threshold: float = 10.0,
                 acceleration_threshold: float = 20.0,
                 min_shake_duration: float = 0.3,
                 max_shake_interval: float = 1.0):
        """
        初始化晃动检测器
        
        Args:
            displacement_threshold: 位移阈值（像素）
            velocity_threshold: 速度阈值（像素/帧）
            acceleration_threshold: 加速度阈值（像素/帧²）
            min_shake_duration: 最小晃动持续时间（秒）
            max_shake_interval: 最大晃动间隔（秒）
        """
        self.displacement_threshold = displacement_threshold
        self.velocity_threshold = velocity_threshold
        self.acceleration_threshold = acceleration_threshold
        self.min_shake_duration = min_shake_duration
        self.max_shake_interval = max_shake_interval
        
        self.object_trackers: Dict[int, ObjectTracker] = {}
        self.next_object_id = 0
        self.shake_events = []
    
    def update_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        更新检测结果并跟踪物体
        
        Args:
            detections: 当前帧的检测结果列表
            
        Returns:
            更新后的检测结果列表，添加了tracking_id和shake_status
        """
        current_time = time.time()
        
        # 如果没有检测到物体，清理跟踪器
        if not detections:
            self._cleanup_old_trackers(current_time)
            return []
        
        # 为每个检测分配或匹配跟踪器
        updated_detections = []
        matched_tracker_ids = set()
        
        for detection in detections:
            center = detection['center']
            bbox = detection['bbox']
            
            # 尝试匹配现有跟踪器
            matched_id = self._match_tracker(center, bbox)
            
            if matched_id is not None:
                # 更新现有跟踪器
                tracker = self.object_trackers[matched_id]
                tracker.update_position(center)
                matched_tracker_ids.add(matched_id)
                
                # 检查晃动状态
                shake_status = self._check_shake(tracker, current_time)
                
                updated_detection = detection.copy()
                updated_detection['tracking_id'] = matched_id
                updated_detection['shake_status'] = shake_status
                updated_detection['displacement'] = tracker.get_displacement()
                updated_detection['velocity'] = tracker.get_velocity()
                updated_detection['acceleration'] = tracker.get_acceleration()
                
                updated_detections.append(updated_detection)
            else:
                # 创建新跟踪器
                tracker_id = self.next_object_id
                tracker = ObjectTracker(tracker_id, center)
                self.object_trackers[tracker_id] = tracker
                matched_tracker_ids.add(tracker_id)
                self.next_object_id += 1
                
                updated_detection = detection.copy()
                updated_detection['tracking_id'] = tracker_id
                updated_detection['shake_status'] = False
                updated_detection['displacement'] = 0.0
                updated_detection['velocity'] = 0.0
                updated_detection['acceleration'] = 0.0
                
                updated_detections.append(updated_detection)
        
        # 清理未匹配的跟踪器
        self._cleanup_unmatched_trackers(matched_tracker_ids, current_time)
        
        return updated_detections
    
    def _match_tracker(self, center: Tuple[float, float], bbox: List[float]) -> int:
        """
        匹配现有跟踪器
        
        Args:
            center: 检测框中心点
            bbox: 检测框坐标 [x1, y1, x2, y2]
            
        Returns:
            匹配的跟踪器ID，如果没有匹配则返回None
        """
        if not self.object_trackers:
            return None
        
        center_np = np.array(center)
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]
        
        # 使用边界框对角线长度的一半作为匹配阈值
        match_threshold = np.sqrt(bbox_width**2 + bbox_height**2) * 0.5
        
        best_match_id = None
        min_distance = float('inf')
        
        for tracker_id, tracker in self.object_trackers.items():
            tracker_pos = np.array(tracker.get_current_position())
            distance = np.linalg.norm(center_np - tracker_pos)
            
            if distance < match_threshold and distance < min_distance:
                min_distance = distance
                best_match_id = tracker_id
        
        return best_match_id
    
    def _check_shake(self, tracker: ObjectTracker, current_time: float) -> bool:
        """
        检查物体是否在晃动
        
        Args:
            tracker: 物体跟踪器
            current_time: 当前时间
            
        Returns:
            是否在晃动
        """
        # 检查位移、速度、加速度是否超过阈值
        displacement = tracker.get_displacement()
        velocity = tracker.get_velocity()
        acceleration = tracker.get_acceleration()
        
        is_shaking = (displacement > self.displacement_threshold or
                     velocity > self.velocity_threshold or
                     acceleration > self.acceleration_threshold)
        
        # 更新晃动状态
        if is_shaking and not tracker.is_shaking:
            # 开始晃动
            tracker.is_shaking = True
            tracker.shake_count += 1
            tracker.last_shake_time = current_time
            
            # 记录晃动事件
            shake_event = {
                'tracker_id': tracker.object_id,
                'start_time': current_time,
                'position': tracker.get_current_position(),
                'displacement': displacement,
                'velocity': velocity,
                'acceleration': acceleration
            }
            self.shake_events.append(shake_event)
            
        elif not is_shaking and tracker.is_shaking:
            # 停止晃动
            tracker.is_shaking = False
            
            # 更新最近晃动事件的结束时间
            if self.shake_events:
                last_event = self.shake_events[-1]
                if last_event['tracker_id'] == tracker.object_id and 'end_time' not in last_event:
                    last_event['end_time'] = current_time
        
        return tracker.is_shaking
    
    def _cleanup_unmatched_trackers(self, matched_ids: set, current_time: float):
        """清理未匹配的跟踪器"""
        tracker_ids = list(self.object_trackers.keys())
        for tracker_id in tracker_ids:
            if tracker_id not in matched_ids:
                # 如果跟踪器长时间未更新，则移除
                tracker = self.object_trackers[tracker_id]
                if current_time - tracker.last_update_time > 5.0:  # 5秒未更新
                    del self.object_trackers[tracker_id]
    
    def _cleanup_old_trackers(self, current_time: float):
        """清理所有旧的跟踪器"""
        tracker_ids = list(self.object_trackers.keys())
        for tracker_id in tracker_ids:
            tracker = self.object_trackers[tracker_id]
            if current_time - tracker.last_update_time > 5.0:  # 5秒未更新
                del self.object_trackers[tracker_id]
    
    def get_shake_events(self, recent_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取晃动事件
        
        Args:
            recent_only: 是否只返回最近的事件
            
        Returns:
            晃动事件列表
        """
        if not self.shake_events:
            return []
        
        if recent_only:
            current_time = time.time()
            recent_events = []
            for event in reversed(self.shake_events):
                if 'end_time' in event:
                    if current_time - event['end_time'] < 60.0:  # 最近60秒内
                        recent_events.append(event)
                else:
                    recent_events.append(event)
            return list(reversed(recent_events))
        
        return self.shake_events.copy()
    
    def reset_shake_events(self):
        """重置晃动事件记录"""
        self.shake_events.clear()