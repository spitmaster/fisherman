#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练模块 - 标注导出器

负责将标注数据导出为各种格式（YOLO、COCO、VOC等）。
采用单一职责原则，只负责导出相关功能。
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

logger = logging.getLogger(__name__)


class AnnotationExporter:
    """标注导出器
    
    负责将标注数据导出为各种格式。
    """
    
    SUPPORTED_FORMATS = ['yolo', 'coco', 'voc', 'csv']
    
    def __init__(self, task_info: Dict[str, Any] = None):
        """初始化导出器
        
        Args:
            task_info: 任务信息字典
        """
        self.task_info = task_info or {}
        self.task_dir = self.task_info.get("task_dir", "")
    
    def export(self, export_format: str, export_dir: str = None) -> bool:
        """导出标注数据
        
        Args:
            export_format: 导出格式 ('yolo', 'coco', 'voc', 'csv')
            export_dir: 导出目录，默认为任务目录下的 annotations
            
        Returns:
            导出是否成功
        """
        if export_format not in self.SUPPORTED_FORMATS:
            logger.error(f"不支持的导出格式: {export_format}")
            return False
        
        if not export_dir:
            export_dir = os.path.join(self.task_dir, "annotations")
        
        os.makedirs(export_dir, exist_ok=True)
        
        try:
            if export_format == "yolo":
                return self._export_yolo_format(export_dir)
            elif export_format == "coco":
                return self._export_coco_format(export_dir)
            elif export_format == "voc":
                return self._export_voc_format(export_dir)
            elif export_format == "csv":
                return self._export_csv_format(export_dir)
        except Exception as e:
            logger.error(f"导出失败: {str(e)}", exc_info=True)
            return False
        
        return False
    
    def _export_yolo_format(self, export_dir: str) -> bool:
        """导出YOLO格式
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        try:
            # 创建类别映射文件
            class_file = os.path.join(export_dir, "classes.txt")
            class_names = self.task_info.get("class_names", {0: "object"})
            
            with open(class_file, 'w', encoding='utf-8') as f:
                for class_id, class_name in sorted(class_names.items()):
                    f.write(f"{class_name}\n")
            
            logger.info(f"YOLO格式导出成功: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出YOLO格式失败: {str(e)}")
            return False
    
    def _export_coco_format(self, export_dir: str) -> bool:
        """导出COCO格式
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        try:
            # 获取图片和标签信息
            image_dir = os.path.join(self.task_dir, "dataset/images/train")
            label_dir = os.path.join(self.task_dir, "dataset/labels/train")
            
            if not os.path.exists(image_dir):
                logger.error("图片目录不存在")
                return False
            
            # 获取图片文件
            valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
            image_files = [f for f in os.listdir(image_dir) 
                          if f.lower().endswith(valid_extensions)]
            
            # 构建COCO数据结构
            coco_data = {
                "images": [],
                "annotations": [],
                "categories": []
            }
            
            # 添加类别信息
            class_names = self.task_info.get("class_names", {0: "object"})
            for class_id, class_name in class_names.items():
                coco_data["categories"].append({
                    "id": class_id,
                    "name": class_name,
                    "supercategory": "none"
                })
            
            # 添加图片和标注信息
            annotation_id = 1
            for img_id, img_file in enumerate(image_files, start=1):
                # 添加图片信息
                img_path = os.path.join(image_dir, img_file)
                img_name = os.path.basename(img_path)
                
                # 获取图片尺寸
                try:
                    from PIL import Image
                    with Image.open(img_path) as img:
                        width, height = img.size
                except:
                    width, height = 640, 480
                
                coco_data["images"].append({
                    "id": img_id,
                    "file_name": img_name,
                    "width": width,
                    "height": height
                })
                
                # 添加标注信息
                label_filename = os.path.splitext(img_file)[0] + ".txt"
                label_path = os.path.join(label_dir, label_filename)
                
                if os.path.exists(label_path):
                    with open(label_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        parts = line.split()
                        if len(parts) < 5:
                            continue
                        
                        try:
                            class_id = int(parts[0])
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            width = float(parts[3])
                            height = float(parts[4])
                            
                            # 转换为绝对坐标
                            x = (x_center - width / 2) * width
                            y = (y_center - height / 2) * height
                            w = width * width
                            h = height * height
                            
                            coco_data["annotations"].append({
                                "id": annotation_id,
                                "image_id": img_id,
                                "category_id": class_id,
                                "bbox": [x, y, w, h],
                                "area": w * h,
                                "iscrowd": 0
                            })
                            annotation_id += 1
                            
                        except (ValueError, IndexError):
                            continue
            
            # 保存COCO文件
            coco_file = os.path.join(export_dir, "annotations.json")
            with open(coco_file, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"COCO格式导出成功: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出COCO格式失败: {str(e)}")
            return False
    
    def _export_voc_format(self, export_dir: str) -> bool:
        """导出VOC格式
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        try:
            # 创建VOC格式的目录结构
            voc_dirs = {
                "Annotations": os.path.join(export_dir, "Annotations"),
                "ImageSets": os.path.join(export_dir, "ImageSets", "Main"),
                "JPEGImages": os.path.join(export_dir, "JPEGImages")
            }
            
            for dir_path in voc_dirs.values():
                os.makedirs(dir_path, exist_ok=True)
            
            # 获取图片和标签信息
            image_dir = os.path.join(self.task_dir, "dataset/images/train")
            label_dir = os.path.join(self.task_dir, "dataset/labels/train")
            
            if not os.path.exists(image_dir):
                logger.error("图片目录不存在")
                return False
            
            # 获取图片文件
            valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
            image_files = [f for f in os.listdir(image_dir) 
                          if f.lower().endswith(valid_extensions)]
            
            # 导出每个图片的XML
            for img_file in image_files:
                img_filename = os.path.splitext(img_file)[0]
                img_path = os.path.join(image_dir, img_file)
                label_filename = img_filename + ".txt"
                label_path = os.path.join(label_dir, label_filename)
                
                # 获取图片尺寸
                try:
                    from PIL import Image
                    with Image.open(img_path) as img:
                        width, height = img.size
                except:
                    width, height = 640, 480
                
                # 创建XML根元素
                annotation = Element('annotation')
                
                # 添加图片信息
                folder = SubElement(annotation, 'folder')
                folder.text = 'JPEGImages'
                
                filename = SubElement(annotation, 'filename')
                filename.text = img_file
                
                size = SubElement(annotation, 'size')
                w = SubElement(size, 'width')
                w.text = str(width)
                h = SubElement(size, 'height')
                h.text = str(height)
                d = SubElement(size, 'depth')
                d.text = '3'
                
                # 添加标注信息
                if os.path.exists(label_path):
                    with open(label_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        parts = line.split()
                        if len(parts) < 5:
                            continue
                        
                        try:
                            class_id = int(parts[0])
                            x_center = float(parts[1])
                            y_center = float(parts[2])
                            w = float(parts[3])
                            h = float(parts[4])
                            
                            # 转换为绝对坐标
                            xmin = int((x_center - w / 2) * width)
                            ymin = int((y_center - h / 2) * height)
                            xmax = int((x_center + w / 2) * width)
                            ymax = int((y_center + h / 2) * height)
                            
                            # 确保坐标在有效范围内
                            xmin = max(0, xmin)
                            ymin = max(0, ymin)
                            xmax = min(width, xmax)
                            ymax = min(height, ymax)
                            
                            class_names = self.task_info.get("class_names", {0: "object"})
                            class_name = class_names.get(class_id, f"class{class_id}")
                            
                            obj = SubElement(annotation, 'object')
                            name = SubElement(obj, 'name')
                            name.text = class_name
                            
                            bndbox = SubElement(obj, 'bndbox')
                            xmin_elem = SubElement(bndbox, 'xmin')
                            xmin_elem.text = str(xmin)
                            ymin_elem = SubElement(bndbox, 'ymin')
                            ymin_elem.text = str(ymin)
                            xmax_elem = SubElement(bndbox, 'xmax')
                            xmax_elem.text = str(xmax)
                            ymax_elem = SubElement(bndbox, 'ymax')
                            ymax_elem.text = str(ymax)
                            
                        except (ValueError, IndexError):
                            continue
                
                # 保存XML文件
                xml_file = os.path.join(voc_dirs["Annotations"], f"{img_filename}.xml")
                with open(xml_file, 'wb') as f:
                    xml_str = tostring(annotation, encoding='unicode')
                    dom = minidom.parseString(xml_str)
                    f.write(dom.toprettyxml(indent="  ", encoding='utf-8'))
                
                # 复制图片到JPEGImages
                import shutil
                dest_img = os.path.join(voc_dirs["JPEGImages"], img_file)
                if not os.path.exists(dest_img):
                    shutil.copy2(img_path, dest_img)
            
            # 创建trainval.txt
            trainval_file = os.path.join(voc_dirs["ImageSets"], "trainval.txt")
            with open(trainval_file, 'w', encoding='utf-8') as f:
                for img_file in image_files:
                    f.write(os.path.splitext(img_file)[0] + '\n')
            
            logger.info(f"VOC格式导出成功: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出VOC格式失败: {str(e)}")
            return False
    
    def _export_csv_format(self, export_dir: str) -> bool:
        """导出CSV格式
        
        Args:
            export_dir: 导出目录
            
        Returns:
            导出是否成功
        """
        try:
            import csv
            
            # 获取图片和标签信息
            image_dir = os.path.join(self.task_dir, "dataset/images/train")
            label_dir = os.path.join(self.task_dir, "dataset/labels/train")
            
            if not os.path.exists(image_dir):
                logger.error("图片目录不存在")
                return False
            
            # 获取图片文件
            valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
            image_files = [f for f in os.listdir(image_dir) 
                          if f.lower().endswith(valid_extensions)]
            
            # 写入CSV文件
            csv_file = os.path.join(export_dir, "annotations.csv")
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['image_file', 'class_name', 'x_center', 'y_center', 'width', 'height'])
                
                class_names = self.task_info.get("class_names", {0: "object"})
                
                for img_file in image_files:
                    label_filename = os.path.splitext(img_file)[0] + ".txt"
                    label_path = os.path.join(label_dir, label_filename)
                    
                    if os.path.exists(label_path):
                        with open(label_path, 'r', encoding='utf-8') as lf:
                            lines = lf.readlines()
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            
                            parts = line.split()
                            if len(parts) < 5:
                                continue
                            
                            try:
                                class_id = int(parts[0])
                                x_center = parts[1]
                                y_center = parts[2]
                                width = parts[3]
                                height = parts[4]
                                
                                class_name = class_names.get(class_id, f"class{class_id}")
                                writer.writerow([img_file, class_name, x_center, y_center, width, height])
                                
                            except (ValueError, IndexError):
                                continue
            
            logger.info(f"CSV格式导出成功: {csv_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出CSV格式失败: {str(e)}")
            return False


# 全局导出器创建函数
def create_exporter(task_info: Dict[str, Any], export_format: str) -> Optional[AnnotationExporter]:
    """创建导出器
    
    Args:
        task_info: 任务信息
        export_format: 导出格式
        
    Returns:
        导出器实例
    """
    if export_format not in AnnotationExporter.SUPPORTED_FORMATS:
        logger.error(f"不支持的格式: {export_format}")
        return None
    
    return AnnotationExporter(task_info)
