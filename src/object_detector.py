from ultralytics import YOLO
import cv2
import numpy as np

class ObjectDetector:
    def __init__(self, model_path='yolov8n.pt', confidence_threshold=0.5):
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
    
    def detect(self, frame):
        if frame is None:
            return []
        
        results = self.model(frame)
        detections = []
        
        for result in results:
            for box in result.boxes:
                confidence = box.conf[0].item()
                if confidence >= self.confidence_threshold:
                    class_id = box.cls[0].item()
                    class_name = self.model.names[int(class_id)]
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    width = x2 - x1
                    height = y2 - y1
                    
                    detections.append({
                        'class_id': int(class_id),
                        'class_name': class_name,
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2],
                        'center': [center_x, center_y],
                        'size': [width, height]
                    })
        
        return detections
    
    def draw_detections(self, frame, detections):
        if frame is None:
            return None
        
        annotated_frame = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class_name']
            confidence = detection['confidence']
            
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(annotated_frame, f'{class_name}: {confidence:.2f}', 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        return annotated_frame
