#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练日志管理器

负责训练日志的输出、文件写入和回调处理。
"""

import re
import logging
from typing import Optional, Callable
from datetime import datetime
import hashlib
from pathlib import Path

from ..dataset_path_manager import DatasetPathManager

logger = logging.getLogger(__name__)


class TrainingLogManager:
    """训练日志管理器"""

    # 类级别的日志回调函数和文件路径
    log_callback: Optional[Callable[[str], None]] = None
    log_file_path: Optional[str] = None

    @classmethod
    def set_log_callback(cls, callback: Callable[[str], None]):
        """设置日志回调函数

        Args:
            callback: 日志回调函数
        """
        cls.log_callback = callback

    def __init__(self, dataset_name: Optional[str] = None):
        """初始化日志管理器

        Args:
            dataset_name: 数据集名称,用于创建日志文件
        """
        self.dataset_name = dataset_name
        if dataset_name:
            self.create_log_file(dataset_name)

    def remove_ansi_codes(self, text: str) -> str:
        """去除字符串中的ANSI转义码

        Args:
            text: 包含ANSI码的文本

        Returns:
            清理后的文本
        """
        # ANSI转义码的正则表达式模式
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[mK]')
        # 去除ANSI码和进度条控制字符
        cleaned = ansi_escape.sub('', text)
        # 去除 carriage return
        cleaned = cleaned.replace('\r', '')
        return cleaned.strip()

    def emit_log(self, message: str):
        """发送日志到回调和文件

        Args:
            message: 日志消息
        """
        # 去除ANSI转义码
        clean_message = self.remove_ansi_codes(message)

        if self.log_callback:
            try:
                self.log_callback(clean_message)
            except Exception as e:
                logger.error(f"日志回调失败: {str(e)}")

        # 写入日志文件
        self.write_log_to_file(clean_message)

    def write_log_to_file(self, message: str):
        """写入日志到文件

        Args:
            message: 日志消息
        """
        if self.log_file_path:
            try:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(message + '\n')
            except Exception as e:
                logger.error(f"写入日志文件失败: {str(e)}")

    def create_log_file(self, dataset_name: str) -> Optional[str]:
        """创建训练日志文件

        Args:
            dataset_name: 训练集名称

        Returns:
            日志文件路径
        """
        try:
            # 生成时间戳和hash
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d%H%M%S")

            # 使用数据集名称作为hash
            hash_value = hashlib.md5(dataset_name.encode('utf-8')).hexdigest()[:8]

            # 日志文件名: 训练日志-年月日时分秒hash.log
            log_filename = f"训练日志-{timestamp}{hash_value}.log"

            # 日志文件保存在数据集目录下
            dataset_path = DatasetPathManager.get_dataset_path(dataset_name)
            log_file_path = dataset_path / log_filename

            # 写入日志头
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write(f"=" * 60 + "\n")
                f.write(f"训练日志\n")
                f.write(f"数据集名称: {dataset_name}\n")
                f.write(f"开始时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"=" * 60 + "\n\n")

            self.log_file_path = str(log_file_path)
            self.dataset_name = dataset_name
            logger.info(f"创建日志文件: {self.log_file_path}")
            return self.log_file_path

        except Exception as e:
            logger.error(f"创建日志文件失败: {str(e)}")
            return None

    def write_completion_log(self, success: bool, error_msg: Optional[str] = None):
        """写入训练完成日志

        Args:
            success: 是否成功
            error_msg: 错误消息
        """
        self.write_log_to_file("=" * 60)
        if success:
            self.write_log_to_file(f"训练完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            if error_msg:
                self.write_log_to_file(f"训练失败: {error_msg}")
            self.write_log_to_file(f"失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.write_log_to_file("=" * 60)
