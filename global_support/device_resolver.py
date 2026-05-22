#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件设备枚举与解析。

启动时调用 get_available_devices() 一次即可获得可用设备列表并全局缓存。
"""

import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    spec: str            # "cpu" / "cuda:0" / "cuda:1"
    kind: str            # "cpu" / "cuda"
    index: int           # 0 for cpu, 0/1/… for each GPU
    name: str            # "CPU" / "NVIDIA GeForce RTX 3080"
    total_memory_mb: int # 0 for CPU
    available: bool      # always True for CPU; CUDA 可用才加入列表


def enumerate_devices() -> List[DeviceInfo]:
    """枚举当前机器可用的所有计算设备。"""
    devices: List[DeviceInfo] = []

    # CPU 始终可用
    devices.append(DeviceInfo(
        spec="cpu",
        kind="cpu",
        index=0,
        name="CPU",
        total_memory_mb=0,
        available=True,
    ))

    # CUDA GPU
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                try:
                    props = torch.cuda.get_device_properties(i)
                    memory_mb = props.total_memory // (1024 * 1024)
                    devices.append(DeviceInfo(
                        spec=f"cuda:{i}",
                        kind="cuda",
                        index=i,
                        name=props.name,
                        total_memory_mb=memory_mb,
                        available=True,
                    ))
                except Exception as e:
                    logger.warning(f"获取 cuda:{i} 属性失败: {e}")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"枚举 CUDA 设备失败: {e}")

    return devices


def device_display_name(info: DeviceInfo) -> str:
    """生成下拉框中显示的友好名称。"""
    if info.kind == "cpu":
        return "CPU  —  中央处理器"
    mem = f"{info.total_memory_mb} MB" if info.total_memory_mb else ""
    return f"GPU {info.index}  —  {info.name}" + (f"  ({mem})" if mem else "")


# 全局缓存，启动时首次调用后复用
_cached_devices: List[DeviceInfo] = []


def get_available_devices() -> List[DeviceInfo]:
    """返回可用设备列表（首次调用时枚举并缓存）。"""
    global _cached_devices
    if not _cached_devices:
        _cached_devices = enumerate_devices()
        specs = [d.spec for d in _cached_devices]
        logger.info(f"可用计算设备: {specs}")
    return _cached_devices
