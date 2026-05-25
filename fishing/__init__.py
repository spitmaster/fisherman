"""钓鱼自动化模块。详见 docs/SPEC.md §2.14 / §5.5c / §2.15。"""

from .constants import (
    BUNDLED_MODEL_FILENAME,
    BUNDLED_MODEL_SUBDIR,
    LIBRARY_HOTKEYS,
    STANDALONE_ENV_FLAG,
    is_standalone_mode,
    resolve_bundled_model_path,
)
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
    # constants
    "LIBRARY_HOTKEYS",
    "BUNDLED_MODEL_FILENAME",
    "BUNDLED_MODEL_SUBDIR",
    "STANDALONE_ENV_FLAG",
    "is_standalone_mode",
    "resolve_bundled_model_path",
]
