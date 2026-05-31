#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钓鱼死循环状态机(FishingLoop)。

详见 docs/SPEC.md §2.14(产品规格)与 §5.5c(状态机与线程模型)。

设计要点:
- 工作线程跑 IDLE → PREPARE → CAST → WAIT_LAND → DETECTING → TRIGGERED/TIMEOUT → PICK_UP → POST_PROCESS → 回头
- 所有 sleep 切成 SLEEP_TICK_S(0.05s)小步,每步检查 stop_flag,响应 ≤ 50ms
- 位移检测参数固定(D6,不暴露 UI),需调先去位移测试 Tab 验证后改本文件常量
- 触发目标取 confidence 最高(D4,单类别 wow_fish.pt 通常 = 1 个浮漂)
- 超时仍走 POST_PROCESS(D3,让通用宏即使没钓到鱼也运行)
- 不入 DB / 日志精简(D5):仅启动 / 停止 / 异常 / 超时 / 按键失败 打 logger,正常轮次靠回调更新 UI
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Tuple

import pyautogui

from recognition import window_io
from recognition.displacement_tracker import DisplacementTracker
from recognition.screen_recognition import ScreenRecognition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 常量(SPEC §2.14 F2.14.2 / F2.14.4-9 默认值)
# ---------------------------------------------------------------------------

# 位移检测参数(SPEC §5.5 实测最优,D6 拍板不暴露 UI)
DISPLACEMENT_RATIO = 0.09
MIN_DISPLACEMENT_PX = 5.0
WINDOW_SECONDS = 0.5
TRIGGER_COOLDOWN_S = 1.0

# 钓鱼循环默认参数(2026-05-25 用户实测最优,见 milestones/20260204.md)
DEFAULT_PREPARE_WAIT_S = 5.0
DEFAULT_CAST_KEY = "-"
DEFAULT_WAIT_LAND_S = 3.0
DEFAULT_DETECT_TIMEOUT_S = 17.0
DEFAULT_POST_TRIGGER_WAIT_S = 1.0

# stop_flag 检查粒度,SPEC §5.5c 要求停止响应 ≤ 50ms
SLEEP_TICK_S = 0.05


# ---------------------------------------------------------------------------
# 状态枚举
# ---------------------------------------------------------------------------


class FishingState(Enum):
    IDLE = "idle"
    PREPARE = "prepare"            # 步骤 0(预备等待)+ 1(钓鱼前准备按键)
    CAST = "cast"                  # 步骤 2(抛竿键)
    WAIT_LAND = "wait_land"        # 步骤 3a(抛竿后等浮漂稳定)
    DETECTING = "detecting"        # 步骤 3b(位移检测中)
    TRIGGERED = "triggered"        # 步骤 4a(触发后等待)
    PICK_UP = "pick_up"            # 步骤 4b(右键点击触发目标)
    POST_PROCESS = "post_process"  # 步骤 5(钓鱼后处理按键)
    TIMEOUT = "timeout"            # 检测超时,跳过点击
    STOPPING = "stopping"          # 收到 stop_flag,清理资源


STATE_LABEL = {
    FishingState.IDLE: "等待启动",
    FishingState.PREPARE: "预备",
    FishingState.CAST: "抛竿",
    FishingState.WAIT_LAND: "等浮漂落水",
    FishingState.DETECTING: "位移检测中",
    FishingState.TRIGGERED: "触发后等待",
    FishingState.PICK_UP: "右键拾取",
    FishingState.POST_PROCESS: "钓鱼后处理",
    FishingState.TIMEOUT: "超时",
    FishingState.STOPPING: "停止中",
}


# ---------------------------------------------------------------------------
# 配置 / 统计
# ---------------------------------------------------------------------------


