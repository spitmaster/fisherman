#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import uuid
import shutil
import logging
from datetime import datetime, date

from global_support.database import db_manager, ImageLibrary

logger = logging.getLogger(__name__)

# 截图存储目录（项目根/image_library/）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_DIR = os.path.join(_PROJECT_ROOT, 'image_library_files')


class LibraryManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def ensure_dir(self):
        os.makedirs(LIBRARY_DIR, exist_ok=True)

    def get_all(self) -> list:
        """返回所有图库条目，按创建时间倒序。"""
        try:
            session = db_manager.get_session()
            rows = session.query(ImageLibrary).order_by(ImageLibrary.created_at.desc()).all()
            result = [
                {
                    'id': r.id,
                    'file_path': r.file_path,
                    'source': r.source,
                    'created_at': r.created_at,
                }
                for r in rows
            ]
            session.close()
            return result
        except Exception as e:
            logger.error(f"获取图库失败: {e}")
            return []

    def add(self, file_path: str, source: str = 'import') -> str:
        """添加一条图库记录，返回 id；file_path 转为绝对路径存储。"""
        try:
            session = db_manager.get_session()
            item = ImageLibrary(
                id=str(uuid.uuid4()),
                file_path=os.path.abspath(file_path),
                source=source,
            )
            session.add(item)
            session.commit()
            item_id = item.id
            session.close()
            return item_id
        except Exception as e:
            logger.error(f"添加图库记录失败: {e}")
            return ''

    def delete(self, image_id: str) -> bool:
        """删除图库记录，同时删除磁盘文件（不影响已导入训练集的副本）。"""
        try:
            session = db_manager.get_session()
            item = session.query(ImageLibrary).filter_by(id=image_id).first()
            if item:
                file_path = item.file_path
                session.delete(item)
                session.commit()
                if os.path.exists(file_path):
                    os.remove(file_path)
            session.close()
            return True
        except Exception as e:
            logger.error(f"删除图库记录失败: {e}")
            return False

    # 支持的图片扩展名
    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}

    def import_file(self, src_path: str, source: str = 'import') -> str:
        """复制 src_path 到图库目录并注册 DB，返回 image_id。
        文件名规则：{原始stem}_{uuid8}{ext}，保证不碰撞。
        """
        self.ensure_dir()
        stem = os.path.splitext(os.path.basename(src_path))[0]
        ext = os.path.splitext(src_path)[1].lower()
        uid8 = str(uuid.uuid4())[:8]
        dst = os.path.join(LIBRARY_DIR, f"{stem}_{uid8}{ext}")
        shutil.copy2(src_path, dst)
        return self.add(dst, source=source)

    def import_files(self, paths: list, source: str = 'import',
                     progress_cb=None) -> int:
        """批量导入，跳过不支持的扩展名。
        progress_cb(done, total) 每导入一张调用一次。
        返回实际导入数量。
        """
        supported = [p for p in paths
                     if os.path.splitext(p)[1].lower() in self.IMAGE_EXTS]
        total = len(supported)
        done = 0
        for path in supported:
            try:
                self.import_file(path, source=source)
                done += 1
            except Exception as e:
                logger.error(f"导入失败 {path}: {e}")
            if progress_cb:
                progress_cb(done, total)
        return done

    @classmethod
    def scan_folder(cls, folder: str) -> list:
        """递归扫描文件夹，返回所有支持的图片路径列表。"""
        result = []
        for root, _, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in cls.IMAGE_EXTS:
                    result.append(os.path.join(root, f))
        return result

    def take_screenshot(self) -> str:
        """捕获主显示器截图，保存到图库目录，注册 DB，返回 image_id。"""
        self.ensure_dir()
        try:
            import mss
            import mss.tools
            ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"screenshot_{ts}.png"
            dst = os.path.join(LIBRARY_DIR, filename)
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # 主显示器（[0] 是所有屏幕的合并区）
                shot = sct.grab(monitor)
                mss.tools.to_png(shot.rgb, shot.size, output=dst)
            return self.add(dst, source='screenshot')
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return ''

    def import_to_dataset(self, file_paths: list, task_id: str) -> int:
        """将图库中的图片复制到指定训练集 images/ 目录（副本，不删原件）。
        返回实际复制数量。
        """
        from training.dataset_path_manager import DatasetPathManager
        images_dir = DatasetPathManager.get_images_path(task_id)
        images_dir.mkdir(parents=True, exist_ok=True)
        done = 0
        for src in file_paths:
            if not os.path.exists(src):
                logger.warning(f"源文件不存在，跳过: {src}")
                continue
            stem = os.path.splitext(os.path.basename(src))[0]
            ext = os.path.splitext(src)[1].lower()
            uid8 = str(uuid.uuid4())[:8]
            dst = images_dir / f"{stem}_{uid8}{ext}"
            try:
                shutil.copy2(src, dst)
                done += 1
            except Exception as e:
                logger.error(f"复制失败 {src} → {dst}: {e}")
        return done

    def get_today_screenshot_count(self) -> int:
        """今日截图数（source='screenshot'）。"""
        try:
            session = db_manager.get_session()
            today_start = datetime.combine(date.today(), datetime.min.time())
            count = session.query(ImageLibrary).filter(
                ImageLibrary.source == 'screenshot',
                ImageLibrary.created_at >= today_start,
            ).count()
            session.close()
            return count
        except Exception as e:
            logger.error(f"查询今日截图数失败: {e}")
            return 0


library_manager = LibraryManager()
