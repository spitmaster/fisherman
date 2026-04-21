#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
识别结果可视化：在截图上绘制检测框与标签。
"""

import cv2
import numpy as np


_PALETTE = [
    (0, 255, 0),
    (0, 165, 255),
    (255, 128, 0),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 0),
    (0, 128, 255),
    (128, 0, 255),
]


def _color_for(class_id: int):
    return _PALETTE[class_id % len(_PALETTE)]


def draw_detections(image: np.ndarray, detections: list, highlight_center=None) -> np.ndarray:
    """在图像上绘制检测框、类别、置信度。

    Args:
        image: BGR numpy 数组（不修改原图）
        detections: ScreenRecognition 产出的检测列表
        highlight_center: 可选，要高亮的点击目标中心 (x, y)

    Returns:
        新的 BGR numpy 数组
    """
    if image is None:
        return image

    canvas = image.copy()
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        class_id = int(det.get("class_id", 0))
        color = _color_for(class_id)
        label = f"{det.get('class_name', class_id)} {float(det['confidence']):.0%}"

        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)

        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_y = max(0, y1 - th - baseline - 4)
        cv2.rectangle(
            canvas,
            (x1, label_y),
            (x1 + tw + 6, label_y + th + baseline + 4),
            color,
            -1,
        )
        cv2.putText(
            canvas,
            label,
            (x1 + 3, label_y + th + 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

        cx, cy = det["center"]
        cv2.circle(canvas, (int(cx), int(cy)), 3, color, -1)

    if highlight_center is not None:
        hx, hy = int(highlight_center[0]), int(highlight_center[1])
        cv2.circle(canvas, (hx, hy), 10, (0, 0, 255), 2)
        cv2.line(canvas, (hx - 14, hy), (hx + 14, hy), (0, 0, 255), 1)
        cv2.line(canvas, (hx, hy - 14), (hx, hy + 14), (0, 0, 255), 1)

    return canvas
