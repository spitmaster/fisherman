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
    history: deque = field(default_factory=deque)  # (timestamp, cx, cy)

    def push(self, cx: float, cy: float, ts: float, retain_secs: float) -> None:
        self.history.append((ts, cx, cy))
        cutoff = ts - retain_secs
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()

    def last_ts(self) -> float:
        return self.history[-1][0] if self.history else 0.0

    def last_pos(self) -> Optional[Tuple[float, float]]:
        if not self.history:
            return None
        _, cx, cy = self.history[-1]
        return cx, cy

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
    """Filter detections by displacement over a sliding time window.

    Each call to update() matches current detections to known tracks (same class,
    nearest centroid within match_radius), then triggers on tracks whose center
    has moved more than displacement_threshold_px compared to their position
    window_seconds ago.

    All state is in-memory; no database writes.
    """

    def __init__(
        self,
        displacement_threshold_px: float = 50.0,
        window_seconds: float = 2.0,
        trigger_cooldown_s: float = 1.0,
        track_timeout_s: float = 3.0,
    ):
        self.displacement_threshold_px = displacement_threshold_px
        self.window_seconds = window_seconds
        self.trigger_cooldown_s = trigger_cooldown_s
        self.track_timeout_s = track_timeout_s

        # (class_name, track_index) → track
        self._tracks: Dict[Tuple[str, int], _TargetTrack] = {}
        self._next_idx: Dict[str, int] = {}
        self._last_trigger: Dict[Tuple[str, int], float] = {}

    @property
    def _match_radius(self) -> float:
        return self.displacement_threshold_px * 2.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: List[dict]) -> List[dict]:
        """Process one frame of detections.

        Args:
            detections: list of dicts with 'class_name', 'center' (cx, cy),
                        'confidence', 'bbox'.

        Returns:
            Subset of detections that triggered the displacement condition.
            Each triggered dict gains a 'displacement_px' key (float).
        """
        now = time.time()
        triggered: List[dict] = []

        for det in detections:
            class_name = det.get("class_name", "")
            cx, cy = det.get("center", (0.0, 0.0))
            cx, cy = float(cx), float(cy)

            key = self._match(class_name, cx, cy, now)
            if key is None:
                # New target — start tracking, no trigger this frame
                self._new_track(class_name, cx, cy, now)
                continue

            track = self._tracks[key]
            track.push(cx, cy, now, self.window_seconds + 1.5)

            if self._displaced(track, cx, cy, now):
                last = self._last_trigger.get(key, 0.0)
                if now - last >= self.trigger_cooldown_s:
                    self._last_trigger[key] = now
                    past = track.pos_at(now - self.window_seconds)
                    dist = math.dist((cx, cy), past) if past else 0.0
                    enriched = dict(det)
                    enriched["displacement_px"] = round(dist, 1)
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
        displacement_threshold_px: Optional[float] = None,
        window_seconds: Optional[float] = None,
        trigger_cooldown_s: Optional[float] = None,
    ) -> None:
        """Update parameters at runtime (may be called from UI thread)."""
        if displacement_threshold_px is not None:
            self.displacement_threshold_px = displacement_threshold_px
        if window_seconds is not None:
            self.window_seconds = window_seconds
        if trigger_cooldown_s is not None:
            self.trigger_cooldown_s = trigger_cooldown_s

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match(self, class_name: str, cx: float, cy: float, now: float
               ) -> Optional[Tuple[str, int]]:
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
        return best_key if best_d <= self._match_radius else None

    def _new_track(self, class_name: str, cx: float, cy: float, now: float
                   ) -> Tuple[str, int]:
        idx = self._next_idx.get(class_name, 0)
        self._next_idx[class_name] = idx + 1
        key = (class_name, idx)
        t = _TargetTrack(class_name=class_name)
        t.push(cx, cy, now, self.window_seconds + 1.5)
        self._tracks[key] = t
        logger.debug(f"新追踪轨迹: {key}")
        return key

    def _displaced(self, track: _TargetTrack, cx: float, cy: float, now: float) -> bool:
        past = track.pos_at(now - self.window_seconds)
        if past is None:
            return False
        return math.dist((cx, cy), past) > self.displacement_threshold_px
