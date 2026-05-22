import os
import sys
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError

# 日志记录
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class TrainingTask(Base):
    __tablename__ = 'training_tasks'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_name = Column(String(255), nullable=False)
    task_description = Column(Text)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    dataset_path = Column(String(500))
    model_path = Column(String(500))
    epochs = Column(Integer, default=50)
    batch_size = Column(Integer, default=8)
    mAP = Column(Float)
    loss = Column(Float)

    # 关系
    training_logs = relationship("TrainingLog", back_populates="training_task")
    recognition_tasks = relationship("RecognitionTask", back_populates="training_task")

class TrainingLog(Base):
    __tablename__ = 'training_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    training_task_id = Column(String(36), ForeignKey('training_tasks.id'))
    log_level = Column(String(10), default='INFO')
    log_message = Column(Text)
    log_time = Column(DateTime, default=datetime.now)

    training_task = relationship("TrainingTask", back_populates="training_logs")

class RecognitionTask(Base):
    __tablename__ = 'recognition_tasks'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    training_task_id = Column(String(36), ForeignKey('training_tasks.id'))
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    confidence_threshold = Column(Integer, default=70)
    click_cooldown = Column(Integer, default=5)
    total_recognitions = Column(Integer, default=0)
    total_clicks = Column(Integer, default=0)
    avg_fps = Column(Integer, default=0)

    training_task = relationship("TrainingTask", back_populates="recognition_tasks")
    recognition_logs = relationship("RecognitionLog", back_populates="recognition_task")
    recognition_details = relationship("RecognitionDetail", back_populates="recognition_task")

class RecognitionLog(Base):
    __tablename__ = 'recognition_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recognition_task_id = Column(String(36), ForeignKey('recognition_tasks.id'))
    log_level = Column(String(10), default='INFO')
    log_message = Column(Text)
    log_time = Column(DateTime, default=datetime.now)

    recognition_task = relationship("RecognitionTask", back_populates="recognition_logs")

class RecognitionDetail(Base):
    __tablename__ = 'recognition_details'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recognition_task_id = Column(String(36), ForeignKey('recognition_tasks.id'))
    timestamp = Column(DateTime, default=datetime.now)
    target_x = Column(Integer)
    target_y = Column(Integer)
    confidence = Column(Integer)
    target_class = Column(String(255))

    recognition_task = relationship("RecognitionTask", back_populates="recognition_details")

class ModelVersion(Base):
    __tablename__ = 'model_versions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    training_task_id = Column(String(36), ForeignKey('training_tasks.id'))
    model_path = Column(String(500))
    version = Column(String(50))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    file_size = Column(Integer, default=0)

    training_task = relationship("TrainingTask")


class ImageLibraryAlbum(Base):
    __tablename__ = 'image_library_albums'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now)

    images = relationship("ImageLibrary", back_populates="album")


class ImageLibrary(Base):
    __tablename__ = 'image_library'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    album_id = Column(String(36), ForeignKey('image_library_albums.id'), nullable=True)
    file_path = Column(String(500), nullable=False)
    source = Column(String(20), default='import')  # 'screenshot' | 'import'
    created_at = Column(DateTime, default=datetime.now)

    album = relationship("ImageLibraryAlbum", back_populates="images")


class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.db_url = 'sqlite:///fisherman.db'
        self.engine = None
        self.Session = None
        
    def connect(self):
        """连接到数据库"""
        try:
            self.engine = create_engine(self.db_url)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("数据库连接成功")
            return True
        except SQLAlchemyError as e:
            logger.error(f"数据库连接失败: {str(e)}")
            return False
            
    def create_tables(self):
        """创建所有数据库表"""
        if not self.engine:
            self.connect()
            
        try:
            Base.metadata.create_all(self.engine)
            logger.info("数据库表创建成功")
            return True
        except SQLAlchemyError as e:
            logger.error(f"创建表失败: {str(e)}")
            return False
            
    def get_session(self):
        """获取数据库会话"""
        if not self.Session:
            self.connect()
            
        return self.Session()

# 全局数据库管理器实例
db_manager = DatabaseManager()