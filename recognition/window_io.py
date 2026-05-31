#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
窗口级 IO 后端(Windows 专用,ctypes 直调 user32/gdi32,零新依赖)。

为「后台钓鱼」路线提供两类能力,都**不要求目标窗口在前台 / 不抢焦点**:

  - 捕获:`capture_window(hwnd)` 用 PrintWindow(PW_RENDERFULLCONTENT) 让窗口自渲染一帧,
          即使被其他窗口遮挡也能抓到真实画面(前提:游戏为窗口 / 无边框模式,
          且后台仍在渲染 —— WoW 需 /console maxfpsbk 30)。
  - 输入:`post_key` / `post_right_click` / `post_left_click` 用 PostMessage 把键鼠消息
          直接投递到窗口句柄,不经过系统焦点。

⚠ 已知边界(详见 docs/SPEC 后续补充):
  - PrintWindow 对**独占全屏**的 DX 游戏通常返回黑屏 → 需游戏切窗口化,或上层换 WGC。
  - WoW「右键与世界交互」依赖真实光标做 3D 射线拾取,PostMessage 合成右键**可能无效**;
    这是后台路线的生死线,需实测(见 BackgroundIoTestDialog)。

坐标约定:所有 (x, y) 均为**客户区相对坐标**(以窗口客户区左上角为原点),
不是屏幕绝对坐标。capture_window 返回的图像尺寸 == 客户区尺寸,二者天然对齐。
"""

from __future__ import annotations

import logging
import sys
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

# 非 Windows 平台:导出空实现,import 不炸(便于在别处无脑 import)
if not IS_WINDOWS:  # pragma: no cover - 仅 win32 运行
    def is_supported() -> bool:
        return False

    def enum_windows() -> List[Tuple[int, str]]:
        return []

    def find_window(title_substr: str) -> int:
        return 0

    def get_client_size(hwnd: int) -> Tuple[int, int]:
        return (0, 0)

    def capture_window(hwnd: int):
        return None

    def is_window(hwnd: int) -> bool:
        return False

    def is_minimized(hwnd: int) -> bool:
        return False

    def post_key(hwnd: int, key: str) -> bool:
        return False

    def post_right_click(hwnd: int, x: int, y: int) -> bool:
        return False

    def post_left_click(hwnd: int, x: int, y: int) -> bool:
        return False

else:
    import ctypes
    from ctypes import wintypes

    import numpy as np

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    # --- Win32 常量 ---
    PW_RENDERFULLCONTENT = 0x00000002  # 关键:让 DX 窗口把真实内容渲染进 DC
    DIB_RGB_COLORS = 0

    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONDOWN = 0x0204
    WM_RBUTTONUP = 0x0205
    WM_MOUSEMOVE = 0x0200
    MK_LBUTTON = 0x0001
    MK_RBUTTON = 0x0002

    MAPVK_VK_TO_VSC = 0

    # 命名键 → VK 码(钓鱼键不止单字符:抛竿可能是 f1 / space / numpad1 等)。
    # 单字符走 VkKeyScanW 解析;多字符名查此表。键名小写,与 keyboard / pyautogui 习惯一致。
    _NAMED_VK = {
        "space": 0x20, "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B,
        "tab": 0x09, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
        "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
        "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
        "insert": 0x2D, "ins": 0x2D,
    }
    _NAMED_VK.update({f"f{i}": 0x6F + i for i in range(1, 25)})       # f1..f24 = 0x70..0x87
    _NAMED_VK.update({f"numpad{i}": 0x60 + i for i in range(0, 10)})  # numpad0..9 = 0x60..0x69

    # --- 函数签名(显式声明,64 位下指针不被截断) ---
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.GetWindowDC.restype = wintypes.HDC
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.PrintWindow.restype = wintypes.BOOL
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    ]
    user32.VkKeyScanW.restype = ctypes.c_short
    user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
    user32.MapVirtualKeyW.restype = wintypes.UINT
    user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]

    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT,
    ]

    # 进程级 DPI 感知:不开的话高分屏下 GetClientRect / PrintWindow 尺寸会和实际像素错位
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    class _BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    _WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _make_lparam(low: int, high: int) -> int:
        return (high & 0xFFFF) << 16 | (low & 0xFFFF)

    def is_supported() -> bool:
        return True

    def enum_windows() -> List[Tuple[int, str]]:
        """枚举所有可见且有标题的顶层窗口,返回 [(hwnd, title), ...]。"""
        results: List[Tuple[int, str]] = []

        def _cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if title:
                results.append((int(hwnd), title))
            return True

        user32.EnumWindows(_WNDENUMPROC(_cb), 0)
        return results

    def find_window(title_substr: str) -> int:
        """按标题子串(不分大小写)模糊匹配第一个可见窗口,返回 hwnd(找不到 0)。"""
        target = (title_substr or "").lower()
        for hwnd, title in enum_windows():
            if target in title.lower():
                return hwnd
        return 0

    def is_window(hwnd: int) -> bool:
        """hwnd 是否仍是有效窗口(游戏关闭 / 重启后会失效)。"""
        return bool(hwnd) and bool(user32.IsWindow(hwnd))

    def is_minimized(hwnd: int) -> bool:
        """窗口是否最小化(IsIconic)。最小化时系统停止渲染,PrintWindow 抓不到画面,
        必须由调用方明确处理(报错引导用户改用遮挡 / 虚拟桌面,而非静默黑屏)。"""
        return bool(hwnd) and bool(user32.IsIconic(hwnd))

    def get_client_size(hwnd: int) -> Tuple[int, int]:
        rect = wintypes.RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return (0, 0)
        return (rect.right - rect.left, rect.bottom - rect.top)

    def _client_offset_in_window(hwnd: int, win_rect: "wintypes.RECT") -> Tuple[int, int]:
        """客户区左上角相对窗口左上角的像素偏移(标题栏高 + 边框宽)。
        PrintWindow 按**窗口**原点渲染,客户区坐标(PostMessage 用)按**客户区**原点;
        二者差这个偏移,抓帧后必须按它裁剪才能让图坐标 == 客户区坐标。"""
        pt = wintypes.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt))  # 客户区 (0,0) → 屏幕坐标
        return (pt.x - win_rect.left, pt.y - win_rect.top)

    def capture_window(hwnd: int) -> Optional["np.ndarray"]:
        """PrintWindow 抓一帧,返回 BGR numpy 数组(与 screen_recognition 一致);失败返回 None。

        关键:按**整窗**尺寸渲染(PrintWindow 含标题栏/边框,原点在窗口左上角),
        再裁剪出纯客户区。返回图尺寸 == 客户区尺寸,且 (0,0) 严格对齐客户区 (0,0)
        —— 这样 detection 坐标可直接喂给 post_right_click,无竖直偏移。
        """
        if not hwnd or not user32.IsWindow(hwnd):
            return None

        wr = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(wr)):
            return None
        ww, wh = wr.right - wr.left, wr.bottom - wr.top
        cw, ch = get_client_size(hwnd)
        if ww <= 0 or wh <= 0 or cw <= 0 or ch <= 0:
            return None
        off_x, off_y = _client_offset_in_window(hwnd, wr)

        hwnd_dc = user32.GetWindowDC(hwnd)
        if not hwnd_dc:
            return None
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, ww, wh)
        old = gdi32.SelectObject(mem_dc, bitmap)
        try:
            ok = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
            if not ok:
                logger.warning("PrintWindow 失败 hwnd=0x%08X(可能独占全屏 / 权限不足)", hwnd)
                return None

            bmi = _BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
            bmi.biWidth = ww
            bmi.biHeight = -wh  # 负 = 自上而下,省翻转
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0  # BI_RGB

            buf = ctypes.create_string_buffer(ww * wh * 4)
            got = gdi32.GetDIBits(
                mem_dc, bitmap, 0, wh, buf, ctypes.byref(bmi), DIB_RGB_COLORS
            )
            if got == 0:
                logger.warning("GetDIBits 返回 0 hwnd=0x%08X", hwnd)
                return None

            arr = np.frombuffer(buf, dtype=np.uint8).reshape((wh, ww, 4))
            # 裁剪出客户区(防越界 clamp),BGRA → BGR,copy 取得数据所有权
            y0 = max(0, off_y)
            x0 = max(0, off_x)
            y1 = min(wh, y0 + ch)
            x1 = min(ww, x0 + cw)
            client = arr[y0:y1, x0:x1, :3]
            return client.copy()
        finally:
            gdi32.SelectObject(mem_dc, old)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(hwnd, hwnd_dc)

    def _vk_and_scan(key: str) -> Optional[Tuple[int, int]]:
        """解析按键 → (vk, scancode)。单字符走 VkKeyScanW,多字符名查 _NAMED_VK。"""
        if not key:
            return None
        if len(key) == 1:
            vk_scan = user32.VkKeyScanW(key)
            if vk_scan == -1:
                return None
            vk = vk_scan & 0xFF
        else:
            vk = _NAMED_VK.get(key.lower())
            if vk is None:
                return None
        scancode = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
        return vk, scancode

    def post_key(hwnd: int, key: str) -> bool:
        """PostMessage 投递一次完整按键(含 scancode 的 lParam,部分游戏校验它)。
        key 为单字符(如 '-' / '1' / 'e')或命名键(如 'space' / 'f1' / 'numpad1')。
        成功投递返回 True(不代表游戏一定响应)。"""
        if not hwnd or not user32.IsWindow(hwnd):
            return False
        parsed = _vk_and_scan(key)
        if parsed is None:
            logger.warning("无法解析按键 %r", key)
            return False
        vk, scancode = parsed
        down = 1 | (scancode << 16)
        up = 1 | (scancode << 16) | (1 << 30) | (1 << 31)
        r1 = user32.PostMessageW(hwnd, WM_KEYDOWN, vk, down)
        r2 = user32.PostMessageW(hwnd, WM_KEYUP, vk, up)
        return bool(r1 and r2)

    def _post_click(hwnd: int, x: int, y: int, down_msg: int, up_msg: int, mk: int) -> bool:
        if not hwnd or not user32.IsWindow(hwnd):
            return False
        lp = _make_lparam(int(x), int(y))
        user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lp)
        r1 = user32.PostMessageW(hwnd, down_msg, mk, lp)
        r2 = user32.PostMessageW(hwnd, up_msg, 0, lp)
        return bool(r1 and r2)

    def post_right_click(hwnd: int, x: int, y: int) -> bool:
        """投递右键到客户区 (x, y)。WoW 世界交互可能无效(3D 射线靠真实光标),需实测。"""
        return _post_click(hwnd, x, y, WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON)

    def post_left_click(hwnd: int, x: int, y: int) -> bool:
        """投递左键到客户区 (x, y)。"""
        return _post_click(hwnd, x, y, WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON)
