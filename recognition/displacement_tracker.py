#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class _TargetTrack:
    class_name: str
    history: deque = field(default_factory=deque)  # (ts, cx, cy, bw, bh)

    def push(self, cx: float, cy: float, bw: float, bh: float,
             ts: float, retain_secs: float) -> None:
        self.history.append((ts, cx, cy, bw, bh))
        cutoff = ts - retain_secs
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

    def last_ts(self) -> float:
        return self.history[-1][0] if self.history else 0.0

    def last_pos(self) -> Optional[Tuple[float, float]]:
        if not self.history:
            return None
        _, cx, cy, _, _ = self.history[-1]
        return cx, cy

    def last_bbox(self) -> Optional[Tuple[float, float]]:
        if not self.history:
            return None
        _, _, _, bw, bh = self.history[-1]
        return bw, bh

    def pos_at(self, target_ts: float) -> Optional[Tuple[float, float]]:
        """Return position closest to target_ts, or None if no entry at/before target_ts."""
        if not self.history:
            return None
        oldest_ts = self.history[0][0]
        if oldest_ts > target_ts:
            return None  # not enough history yet
        best = min(self.history, key=lambda e: abs(e[0] - target_ts))
        return best[1], best[2]


class DisplacementTracker:
    """Filter detections by *relative* displacement over a sliding time window.

    Threshold is computed per-detection:

        threshold_px = max(min_displacement_px, bbox_diagonal * displacement_ratio)

    Rationale: in a 3D scene the same real-world motion produces different
    pixel displacements depending on depth (近 = 大 bbox + 大像素, 远 = 小 bbox +
    小像素). 把阈值绑定到目标自身大小后,远近场景共用一套灵敏度参数。
    `min_displacement_px` 兜底防止远距离 bbox 太小时阈值过小被 YOLO 抖动误触发。

    All state is in-memory; no database writes.
    """

    def __init__(
        self,
        displacement_ratio: float = 0.2,
        min_displacement_px: float = 5.0,
        window_seconds: float = 2.0,
        trigger_cooldown_s: float = 1.0,
        track_timeout_s: float = 3.0,
    ):
        self.displacement_ratio = displacement_ratio
        self.min_displacement_px = min_displacement_px
        self.window_seconds = window_seconds
        self.trigger_cooldown_s = trigger_cooldown_s
        self.track_timeout_s = track_timeout_s

        # (class_name, track_index) → track
        self._tracks: Dict[Tuple[str, int], _TargetTrack] = {}
        self._next_idx: Dict[str, int] = {}
        self._last_trigger: Dict[Tuple[str, int], float] = {}

    # ------------------------------------------------------------------
    # 阈值与匹配半径(都跟 bbox 大小走)
    # ------------------------------------------------------------------

    def _threshold_px(self, bw: float, bh: float) -> float:
        """该 bbox 大小下的位移触发阈值。"""
        diag = math.hypot(bw, bh)
        return max(self.min_displacement_px, diag * self.displacement_ratio)

    def _match_radius(self, bw: float, bh: float) -> float:
        """新检测与已有轨迹匹配的最大距离。
        取阈值的 2 倍 + 兜底,允许目标在阈值范围内"正常运动"还能被匹配。
        """
        return max(self.min_displacement_px * 4.0, self._threshold_px(bw, bh) * 2.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: List[dict]) -> List[dict]:
        """Process one frame of detections.

        Args:
            detections: list of dicts with 'class_name', 'center' (cx, cy),
                        'bbox' (x1, y1, x2, y2), 'confidence'.

        Returns:
            Subset of detections that triggered the displacement condition.
            Each triggered dict gains:
              - 'displacement_px' (float): observed displacement
              - 'threshold_px' (float): the per-detection threshold that was crossed
        """
        now = time.time()
        triggered: List[dict] = []

        for det in detections:
            class_name = det.get("class_name", "")
            cx, cy = det.get("center", (0.0, 0.0))
            cx, cy = float(cx), float(cy)
            bbox = det.get("bbox", (cx, cy, cx, cy))
            bw = float(abs(bbox[2] - bbox[0]))
            bh = float(abs(bbox[3] - bbox[1]))

            key = self._match(class_name, cx, cy, bw, bh, now)
            if key is None:
                # New target — start tracking, no trigger this frame
                self._new_track(class_name, cx, cy, bw, bh, now)
                continue

            track = self._tracks[key]
            track.push(cx, cy, bw, bh, now, self.window_seconds + 1.5)

            if self._displaced(track, cx, cy, bw, bh, now):
                last = self._last_trigger.get(key, 0.0)
                if now - last >= self.trigger_cooldown_s:
                    self._last_trigger[key] = now
                    past = track.pos_at(now - self.window_seconds)
                    dist = math.dist((cx, cy), past) if past else 0.0
                    threshold = self._threshold_px(bw, bh)
                    diag = math.hypot(bw, bh)
                    enriched = dict(det)
                    enriched["displacement_px"] = round(dist, 1)
                    enriched["threshold_px"] = round(threshold, 1)
                    enriched["displacement_ratio"] = round(dist / diag, 3) if diag > 0 else 0.0
                    enriched["bbox_diag_px"] = round(diag, 1)
                    triggered.append(enriched)

        # Prune tracks that have not been seen recently
        stale = [k for k, t in self._tracks.items()
                 if now - t.last_ts() > self.track_timeout_s]
        for k in stale:
            del self._tracks[k]
            self._last_trigger.pop(k, None)

        return triggered

    def reset(self) -> None:
        """Clear all state (call when recognition stops)."""
        self._tracks.clear()
        self._next_idx.clear()
        self._last_trigger.clear()

    def configure(
        self,
        displacement_ratio: Optional[float] = None,
        min_displacement_px: Optional[float] = None,
        window_seconds: Optional[float] = None,
        trigger_cooldown_s: Optional[float] = None,
    ) -> None:
        """Update parameters at runtime (may be called from UI thread)."""
        if displacement_ratio is not None:
            self.displacement_ratio = displacement_ratio
        if min_displacement_px is not None:
            self.min_displacement_px = min_displacement_px
        if window_seconds is not None:
            self.window_seconds = window_seconds
        if trigger_cooldown_s is not None:
            self.trigger_cooldown_s = trigger_cooldown_s

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match(self, class_name: str, cx: float, cy: float,
               bw: float, bh: float, now: float
               ) -> Optional[Tuple[str, int]]:
        radius = self._match_radius(bw, bh)
        best_key, best_d = None, float("inf")
        for key, track in self._tracks.items():
            if key[0] != class_name:
                continue
            if now - track.last_ts() > self.track_timeout_s:
                continue
            pos = track.last_pos()
            if pos is None:
                continue
            d = math.dist((cx, cy), pos)
            if d < best_d:
                best_d, best_key = d, key
        return best_key if best_d <= radius else None

    def _new_track(self, class_name: str, cx: float, cy: float,
                   bw: float, bh: float, now: float
                   ) -> Tuple[str, int]:
        idx = self._next_idx.get(class_name, 0)
        self._next_idx[class_name] = idx + 1
        key = (class_name, idx)
        t = _TargetTrack(class_name=class_name)
        t.push(cx, cy, bw, bh, now, self.window_seconds + 1.5)
        self._tracks[key] = t
        logger.debug(f"新追踪轨迹: {key}  bbox={bw:.0f}x{bh:.0f}")
        return key

    def _displaced(self, track: _TargetTrack, cx: float, cy: float,
                   bw: float, bh: float, now: float) -> bool:
        past = track.pos_at(now - self.window_seconds)
        if past is None:
            return False
        threshold = self._threshold_px(bw, bh)
        return math.dist((cx, cy), past) > threshold
