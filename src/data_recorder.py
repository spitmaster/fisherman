import pandas as pd
import os
from datetime import datetime

class DataRecorder:
    def __init__(self, output_dir='data'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.data = []
    
    def record(self, object_id, object_name, position, timestamp, is_shaking=False):
        record = {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f'),
            'object_id': object_id,
            'object_name': object_name,
            'position_x': position[0],
            'position_y': position[1],
            'is_shaking': is_shaking
        }
        self.data.append(record)
    
    def save(self, filename=None):
        if not self.data:
            return
        
        if filename is None:
            filename = f'shake_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv'
        
        filepath = os.path.join(self.output_dir, filename)
        df = pd.DataFrame(self.data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        # 清空数据
        self.data = []
        return filepath
    
    def get_current_data(self):
        return self.data
    
    def clear(self):
        self.data = []