@dataclass
class FishingConfig:
    """单轮钓鱼循环的全部配置参数。"""

    model_path: str
    confidence: float = 0.70
    device: str = "cpu"
    # (x, y, w, h) 屏幕绝对坐标,None=全屏
    monitor_area: Optional[Tuple[int, int, int, int]] = None

    # 操作模式(M7 后台钓鱼):
    #   "screen" — 前台:mss 抓屏 + pyautogui 投键鼠(现状,游戏须前台)
    #   "window" — 后台:window_io 抓窗口 + PostMessage 投键鼠(游戏可后台/被遮挡)
    capture_mode: str = "screen"
    hwnd: int = 0                                # 后台模式初始窗口句柄(UI 选中时记)
    window_title: str = ""                       # 后台模式窗口标题(运行时按它重解析 hwnd)
    # (x, y, w, h) 客户区相对子区域,None=整个客户区(仅 window 模式)
    window_region: Optional[Tuple[int, int, int, int]] = None

    prepare_wait_s: float = DEFAULT_PREPARE_WAIT_S
    pre_action_key: str = ""        # 空 = 跳过
    cast_key: str = DEFAULT_CAST_KEY
    wait_land_s: float = DEFAULT_WAIT_LAND_S
    detect_timeout_s: float = DEFAULT_DETECT_TIMEOUT_S
    post_trigger_wait_s: float = DEFAULT_POST_TRIGGER_WAIT_S
    post_action_key: str = ""       # 空 = 跳过


@dataclass
class FishingStats:
    rounds: int = 0
    success: int = 0
    timeout: int = 0
    consecutive_fail: int = 0

    def snapshot(self) -> "FishingStats":
        return FishingStats(
            rounds=self.rounds,
            success=self.success,
            timeout=self.timeout,
            consecutive_fail=self.consecutive_fail,
        )


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------


