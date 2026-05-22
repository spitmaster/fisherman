#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import uuid
import shutil
import logging
from datetime import datetime, date

from global_support.database import db_manager, ImageLibrary, ImageLibraryAlbum

logger = logging.getLogger(__name__)

# 截图存储目录（项目根/image_library_files/）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_DIR = os.path.join(_PROJECT_ROOT, 'image_library_files')

DEFAULT_ALBUM_NAME = '默认图集'


class LibraryManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def ensure_dir(self):
        os.makedirs(LIBRARY_DIR, exist_ok=True)

    # ------------------------------------------------------------- 图集 CRUD --

    def ensure_default_album(self) -> str:
        """确保「默认图集」存在,并把所有 album_id 为空的旧图片归入默认图集。
        返回默认图集 id。
        """
        try:
            session = db_manager.get_session()
            album = session.query(ImageLibraryAlbum).filter_by(name=DEFAULT_ALBUM_NAME).first()
            if album is None:
                album = ImageLibraryAlbum(
                    id=str(uuid.uuid4()),
                    name=DEFAULT_ALBUM_NAME,
                )
                session.add(album)
                session.commit()
                logger.info(f"创建默认图集: id={album.id}")
            album_id = album.id

            # 把所有 album_id IS NULL 的旧图片归入默认图集
            orphans = session.query(ImageLibrary).filter(ImageLibrary.album_id.is_(None)).all()
            if orphans:
                for img in orphans:
                    img.album_id = album_id
                session.commit()
                logger.info(f"将 {len(orphans)} 张旧图片归入默认图集")

            session.close()
            return album_id
        except Exception as e:
            logger.error(f"确保默认图集失败: {e}")
            return ''

    def get_all_albums(self) -> list:
        """返回所有图集(含图片数),按创建时间升序;默认图集恒在最前。"""
        try:
            session = db_manager.get_session()
            albums = session.query(ImageLibraryAlbum).order_by(ImageLibraryAlbum.created_at.asc()).all()
            result = []
            for a in albums:
                count = session.query(ImageLibrary).filter_by(album_id=a.id).count()
                result.append({
                    'id': a.id,
                    'name': a.name,
                    'created_at': a.created_at,
                    'image_count': count,
                    'is_default': a.name == DEFAULT_ALBUM_NAME,
                })
            # 默认图集放最前
            result.sort(key=lambda x: (not x['is_default'], x['created_at'] or datetime.min))
            session.close()
            return result
        except Exception as e:
            logger.error(f"获取图集列表失败: {e}")
            return []

    def create_album(self, name: str) -> str:
        """新建图集。同名冲突返回空字符串。"""
        name = (name or '').strip()
        if not name:
            return ''
        try:
            session = db_manager.get_session()
            exists = session.query(ImageLibraryAlbum).filter_by(name=name).first()
            if exists:
                session.close()
                logger.warning(f"图集名已存在: {name}")
                return ''
            album = ImageLibraryAlbum(id=str(uuid.uuid4()), name=name)
            session.add(album)
            session.commit()
            album_id = album.id
            session.close()
            logger.info(f"创建图集: {name} ({album_id})")
            return album_id
        except Exception as e:
            logger.error(f"创建图集失败 {name}: {e}")
            return ''

    def rename_album(self, album_id: str, new_name: str) -> bool:
        """重命名图集。默认图集不可改名。"""
        new_name = (new_name or '').strip()
        if not new_name:
            return False
        try:
            session = db_manager.get_session()
            album = session.query(ImageLibraryAlbum).filter_by(id=album_id).first()
            if not album:
                session.close()
                return False
            if album.name == DEFAULT_ALBUM_NAME:
                session.close()
                logger.warning("默认图集不可重命名")
                return False
            dup = session.query(ImageLibraryAlbum).filter_by(name=new_name).first()
            if dup and dup.id != album_id:
                session.close()
                logger.warning(f"重命名失败,名称已存在: {new_name}")
                return False
            album.name = new_name
            session.commit()
            session.close()
            return True
        except Exception as e:
            logger.error(f"重命名图集失败: {e}")
            return False

    def delete_album(self, album_id: str) -> bool:
        """删除图集,同时删除图集内所有图片(DB + 磁盘文件)。默认图集不可删。"""
        try:
            session = db_manager.get_session()
            album = session.query(ImageLibraryAlbum).filter_by(id=album_id).first()
            if not album:
                session.close()
                return False
            if album.name == DEFAULT_ALBUM_NAME:
                session.close()
                logger.warning("默认图集不可删除")
                return False
            images = session.query(ImageLibrary).filter_by(album_id=album_id).all()
            file_paths = [img.file_path for img in images]
            for img in images:
                session.delete(img)
            session.delete(album)
            session.commit()
            session.close()
            # 删除磁盘文件
            for fp in file_paths:
                try:
                    if fp and os.path.exists(fp):
                        os.remove(fp)
                except Exception as e:
                    logger.warning(f"删除文件失败 {fp}: {e}")
            logger.info(f"删除图集 {album.name},清理图片 {len(file_paths)} 张")
            return True
        except Exception as e:
            logger.error(f"删除图集失败: {e}")
            return False

    # ----------------------------------------------------------- 图片查询 ----

    def get_images(self, album_id: str) -> list:
        """返回指定图集的图片列表,按创建时间倒序。"""
        if not album_id:
            return []
        try:
            session = db_manager.get_session()
            rows = (session.query(ImageLibrary)
                    .filter_by(album_id=album_id)
                    .order_by(ImageLibrary.created_at.desc())
                    .all())
            result = [
                {
                    'id': r.id,
                    'album_id': r.album_id,
                    'file_path': r.file_path,
                    'source': r.source,
                    'created_at': r.created_at,
                }
                for r in rows
            ]
            session.close()
            return result
        except Exception as e:
            logger.error(f"获取图集图片失败: {e}")
            return []

    # ------------------------------------------------------------- 图片写入 --

    def add(self, file_path: str, source: str = 'import', album_id: str = None) -> str:
        """添加一条图库记录,返回 id。"""
        try:
            session = db_manager.get_session()
            item = ImageLibrary(
                id=str(uuid.uuid4()),
                album_id=album_id,
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
        """删除单张图片记录,同时删除磁盘文件。"""
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

    def import_file(self, src_path: str, source: str = 'import', album_id: str = None) -> str:
        """复制 src_path 到图库目录并注册 DB,返回 image_id。"""
        self.ensure_dir()
        stem = os.path.splitext(os.path.basename(src_path))[0]
        ext = os.path.splitext(src_path)[1].lower()
        uid8 = str(uuid.uuid4())[:8]
        dst = os.path.join(LIBRARY_DIR, f"{stem}_{uid8}{ext}")
        shutil.copy2(src_path, dst)
        return self.add(dst, source=source, album_id=album_id)

    def import_files(self, paths: list, source: str = 'import',
                     album_id: str = None, progress_cb=None) -> int:
        """批量导入到指定图集,跳过不支持的扩展名。返回实际导入数量。"""
        supported = [p for p in paths
                     if os.path.splitext(p)[1].lower() in self.IMAGE_EXTS]
        total = len(supported)
        done = 0
        for path in supported:
            try:
                self.import_file(path, source=source, album_id=album_id)
                done += 1
            except Exception as e:
                logger.error(f"导入失败 {path}: {e}")
            if progress_cb:
                progress_cb(done, total)
        return done

    @classmethod
    def scan_folder(cls, folder: str) -> list:
        """递归扫描文件夹,返回所有支持的图片路径列表。"""
        result = []
        for root, _, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in cls.IMAGE_EXTS:
                    result.append(os.path.join(root, f))
        return result

    def take_screenshot(self, album_id: str = None) -> str:
        """捕获主显示器截图,保存到图库目录,注册到指定图集。"""
        self.ensure_dir()
        try:
            import mss
            import mss.tools
            ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"screenshot_{ts}.png"
            dst = os.path.join(LIBRARY_DIR, filename)
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # 主显示器
                shot = sct.grab(monitor)
                mss.tools.to_png(shot.rgb, shot.size, output=dst)
            return self.add(dst, source='screenshot', album_id=album_id)
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return ''

    def import_to_dataset(self, file_paths: list, task_id: str) -> int:
        """将图库中的图片复制到指定训练集 images/ 目录。返回实际复制数量。"""
        from training.dataset_path_manager import DatasetPathManager
        images_dir = DatasetPathManager.get_images_path(task_id)
        images_dir.mkdir(parents=True, exist_ok=True)
        done = 0
        for src in file_paths:
            if not os.path.exists(src):
                logger.warning(f"源文件不存在,跳过: {src}")
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
        """今日截图数(source='screenshot')。"""
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
