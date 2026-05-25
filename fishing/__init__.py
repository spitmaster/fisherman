"""钓鱼自动化模块。详见 docs/SPEC.md §2.14 / §5.5c。"""

from .fishing_loop import (
    DEFAULT_CAST_KEY,
    DEFAULT_DETECT_TIMEOUT_S,
    DEFAULT_POST_TRIGGER_WAIT_S,
    DEFAULT_PREPARE_WAIT_S,
    DEFAULT_WAIT_LAND_S,
    DISPLACEMENT_RATIO,
    MIN_DISPLACEMENT_PX,
    TRIGGER_COOLDOWN_S,
    WINDOW_SECONDS,
    FishingConfig,
    FishingLoop,
    FishingStats,
    FishingState,
    STATE_LABEL,
)

__all__ = [
    "FishingLoop",
    "FishingConfig",
    "FishingStats",
    "FishingState",
    "STATE_LABEL",
    "DISPLACEMENT_RATIO",
    "MIN_DISPLACEMENT_PX",
    "WINDOW_SECONDS",
    "TRIGGER_COOLDOWN_S",
    "DEFAULT_PREPARE_WAIT_S",
    "DEFAULT_CAST_KEY",
    "DEFAULT_WAIT_LAND_S",
    "DEFAULT_DETECT_TIMEOUT_S",
    "DEFAULT_POST_TRIGGER_WAIT_S",
]