class FishingLoop:
    """死循环钓鱼状态机。

    线程模型:
        - `start()` 起 1 个 daemon 工作线程跑 `_run`,所有状态机推进在该线程内
        - 回调(`on_state_change` / `on_round_complete` / `on_trigger` / `on_error`)
          全部在工作线程触发;UI 端必须用 pyqtSignal 切回主线程更新 QWidget(架构不变量 2)
        - `ScreenRecognition` 内部还会起截图+推理共 2 个 daemon 线程,
          只在 DETECTING 阶段 running、其他阶段 stop;模型只在第一次 DETECTING 时加载,
          后续轮次复用同一 `ScreenRecognition` 实例
    """

    def __init__(
        self,
        config: FishingConfig,
        on_state_change: Optional[
            Callable[[FishingState, int, float, float], None]
        ] = None,
        on_round_complete: Optional[Callable[[FishingStats], None]] = None,
        on_trigger: Optional[Callable[[dict], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_frame: Optional[Callable[[object, list], None]] = None,
    ):
        """
        Args:
            config: 单轮配置(见 `FishingConfig`)
            on_state_change(state, round_idx, elapsed_s, total_s):
                状态切换 / 进度刷新。`elapsed_s` 与 `total_s` 用于实时进度条;
                瞬时步骤(CAST/PICK_UP/POST_PROCESS)传 0.0/0.0
            on_round_complete(stats): 一轮完结时回调,传入 stats 快照
            on_trigger(detection): 检测到首次触发位移时回调,传入 enriched detection dict
            on_error(msg): 任何异常(按键失败 / 识别错误 / 主循环崩溃)的人类可读描述
            on_frame(frame_bgr, detections): 每帧截图回调(在截图后台线程触发),
                供 UI 渲染预览。注意:此回调在后台线程内,UI 端必须用 pyqtSignal 切回主线程。
        """
        self.config = config
        self.on_state_change = on_state_change
        self.on_round_complete = on_round_complete
        self.on_trigger = on_trigger
        self.on_error = on_error
        self.on_frame = on_frame

        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._state: FishingState = FishingState.IDLE
        self._round_idx: int = 0
        self.stats = FishingStats()

        # 识别管线复用:首次 DETECTING 时建好,之后每轮仅 start/stop 不重 load 模型
        self._recognition: Optional[ScreenRecognition] = None
        self._tracker: Optional[DisplacementTracker] = None

        # 后台模式运行时解析出的窗口句柄(随游戏重启变化,按 window_title 重解析)
        self._hwnd: int = config.hwnd

        # 触发结果(由 ScreenRecognition 推理线程写、主循环读)
        self._triggered_target: Optional[dict] = None
        self._trigger_lock = threading.Lock()

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    @property
    def state(self) -> FishingState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.is_running:
            logger.warning("钓鱼循环已在运行,忽略 start")
            return False
        self._stop_flag.clear()
        self.stats = FishingStats()
        self._round_idx = 0
        self._thread = threading.Thread(
            target=self._run, name="FishingLoop", daemon=True
        )
        self._thread.start()
        logger.info(
            "钓鱼循环启动: model=%s device=%s cast=%r pre=%r post=%r "
            "wait_land=%.1fs detect_timeout=%.1fs post_trigger=%.1fs prepare=%.1fs",
            self.config.model_path, self.config.device,
            self.config.cast_key, self.config.pre_action_key, self.config.post_action_key,
            self.config.wait_land_s, self.config.detect_timeout_s,
            self.config.post_trigger_wait_s, self.config.prepare_wait_s,
        )
        return True

    def stop(self) -> None:
        if not self.is_running:
            return
        logger.info("钓鱼循环收到停止信号")
        self._stop_flag.set()

    def wait_until_stopped(self, timeout: float = 5.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def _run(self) -> None:
        try:
            # 识别在整个钓鱼期间常驻,保证预览不间断;
            # tracker 仅在 DETECTING 阶段存在,其他阶段 _on_raw_detections 直接 return
            self._ensure_recognition_started()

            while not self._stop_flag.is_set():
                # 后台模式:每轮开头确认游戏窗口还在(关闭/重启则 hwnd 失效)
                if not self._check_window_alive():
                    break

                self._round_idx += 1
                self.stats.rounds += 1

                if not self._do_prepare():
                    break
                if not self._do_cast():
                    break
                if not self._do_wait_land():
                    break

                target = self._do_detect()
                if self._stop_flag.is_set():
                    break

                if target is not None:
                    if not self._do_triggered_wait():
                        break
                    self._do_pick_up(target)
                    self.stats.success += 1
                    self.stats.consecutive_fail = 0
                else:
                    self._set_state(FishingState.TIMEOUT, 0.0, 0.0)
                    self.stats.timeout += 1
                    self.stats.consecutive_fail += 1
                    logger.warning(
                        "第 %d 轮位移检测超时(连续失败 %d)",
                        self._round_idx, self.stats.consecutive_fail,
                    )

                # D3:即使超时也走 POST_PROCESS,让通用宏(清菜单/卸 buff)生效
                self._do_post_process()

                self._emit_round_complete()

        except Exception as e:
            logger.error("钓鱼循环异常退出: %s", e, exc_info=True)
            if self.on_error:
                try:
                    self.on_error(str(e))
                except Exception:
                    pass
        finally:
            self._set_state(FishingState.STOPPING, 0.0, 0.0)
            self._teardown_recognition()
            self._set_state(FishingState.IDLE, 0.0, 0.0)
            logger.info(
                "钓鱼循环已停止: 共 %d 轮 / 成功 %d / 超时 %d",
                self.stats.rounds, self.stats.success, self.stats.timeout,
            )

    # ------------------------------------------------------------------
    # 各步骤
    # ------------------------------------------------------------------

    def _do_prepare(self) -> bool:
        if not self._sleep_with_state(
            FishingState.PREPARE, self.config.prepare_wait_s
        ):
            return False
        if self.config.pre_action_key:
            self._press_key(self.config.pre_action_key)
        return not self._stop_flag.is_set()

    def _do_cast(self) -> bool:
        self._set_state(FishingState.CAST, 0.0, 0.0)
        self._press_key(self.config.cast_key)
        return not self._stop_flag.is_set()

    def _do_wait_land(self) -> bool:
        return self._sleep_with_state(
            FishingState.WAIT_LAND, self.config.wait_land_s
        )

    def _do_detect(self) -> Optional[dict]:
        """返回触发的检测(confidence 最高);超时 / 被停返回 None。
        本阶段新建 tracker → 进入 DETECTING;退出时清空 tracker → 让识别线程的回调进入"空转"模式。
        ScreenRecognition 自身常驻不停,预览仍在跑。
        """
        self._reset_trigger()
        self._tracker = DisplacementTracker(
            displacement_ratio=DISPLACEMENT_RATIO,
            min_displacement_px=MIN_DISPLACEMENT_PX,
            window_seconds=WINDOW_SECONDS,
            trigger_cooldown_s=TRIGGER_COOLDOWN_S,
        )
        deadline = time.time() + self.config.detect_timeout_s
        total = self.config.detect_timeout_s

        try:
            while not self._stop_flag.is_set():
                now = time.time()
                if now >= deadline:
                    return None
                elapsed = total - (deadline - now)
                self._set_state(FishingState.DETECTING, elapsed, total)
                with self._trigger_lock:
                    target = self._triggered_target
                if target is not None:
                    return target
                time.sleep(SLEEP_TICK_S)
            return None
        finally:
            # tracker 置空,后续非 DETECTING 阶段 _on_raw_detections 看到 None 直接 return
            self._tracker = None

    def _do_triggered_wait(self) -> bool:
        return self._sleep_with_state(
            FishingState.TRIGGERED, self.config.post_trigger_wait_s
        )

    def _do_pick_up(self, target: dict) -> None:
        self._set_state(FishingState.PICK_UP, 0.0, 0.0)
        center = target.get("center", (0, 0))
        try:
            cx, cy = int(center[0]), int(center[1])
            if self.config.capture_mode == "window":
                # 后台:detection.center 是「喂给 YOLO 的帧」局部坐标(整窗客户区,或子区域)。
                # 子区域模式 + 子区域偏移 = 客户区坐标;整窗则偏移 0。
                # 抓帧已裁剪掉标题栏(window_io 客户区对齐),故无竖直偏移。
                if self.config.window_region is not None:
                    cx += int(self.config.window_region[0])
                    cy += int(self.config.window_region[1])
                window_io.post_right_click(self._hwnd, cx, cy)
                logger.info(
                    "后台右键拾取 @客户区(%d, %d)  hwnd=0x%08X  center_local=%s",
                    cx, cy, self._hwnd, center,
                )
            else:
                # 前台:detection.center 是截图局部坐标;选区识别须 + monitor_area 偏移
                # 才是屏幕绝对坐标(双屏副屏偏移可能 >= 1920,无此修正会点错屏)。
                if self.config.monitor_area is not None:
                    cx += int(self.config.monitor_area[0])
                    cy += int(self.config.monitor_area[1])
                pyautogui.rightClick(cx, cy)
                logger.info("右键拾取 @(%d, %d)  target_center_local=%s", cx, cy, center)
        except Exception as e:
            logger.error("右键拾取失败 @%s: %s", center, e)
            if self.on_error:
                self.on_error(f"右键拾取失败: {e}")

    def _do_post_process(self) -> None:
        self._set_state(FishingState.POST_PROCESS, 0.0, 0.0)
        if self.config.post_action_key:
            self._press_key(self.config.post_action_key)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _sleep_with_state(self, state: FishingState, total_s: float) -> bool:
        """带进度刷新的可中断 sleep。返回 True=完成,False=被 stop 中断。"""
        if total_s <= 0:
            self._set_state(state, 0.0, 0.0)
            return not self._stop_flag.is_set()

        start = time.time()
        deadline = start + total_s
        while not self._stop_flag.is_set():
            now = time.time()
            elapsed = now - start
            if now >= deadline:
                self._set_state(state, total_s, total_s)
                return True
            self._set_state(state, elapsed, total_s)
            remaining = deadline - now
            time.sleep(min(SLEEP_TICK_S, remaining))
        return False

    def _press_key(self, key: str) -> None:
        key = (key or "").strip()
        if not key:
            return
        try:
            if self.config.capture_mode == "window":
                # 后台:PostMessage 投键到窗口句柄,不抢焦点
                ok = window_io.post_key(self._hwnd, key)
                if not ok:
                    logger.error("后台投键 %r 失败(hwnd=0x%08X)", key, self._hwnd)
                    if self.on_error:
                        self.on_error(f"后台投键 {key!r} 失败")
            else:
                pyautogui.press(key)
        except Exception as e:
            logger.error("按键 %r 失败: %s", key, e)
            if self.on_error:
                self.on_error(f"按键 {key!r} 失败: {e}")

    def _set_state(
        self, state: FishingState, elapsed: float, total: float
    ) -> None:
        self._state = state
        if self.on_state_change:
            try:
                self.on_state_change(state, self._round_idx, elapsed, total)
            except Exception as e:
                logger.error("on_state_change 回调出错: %s", e)

    def _emit_round_complete(self) -> None:
        if self.on_round_complete:
            try:
                self.on_round_complete(self.stats.snapshot())
            except Exception as e:
                logger.error("on_round_complete 回调出错: %s", e)

    # ------------------------------------------------------------------
    # 识别 / 位移
    # ------------------------------------------------------------------

    def _ensure_recognition_started(self) -> None:
        """在 _run 入口调一次。识别在整个钓鱼期间常驻,供 UI 持续预览。"""
        if self._recognition is None:
            self._recognition = ScreenRecognition(
                model_path=self.config.model_path,
                confidence_threshold=self.config.confidence,
                click_enabled=False,                  # 钓鱼自己 rightClick,不走 ScreenRecognition 的左键
                device=self.config.device,
            )
            self._recognition.on_recognition_result = self._on_raw_detections
            self._recognition.on_error = lambda e: (
                self.on_error and self.on_error(f"识别错误: {e}")
            )
            if self.on_frame is not None:
                self._recognition.on_frame_result = self.on_frame

        if self.config.capture_mode == "window":
            # 后台模式:先解析 hwnd(按标题,容忍游戏重启换句柄),配置窗口捕获
            self._resolve_hwnd()
            self._recognition.set_window_capture(self._hwnd, self.config.window_region)
        elif self.config.monitor_area:
            self._recognition.set_monitor_area(*self.config.monitor_area)
        else:
            self._recognition.use_full_screen_monitor()

        if not self._recognition.is_running:
            self._recognition.start_recognition()

    def _resolve_hwnd(self) -> int:
        """后台模式:按窗口标题重解析 hwnd(句柄随游戏重启变化);
        标题为空则沿用初始 config.hwnd。返回解析结果(可能 0=找不到)。"""
        hwnd = self.config.hwnd
        if self.config.window_title:
            found = window_io.find_window(self.config.window_title)
            if found:
                hwnd = found
        self._hwnd = hwnd
        return hwnd

    def _check_window_alive(self) -> bool:
        """后台模式每轮校验目标窗口存活;前台模式恒 True。
        窗口丢失(关闭/重启解析不到)→ on_error + 返回 False 让主循环退出(F2.16.7)。"""
        if self.config.capture_mode != "window":
            return True

        hwnd = self._resolve_hwnd()
        if not window_io.is_window(hwnd):
            msg = f"游戏窗口丢失({self.config.window_title or hex(self.config.hwnd)})"
            logger.warning(msg)
            if self.on_error:
                self.on_error(msg)
            return False

        if window_io.is_minimized(hwnd):
            # 最小化 = 系统停渲,抓不到画面。明确报错引导,而非静默空转。
            msg = "游戏窗口已最小化,无法后台捕获;请勿最小化,改用遮挡 / 虚拟桌面 / 移到屏幕外"
            logger.warning(msg)
            if self.on_error:
                self.on_error(msg)
            return False

        # 重解析后句柄变了(游戏重启)→ 同步给识别管线,继续钓
        if self._recognition is not None and self._recognition.hwnd != hwnd:
            self._recognition.set_window_capture(hwnd, self.config.window_region)
        return True

    def _teardown_recognition(self) -> None:
        if self._recognition is not None and self._recognition.is_running:
            self._recognition.stop_recognition()
        self._recognition = None
        self._tracker = None

    def _reset_trigger(self) -> None:
        with self._trigger_lock:
            self._triggered_target = None

    def _on_raw_detections(self, detections: list) -> None:
        """ScreenRecognition 推理线程回调。喂 tracker 并暂存首次触发目标。"""
        tracker = self._tracker
        if tracker is None or self._stop_flag.is_set():
            return
        try:
            triggered = tracker.update(detections)
        except Exception as e:
            logger.error("tracker.update 出错: %s", e)
            return
        if not triggered:
            return

        # D4:单类别 wow_fish.pt,取 confidence 最高;通常 len == 1
        target = max(triggered, key=lambda d: float(d.get("confidence", 0.0)))
        with self._trigger_lock:
            if self._triggered_target is not None:
                return  # 已经触发,本轮后续帧忽略,避免抢覆盖
            self._triggered_target = target

        if self.on_trigger:
            try:
                self.on_trigger(target)
            except Exception as e:
                logger.error("on_trigger 回调出错: %s", e)
