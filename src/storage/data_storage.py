import sqlite3
import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Any

class DataStorage:
    """数据存储管理器"""
    
    def __init__(self, db_path: str = "detection_data.db"):
        """
        初始化数据存储
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建检测事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shake_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tracking_id INTEGER,
                start_time REAL,
                end_time REAL,
                duration REAL,
                position_x REAL,
                position_y REAL,
                displacement REAL,
                velocity REAL,
                acceleration REAL,
                bbox TEXT,
                confidence REAL,
                class_name TEXT,
                additional_info TEXT
            )
        ''')
        
        # 创建检测记录表（每帧检测结果）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detection_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                frame_index INTEGER,
                tracking_id INTEGER,
                position_x REAL,
                position_y REAL,
                bbox TEXT,
                confidence REAL,
                class_name TEXT,
                shake_status BOOLEAN,
                displacement REAL,
                velocity REAL,
                acceleration REAL
            )
        ''')
        
        # 创建模型信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_shake_event(self, event_data: Dict[str, Any]):
        """
        保存晃动事件
        
        Args:
            event_data: 晃动事件数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 计算持续时间
        duration = None
        if 'end_time' in event_data and 'start_time' in event_data:
            duration = event_data['end_time'] - event_data['start_time']
        
        # 提取位置信息
        position_x, position_y = event_data.get('position', (0, 0))
        
        cursor.execute('''
            INSERT INTO shake_events (
                tracking_id, start_time, end_time, duration,
                position_x, position_y, displacement, velocity, acceleration,
                bbox, confidence, class_name, additional_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_data.get('tracker_id'),
            event_data.get('start_time'),
            event_data.get('end_time'),
            duration,
            position_x,
            position_y,
            event_data.get('displacement', 0),
            event_data.get('velocity', 0),
            event_data.get('acceleration', 0),
            json.dumps(event_data.get('bbox', [])),
            event_data.get('confidence', 0),
            event_data.get('class_name', ''),
            json.dumps(event_data.get('additional_info', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def save_detection_record(self, detection_data: Dict[str, Any], frame_index: int):
        """
        保存单帧检测记录
        
        Args:
            detection_data: 检测数据
            frame_index: 帧索引
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        position_x, position_y = detection_data.get('center', (0, 0))
        
        cursor.execute('''
            INSERT INTO detection_records (
                frame_index, tracking_id, position_x, position_y,
                bbox, confidence, class_name, shake_status,
                displacement, velocity, acceleration
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            frame_index,
            detection_data.get('tracking_id'),
            position_x,
            position_y,
            json.dumps(detection_data.get('bbox', [])),
            detection_data.get('confidence', 0),
            detection_data.get('class_name', ''),
            detection_data.get('shake_status', False),
            detection_data.get('displacement', 0),
            detection_data.get('velocity', 0),
            detection_data.get('acceleration', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def save_model_info(self, name: str, path: str, description: str = ""):
        """
        保存模型信息
        
        Args:
            name: 模型名称
            path: 模型文件路径
            description: 模型描述
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO model_info (name, path, description)
            VALUES (?, ?, ?)
        ''', (name, path, description))
        
        conn.commit()
        conn.close()
    
    def get_shake_events(self, start_time: datetime = None, end_time: datetime = None, 
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取晃动事件
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回记录数限制
            
        Returns:
            晃动事件列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM shake_events WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        events = []
        for row in rows:
            event = dict(row)
            # 解析JSON字段
            event['bbox'] = json.loads(event['bbox']) if event['bbox'] else []
            event['additional_info'] = json.loads(event['additional_info']) if event['additional_info'] else {}
            events.append(event)
        
        conn.close()
        return events
    
    def get_detection_records(self, tracking_id: int = None, frame_index: int = None,
                             limit: int = 1000) -> List[Dict[str, Any]]:
        """
        获取检测记录
        
        Args:
            tracking_id: 跟踪ID
            frame_index: 帧索引
            limit: 返回记录数限制
            
        Returns:
            检测记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM detection_records WHERE 1=1"
        params = []
        
        if tracking_id is not None:
            query += " AND tracking_id = ?"
            params.append(tracking_id)
        
        if frame_index is not None:
            query += " AND frame_index = ?"
            params.append(frame_index)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            record = dict(row)
            record['bbox'] = json.loads(record['bbox']) if record['bbox'] else []
            records.append(record)
        
        conn.close()
        return records
    
    def get_model_info(self) -> List[Dict[str, Any]]:
        """获取所有模型信息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM model_info ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        models = [dict(row) for row in rows]
        conn.close()
        return models
    
    def export_to_csv(self, file_path: str, start_time: datetime = None, 
                     end_time: datetime = None):
        """
        导出晃动事件到CSV文件
        
        Args:
            file_path: CSV文件路径
            start_time: 开始时间
            end_time: 结束时间
        """
        events = self.get_shake_events(start_time, end_time, limit=10000)
        
        if not events:
            return
        
        # 确定CSV字段
        fieldnames = [
            'id', 'timestamp', 'tracking_id', 'start_time', 'end_time', 'duration',
            'position_x', 'position_y', 'displacement', 'velocity', 'acceleration',
            'confidence', 'class_name'
        ]
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for event in events:
                # 只写入基本字段
                row = {field: event.get(field, '') for field in fieldnames}
                writer.writerow(row)
    
    def export_to_json(self, file_path: str, start_time: datetime = None,
                      end_time: datetime = None):
        """
        导出晃动事件到JSON文件
        
        Args:
            file_path: JSON文件路径
            start_time: 开始时间
            end_time: 结束时间
        """
        events = self.get_shake_events(start_time, end_time, limit=10000)
        
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(events, jsonfile, ensure_ascii=False, indent=2, default=str)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # 总晃动事件数
        cursor.execute("SELECT COUNT(*) FROM shake_events")
        stats['total_events'] = cursor.fetchone()[0]
        
        # 今日事件数
        cursor.execute("SELECT COUNT(*) FROM shake_events WHERE DATE(timestamp) = DATE('now')")
        stats['today_events'] = cursor.fetchone()[0]
        
        # 平均持续时间
        cursor.execute("SELECT AVG(duration) FROM shake_events WHERE duration IS NOT NULL")
        avg_duration = cursor.fetchone()[0]
        stats['avg_duration'] = avg_duration if avg_duration else 0
        
        # 不同类别的统计
        cursor.execute("SELECT class_name, COUNT(*) FROM shake_events GROUP BY class_name")
        stats['events_by_class'] = dict(cursor.fetchall())
        
        conn.close()
        return stats