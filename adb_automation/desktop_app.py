from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\desktop_app.pyc')

del _exec_recovered_module

import sys as _sys
import queue as _queue
import threading as _threading
from contextlib import suppress as _suppress
from datetime import datetime as _datetime
from pathlib import Path as _Path
from PIL import ImageDraw as _ImageDraw
from .adb import RUNTIME_ROOT as _ADB_RUNTIME_ROOT


PROJECT_ROOT = _ADB_RUNTIME_ROOT


def _asset_path(name):
    roots = []
    if getattr(_sys, "frozen", False):
        roots.append(_Path(_sys.executable).resolve().parent)
    bundle_root = getattr(_sys, "_MEIPASS", None)
    if bundle_root:
        roots.append(_Path(bundle_root))
    roots.append(_Path(__file__).resolve().parents[1])
    roots.append(_Path.cwd())
    for root in roots:
        path = root / "assets" / name
        if path.is_file():
            return path
    return None


def _load_asset_photo(name, max_size):
    path = _asset_path(name)
    if path is None:
        return None
    try:
        image = Image.open(path).convert("RGBA")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception:
        return None


def _set_window_icon(root):
    photo = _load_asset_photo("app_header.png", (64, 64))
    if photo is None:
        return
    root.iconphoto(True, photo)
    root._adb_automation_icon_photo = photo


class _WindowsTrayIcon:
    _WM_CLOSE = 0x0010

    def __init__(self, tooltip, icon_path, on_show, on_exit):
        self.tooltip = tooltip
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_exit = on_exit
        self._hwnd = None
        self._hicon = None
        self._thread = None
        self._ready = _threading.Event()
        self._started = False
        self._wndproc = None

    def start(self):
        if not _sys.platform.startswith("win"):
            return False
        self._thread = _threading.Thread(target=self._run, name="ADBTrayIcon", daemon=True)
        self._thread.start()
        self._ready.wait(2)
        return self._started

    def stop(self):
        if not self._hwnd or not _sys.platform.startswith("win"):
            return
        with _suppress(Exception):
            import ctypes as _ctypes

            _ctypes.windll.user32.PostMessageW(self._hwnd, self._WM_CLOSE, 0, 0)

    def _dispatch(self, callback):
        try:
            callback()
        except Exception:
            pass

    def _run(self):
        import ctypes as _ctypes
        from ctypes import wintypes as _wintypes

        WM_DESTROY = 0x0002
        WM_COMMAND = 0x0111
        WM_LBUTTONUP = 0x0202
        WM_LBUTTONDBLCLK = 0x0203
        WM_RBUTTONUP = 0x0205
        WM_USER = 0x0400
        WM_TRAYICON = WM_USER + 20
        WM_NULL = 0x0000

        NIM_ADD = 0x00000000
        NIM_DELETE = 0x00000002
        NIF_MESSAGE = 0x00000001
        NIF_ICON = 0x00000002
        NIF_TIP = 0x00000004

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        MF_STRING = 0x00000000
        MF_SEPARATOR = 0x00000800
        TPM_RIGHTBUTTON = 0x00000002

        IDM_SHOW = 1001
        IDM_EXIT = 1002

        _LRESULT = getattr(_wintypes, "LRESULT", _ctypes.c_ssize_t)
        _WNDPROC = _ctypes.WINFUNCTYPE(
            _LRESULT,
            _wintypes.HWND,
            _wintypes.UINT,
            _wintypes.WPARAM,
            _wintypes.LPARAM,
        )

        class _GUID(_ctypes.Structure):
            _fields_ = [
                ("Data1", _wintypes.DWORD),
                ("Data2", _wintypes.WORD),
                ("Data3", _wintypes.WORD),
                ("Data4", _ctypes.c_ubyte * 8),
            ]

        class _WNDCLASSW(_ctypes.Structure):
            _fields_ = [
                ("style", _wintypes.UINT),
                ("lpfnWndProc", _WNDPROC),
                ("cbClsExtra", _ctypes.c_int),
                ("cbWndExtra", _ctypes.c_int),
                ("hInstance", _wintypes.HANDLE),
                ("hIcon", _wintypes.HANDLE),
                ("hCursor", _wintypes.HANDLE),
                ("hbrBackground", _wintypes.HANDLE),
                ("lpszMenuName", _wintypes.LPCWSTR),
                ("lpszClassName", _wintypes.LPCWSTR),
            ]

        class _NOTIFYICONDATAW(_ctypes.Structure):
            _fields_ = [
                ("cbSize", _wintypes.DWORD),
                ("hWnd", _wintypes.HWND),
                ("uID", _wintypes.UINT),
                ("uFlags", _wintypes.UINT),
                ("uCallbackMessage", _wintypes.UINT),
                ("hIcon", _wintypes.HANDLE),
                ("szTip", _wintypes.WCHAR * 128),
                ("dwState", _wintypes.DWORD),
                ("dwStateMask", _wintypes.DWORD),
                ("szInfo", _wintypes.WCHAR * 256),
                ("uVersion", _wintypes.UINT),
                ("szInfoTitle", _wintypes.WCHAR * 64),
                ("dwInfoFlags", _wintypes.DWORD),
                ("guidItem", _GUID),
                ("hBalloonIcon", _wintypes.HANDLE),
            ]

        user32 = _ctypes.windll.user32
        shell32 = _ctypes.windll.shell32
        kernel32 = _ctypes.windll.kernel32

        kernel32.GetModuleHandleW.restype = _wintypes.HANDLE
        kernel32.GetModuleHandleW.argtypes = [_wintypes.LPCWSTR]
        user32.RegisterClassW.argtypes = [_ctypes.POINTER(_WNDCLASSW)]
        user32.CreateWindowExW.restype = _wintypes.HWND
        user32.CreateWindowExW.argtypes = [
            _wintypes.DWORD,
            _wintypes.LPCWSTR,
            _wintypes.LPCWSTR,
            _wintypes.DWORD,
            _ctypes.c_int,
            _ctypes.c_int,
            _ctypes.c_int,
            _ctypes.c_int,
            _wintypes.HWND,
            _wintypes.HANDLE,
            _wintypes.HANDLE,
            _ctypes.c_void_p,
        ]
        user32.LoadImageW.restype = _wintypes.HANDLE
        user32.LoadImageW.argtypes = [_wintypes.HANDLE, _wintypes.LPCWSTR, _wintypes.UINT, _ctypes.c_int, _ctypes.c_int, _wintypes.UINT]
        user32.LoadIconW.restype = _wintypes.HANDLE
        user32.LoadIconW.argtypes = [_wintypes.HANDLE, _wintypes.LPCWSTR]
        user32.CreatePopupMenu.restype = _wintypes.HANDLE
        user32.AppendMenuW.argtypes = [_wintypes.HANDLE, _wintypes.UINT, _ctypes.c_size_t, _wintypes.LPCWSTR]
        user32.TrackPopupMenu.argtypes = [_wintypes.HANDLE, _wintypes.UINT, _ctypes.c_int, _ctypes.c_int, _ctypes.c_int, _wintypes.HWND, _ctypes.c_void_p]
        user32.SetForegroundWindow.argtypes = [_wintypes.HWND]
        user32.DestroyMenu.argtypes = [_wintypes.HANDLE]
        user32.DestroyWindow.argtypes = [_wintypes.HWND]
        user32.DestroyIcon.argtypes = [_wintypes.HANDLE]
        user32.PostMessageW.argtypes = [_wintypes.HWND, _wintypes.UINT, _wintypes.WPARAM, _wintypes.LPARAM]
        user32.PostQuitMessage.argtypes = [_ctypes.c_int]
        user32.GetMessageW.argtypes = [_ctypes.POINTER(_wintypes.MSG), _wintypes.HWND, _wintypes.UINT, _wintypes.UINT]
        user32.TranslateMessage.argtypes = [_ctypes.POINTER(_wintypes.MSG)]
        user32.DispatchMessageW.argtypes = [_ctypes.POINTER(_wintypes.MSG)]
        user32.DefWindowProcW.restype = _LRESULT
        user32.DefWindowProcW.argtypes = [_wintypes.HWND, _wintypes.UINT, _wintypes.WPARAM, _wintypes.LPARAM]
        shell32.Shell_NotifyIconW.restype = _wintypes.BOOL
        shell32.Shell_NotifyIconW.argtypes = [_wintypes.DWORD, _ctypes.POINTER(_NOTIFYICONDATAW)]

        hinstance = kernel32.GetModuleHandleW(None)
        class_name = f"ADBTrayIconWindow{ id(self) }"

        def dispatch_show():
            self._dispatch(self.on_show)

        def dispatch_exit():
            self._dispatch(self.on_exit)

        def show_menu(hwnd):
            point = _wintypes.POINT()
            user32.GetCursorPos(_ctypes.byref(point))
            menu = user32.CreatePopupMenu()
            if not menu:
                return
            user32.AppendMenuW(menu, MF_STRING, IDM_SHOW, "显示")
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, IDM_EXIT, "退出应用")
            user32.SetForegroundWindow(hwnd)
            user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON, point.x, point.y, 0, hwnd, None)
            user32.PostMessageW(hwnd, WM_NULL, 0, 0)
            user32.DestroyMenu(menu)

        def remove_icon(hwnd):
            data = _NOTIFYICONDATAW()
            data.cbSize = _ctypes.sizeof(_NOTIFYICONDATAW)
            data.hWnd = hwnd
            data.uID = 1
            shell32.Shell_NotifyIconW(NIM_DELETE, _ctypes.byref(data))

        @_WNDPROC
        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAYICON:
                event = int(lparam)
                if event in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    dispatch_show()
                    return 0
                if event == WM_RBUTTONUP:
                    show_menu(hwnd)
                    return 0
            if msg == WM_COMMAND:
                command_id = int(wparam) & 0xFFFF
                if command_id == IDM_SHOW:
                    dispatch_show()
                    return 0
                if command_id == IDM_EXIT:
                    dispatch_exit()
                    return 0
            if msg == self._WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if msg == WM_DESTROY:
                remove_icon(hwnd)
                if self._hicon:
                    user32.DestroyIcon(self._hicon)
                    self._hicon = None
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = wndproc
        window_class = _WNDCLASSW()
        window_class.lpfnWndProc = wndproc
        window_class.hInstance = hinstance
        window_class.lpszClassName = class_name

        try:
            if not user32.RegisterClassW(_ctypes.byref(window_class)):
                return
            hwnd = user32.CreateWindowExW(0, class_name, class_name, 0, 0, 0, 0, 0, None, None, hinstance, None)
            if not hwnd:
                return
            self._hwnd = hwnd

            if self.icon_path:
                self._hicon = user32.LoadImageW(None, str(self.icon_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            if not self._hicon:
                self._hicon = user32.LoadIconW(None, _ctypes.cast(_ctypes.c_void_p(32512), _wintypes.LPCWSTR))

            data = _NOTIFYICONDATAW()
            data.cbSize = _ctypes.sizeof(_NOTIFYICONDATAW)
            data.hWnd = hwnd
            data.uID = 1
            data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            data.uCallbackMessage = WM_TRAYICON
            data.hIcon = self._hicon
            data.szTip = self.tooltip[:127]
            if not shell32.Shell_NotifyIconW(NIM_ADD, _ctypes.byref(data)):
                user32.DestroyWindow(hwnd)
                return

            self._started = True
            self._ready.set()

            msg = _wintypes.MSG()
            while user32.GetMessageW(_ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(_ctypes.byref(msg))
                user32.DispatchMessageW(_ctypes.byref(msg))
        finally:
            self._ready.set()


def _install_tray_mode(app, root):
    if getattr(root, "_adb_automation_tray_installed", False):
        return
    tray_actions = _queue.Queue()

    def show_window():
        try:
            root.deiconify()
            root.state("normal")
            root.lift()
            root.focus_force()
        except Exception:
            pass

    def hide_to_tray():
        try:
            root.withdraw()
        except Exception:
            pass

    def exit_application():
        tray = getattr(root, "_adb_automation_tray", None)
        if tray is not None:
            tray.stop()
        with _suppress(Exception):
            runner = getattr(app, "schedule_runner", None)
            if runner is not None:
                runner.request_stop()
        with _suppress(Exception):
            stop_event = getattr(app, "stop_event", None)
            if stop_event is not None:
                stop_event.set()
        with _suppress(Exception):
            root.after(50, root.destroy)

    def poll_tray_actions():
        try:
            while True:
                action = tray_actions.get_nowait()
                if action == "show":
                    show_window()
                elif action == "exit":
                    exit_application()
        except _queue.Empty:
            pass
        with _suppress(Exception):
            root.after(200, poll_tray_actions)

    icon_path = _asset_path("app_icon.ico")
    tray = _WindowsTrayIcon("三角洲助手", icon_path, lambda: tray_actions.put("show"), lambda: tray_actions.put("exit"))
    if not tray.start():
        return

    def cleanup_tray(event=None):
        if event is not None and event.widget is not root:
            return
        tray.stop()

    root._adb_automation_tray = tray
    root._adb_automation_tray_installed = True
    root.protocol("WM_DELETE_WINDOW", hide_to_tray)
    root.bind("<Destroy>", cleanup_tray, add="+")
    root.after(200, poll_tray_actions)


def _patch_desktop_branding():
    original_init = DesktopApp.__init__
    original_page_schedule = DesktopApp._page_schedule

    def init_with_icon(self, root):
        original_init(self, root)
        _set_window_icon(root)
        _install_tray_mode(self, root)

    def build_sidebar_with_image(self, parent):
        brand = tk.Frame(parent, bg=self.colors["sidebar"])
        brand.pack(anchor="w", padx=18, pady=(16, 14))

        photo = _load_asset_photo("app_header.png", (58, 58))
        if photo is not None:
            image_label = tk.Label(brand, image=photo, bg=self.colors["sidebar"], bd=0)
            image_label.image = photo
            image_label.pack(side="left", padx=(0, 10))
            self._adb_automation_header_photo = photo

        tk.Label(
            brand,
            text="三角洲\n助手",
            bg=self.colors["sidebar"],
            fg="#ffffff",
            justify="left",
            font=("Microsoft YaHei UI", 18, "bold"),
        ).pack(side="left")

        pages = [
            ("device", "设备与坐标"),
            ("qq", "QQ 切换"),
            ("delta", "三角洲制作"),
            ("full", "完整流程"),
            ("schedule", "定时任务"),
            ("logs", "日志与截图"),
        ]
        for key, label in pages:
            button = tk.Button(
                parent,
                text=label,
                command=lambda page=key: self._show_page(page),
                anchor="w",
                bg=self.colors["sidebar"],
                fg="#cbd5e1",
                activebackground=self.colors["sidebar_hover"],
                activeforeground="#ffffff",
                bd=0,
                padx=18,
                pady=12,
                cursor="hand2",
                font=("Microsoft YaHei UI", 10, "bold"),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = button

        tk.Label(
            parent,
            text="仅保留当前已验证坐标\n读取 device_profiles\\xiaomi_2211133c.txt",
            bg=self.colors["sidebar"],
            fg="#94a3b8",
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(side="bottom", anchor="w", padx=20, pady=22)

    def page_schedule_with_four_times(self, parent):
        original_page_schedule(self, parent)
        replacement = "例如 02:00,08:00,14:00,20:00，可填 1-4 个时间"

        def update_hint(widget):
            with _suppress(Exception):
                text = widget.cget("text")
                if isinstance(text, str) and "必须 2 个时间" in text:
                    widget.configure(text=replacement)
            for child in widget.winfo_children():
                update_hint(child)

        update_hint(parent)

    DesktopApp.__init__ = init_with_icon
    DesktopApp._build_sidebar = build_sidebar_with_image
    DesktopApp._page_schedule = page_schedule_with_four_times


_patch_desktop_branding()
del _patch_desktop_branding


_SCHEDULE_MODE_LABELS = {
    "daily_times": "每天固定时间",
    "finish_interval": "结束后倒计时",
}


def _schedule_mode_to_label(mode):
    return _SCHEDULE_MODE_LABELS.get(str(mode).strip(), _SCHEDULE_MODE_LABELS["daily_times"])


def _schedule_label_to_mode(label):
    for mode, mode_label in _SCHEDULE_MODE_LABELS.items():
        if label == mode_label:
            return mode
    return "daily_times"


def _format_interval_value(value):
    try:
        hours = float(str(value).strip())
    except (TypeError, ValueError):
        hours = 8.0
    if hours.is_integer():
        return str(int(hours))
    return f"{hours:g}"


def _format_interval_minutes_value(value):
    try:
        minutes = int(str(value).strip())
    except (TypeError, ValueError):
        minutes = 0
    return str(max(0, min(59, minutes)))


def _read_interval_hours(value):
    try:
        hours = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("结束后倒计时间隔必须是数字小时，例如 8 或 9") from exc
    if hours < 0 or hours > 24:
        raise ValueError("结束后倒计时小时必须在 0-24 之间")
    if hours.is_integer():
        return int(hours)
    return hours


def _read_interval_minutes(value):
    try:
        minutes = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("结束后倒计时分钟必须是 0-59 的整数") from exc
    if minutes < 0 or minutes > 59:
        raise ValueError("结束后倒计时分钟必须是 0-59 的整数")
    return minutes


def _format_last_finished_value(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        from .scheduler import normalize_last_finished_at

        return normalize_last_finished_at(text)
    except Exception:
        return text


def _read_last_finished_at(value):
    text = str(value or "").strip()
    if not text:
        return ""
    from .scheduler import normalize_last_finished_at

    return normalize_last_finished_at(text)


def _patch_schedule_interval_mode():
    original_init = DesktopApp.__init__
    original_schedule_config = DesktopApp._schedule_config

    def init_with_schedule_mode(self, root):
        original_init(self, root)
        config = self._load_config_safely()
        self.schedule_mode_var = tk.StringVar(value=_schedule_mode_to_label(config.get("mode", "daily_times")))
        self.schedule_interval_hours_var = tk.StringVar(value=_format_interval_value(config.get("interval_hours", 8)))
        self.schedule_interval_minutes_var = tk.StringVar(value=_format_interval_minutes_value(config.get("interval_minutes", 0)))
        self.schedule_last_finished_at_var = tk.StringVar(value=_format_last_finished_value(config.get("last_finished_at", "")))

    def schedule_config_with_interval(self):
        config = original_schedule_config(self)
        mode_var = getattr(self, "schedule_mode_var", None)
        mode_label = mode_var.get() if mode_var is not None else "每天固定时间"
        interval_var = getattr(self, "schedule_interval_hours_var", None)
        interval_value = interval_var.get() if interval_var is not None else "8"
        interval_minutes_var = getattr(self, "schedule_interval_minutes_var", None)
        interval_minutes_value = interval_minutes_var.get() if interval_minutes_var is not None else "0"
        last_finished_var = getattr(self, "schedule_last_finished_at_var", None)
        last_finished_value = last_finished_var.get() if last_finished_var is not None else ""
        mode = _schedule_label_to_mode(mode_label)
        config["mode"] = mode
        config["interval_hours"] = _read_interval_hours(interval_value)
        config["interval_minutes"] = _read_interval_minutes(interval_minutes_value)
        config["last_finished_at"] = _read_last_finished_at(last_finished_value)
        if config["mode"] == "finish_interval":
            total_minutes = int(round(float(config["interval_hours"]) * 60)) + int(config["interval_minutes"])
            if total_minutes < 1 or total_minutes > 24 * 60:
                raise ValueError("结束后倒计时间隔必须在 1 分钟到 24 小时之间")
        return config

    def page_schedule_with_interval(self, parent):
        self._page_title(
            parent,
            "定时任务",
            "定时会使用当前页面的 serial、坐标预设、账号数、轮数和制作台勾选。",
        )
        form = self._form(parent)
        self._combo_row(
            form,
            0,
            "定时目标",
            self.schedule_target_var,
            [SCHEDULE_TARGETS[key] for key in ("full_flow", "delta_force", "qq_switch")],
        )
        self._combo_row(
            form,
            1,
            "时间模式",
            self.schedule_mode_var,
            list(_SCHEDULE_MODE_LABELS.values()),
        )
        self._entry_row(form, 2, "每天北京时间", self.schedule_times_var)
        ttk.Label(
            form,
            text="固定时间模式使用，例如 02:00,08:00,14:00,20:00，可填 1-4 个时间",
            style="Hint.TLabel",
        ).grid(row=3, column=1, sticky="w", pady=(0, 6))
        self._entry_row(form, 4, "结束后倒计时小时", self.schedule_interval_hours_var)
        self._entry_row(form, 5, "结束后倒计时分钟", self.schedule_interval_minutes_var)
        ttk.Label(
            form,
            text="倒计时模式使用；上次运行完毕时间为空时，会从启动或结束时间开始倒计时",
            style="Hint.TLabel",
        ).grid(row=6, column=1, sticky="w", pady=(0, 6))
        self._entry_row(form, 7, "上次运行完毕时间", self.schedule_last_finished_at_var)
        ttk.Label(
            form,
            text="倒计时模式使用；例如 2026-05-16 12:00，也可填 12:00 表示今天",
            style="Hint.TLabel",
        ).grid(row=8, column=1, sticky="w", pady=(0, 6))

        row = ttk.Frame(parent, style="Surface.TFrame")
        row.pack(fill="x", pady=(14, 0))
        self._button(row, "启动定时", self.start_schedule, accent=True).pack(side="left", padx=(0, 8))
        self._button(row, "停止定时", self.stop_schedule, danger=True).pack(side="left", padx=8)
        self._button(row, "保存配置", self.save_current_settings).pack(side="left", padx=8)
        ttk.Label(
            parent,
            textvariable=self.schedule_status_var,
            style="Hint.TLabel",
            wraplength=720,
        ).pack(anchor="w", pady=(14, 0))

    DesktopApp.__init__ = init_with_schedule_mode
    DesktopApp._schedule_config = schedule_config_with_interval
    DesktopApp._page_schedule = page_schedule_with_interval


_patch_schedule_interval_mode()
del _patch_schedule_interval_mode


def _patch_gui_log_timestamps():
    original_log = DesktopApp._log

    def log_with_timestamp(self, message):
        text = str(message).rstrip()
        if text.startswith("[") and len(text) >= 10 and text[3:4] == ":" and text[6:7] == ":" and text[9:10] == "]":
            original_log(self, text)
            return
        original_log(self, f"[{_datetime.now().strftime('%H:%M:%S')}] {text}")

    DesktopApp._log = log_with_timestamp


_patch_gui_log_timestamps()
del _patch_gui_log_timestamps


_REMOTE_AUTH_INITIAL_DELAY_MS = 15_000
_REMOTE_AUTH_CHECK_INTERVAL_MS = 60_000


def _patch_runtime_authorization_check():
    original_init = DesktopApp.__init__
    original_run_worker = DesktopApp._run_worker
    original_start_schedule = DesktopApp.start_schedule
    original_on_close = DesktopApp.on_close

    def schedule_check(self, delay_ms):
        if getattr(self, "_remote_authorization_stopped", False):
            return
        root = getattr(self, "root", None)
        if root is None:
            return

        def callback():
            self._remote_authorization_after_id = None
            start_check(self)

        with _suppress(Exception):
            self._remote_authorization_after_id = root.after(delay_ms, callback)

    def stop_for_authorization(self, message):
        if getattr(self, "_remote_authorization_stopped", False):
            return
        self._remote_authorization_stopped = True
        with _suppress(Exception):
            self.stop_event.set()
        with _suppress(Exception):
            self.schedule_stop_event.set()
        with _suppress(Exception):
            runner = getattr(self, "schedule_runner", None)
            if runner is not None:
                runner.request_stop()
        with _suppress(Exception):
            self._log("远程授权已停用，程序将关闭")

        def close_after_notice():
            from tkinter import messagebox as _messagebox

            with _suppress(Exception):
                _messagebox.showerror("授权不可用", message, parent=self.root)
            with _suppress(Exception):
                original_on_close(self)

        with _suppress(Exception):
            self.root.after(0, close_after_notice)

    def start_check(self):
        if getattr(self, "_remote_authorization_stopped", False):
            return
        if getattr(self, "_remote_authorization_checking", False):
            schedule_check(self, _REMOTE_AUTH_CHECK_INTERVAL_MS)
            return
        self._remote_authorization_checking = True
        machine_code = getattr(self, "_remote_authorization_machine_code", None)
        root = getattr(self, "root", None)

        def worker():
            try:
                from .license_gate import check_remote_authorization

                allowed, message = check_remote_authorization(machine_code)
            except Exception as exc:
                allowed, message = False, str(exc)

            def finish():
                self._remote_authorization_checking = False
                if allowed:
                    schedule_check(self, _REMOTE_AUTH_CHECK_INTERVAL_MS)
                else:
                    stop_for_authorization(self, message)

            with _suppress(Exception):
                root.after(0, finish)

        _threading.Thread(target=worker, name="RemoteAuthorizationCheck", daemon=True).start()

    def init_with_runtime_authorization(self, root):
        original_init(self, root)
        self._remote_authorization_after_id = None
        self._remote_authorization_checking = False
        self._remote_authorization_stopped = False
        try:
            from .license_gate import get_machine_code

            self._remote_authorization_machine_code = get_machine_code()
        except Exception:
            self._remote_authorization_machine_code = None
        schedule_check(self, _REMOTE_AUTH_INITIAL_DELAY_MS)

    def run_worker_with_authorization(self, name, target):
        if getattr(self, "_remote_authorization_stopped", False):
            with _suppress(Exception):
                self._log("授权已停用，无法启动任务")
            return None
        return original_run_worker(self, name, target)

    def start_schedule_with_authorization(self):
        if getattr(self, "_remote_authorization_stopped", False):
            with _suppress(Exception):
                self._log("授权已停用，无法启动定时任务")
            return None
        return original_start_schedule(self)

    def on_close_with_runtime_authorization(self):
        after_id = getattr(self, "_remote_authorization_after_id", None)
        if after_id:
            with _suppress(Exception):
                self.root.after_cancel(after_id)
            self._remote_authorization_after_id = None
        return original_on_close(self)

    DesktopApp.__init__ = init_with_runtime_authorization
    DesktopApp._run_worker = run_worker_with_authorization
    DesktopApp.start_schedule = start_schedule_with_authorization
    DesktopApp.on_close = on_close_with_runtime_authorization


_patch_runtime_authorization_check()
del _patch_runtime_authorization_check


def _patch_wireless_adb_ui():
    original_init = DesktopApp.__init__
    original_page_device = DesktopApp._page_device
    original_run_worker = DesktopApp._run_worker
    original_start_schedule = DesktopApp.start_schedule

    def is_wireless_serial(value):
        text = str(value or "").strip()
        if ":" not in text:
            return False
        host, port = text.rsplit(":", 1)
        return bool(host) and port.isdigit()

    def init_with_wireless_adb(self, root):
        from .wireless_adb import load_config

        config = load_config()
        saved_serial = str(config.get("serial") or "").strip()
        saved_host = str(config.get("host") or "").strip()
        self.wireless_devices = []
        self.wireless_device_labels = []
        self.wireless_selected_var = tk.StringVar(value="")
        self.wireless_pair_code_var = tk.StringVar(value="")
        self.wireless_manual_address_var = tk.StringVar(value="")
        self.wireless_status_var = tk.StringVar(
            value=(f"已保存无线设备：{saved_serial}" if saved_serial else "手机打开无线调试后，点击自动发现。")
        )
        self.wireless_busy = False
        original_init(self, root)
        if saved_serial:
            with _suppress(Exception):
                self.serial_var.set(saved_serial)
            self.wireless_manual_address_var.set(saved_serial)
            self.wireless_selected_var.set(saved_host or saved_serial)

    def selected_wireless_device(self):
        label = self.wireless_selected_var.get()
        for index, item_label in enumerate(getattr(self, "wireless_device_labels", [])):
            if item_label == label:
                return self.wireless_devices[index]
        return None

    def manual_wireless_device(self, pairing=False):
        from .wireless_adb import WirelessDevice

        address = self.wireless_manual_address_var.get().strip()
        if not address:
            return None
        if ":" not in address:
            raise RuntimeError("手动地址格式应为 IP:端口，例如 192.168.1.23:37121")
        host, port_text = address.rsplit(":", 1)
        host = host.strip()
        if not host or not port_text.isdigit():
            raise RuntimeError("手动地址格式应为 IP:端口，例如 192.168.1.23:37121")
        port = int(port_text)
        if pairing:
            return WirelessDevice(host=host, name="手动输入", pairing_port=port)
        return WirelessDevice(host=host, name="手动输入", connect_port=port)

    def set_wireless_busy(self, busy, message=None):
        self.wireless_busy = bool(busy)
        for button in getattr(self, "wireless_buttons", []):
            with _suppress(Exception):
                button.configure(state=("disabled" if self.wireless_busy else "normal"))
        if message:
            self.wireless_status_var.set(message)

    def run_wireless_task(self, message, worker, on_success):
        if getattr(self, "wireless_busy", False):
            self.wireless_status_var.set("无线 ADB 操作正在处理中，请稍等。")
            return
        set_wireless_busy(self, True, message)

        def job():
            result = None
            error = None
            try:
                result = worker()
            except Exception as exc:
                error = str(exc)

            def finish():
                set_wireless_busy(self, False)
                if error:
                    self.wireless_status_var.set(error)
                    with _suppress(Exception):
                        self._log(f"无线 ADB: {error}")
                    return
                on_success(result)

            with _suppress(Exception):
                self.root.after(0, finish)

        _threading.Thread(target=job, name="WirelessADBTask", daemon=True).start()

    def refresh_wireless_devices(self):
        from .wireless_adb import discover_wireless_devices

        def worker():
            return discover_wireless_devices()

        def done(devices):
            self.wireless_devices = devices
            self.wireless_device_labels = [device.label for device in devices]
            with _suppress(Exception):
                self.wireless_device_combo.configure(values=self.wireless_device_labels)
            if devices:
                self.wireless_selected_var.set(self.wireless_device_labels[0])
                self.wireless_status_var.set(f"发现 {len(devices)} 台无线调试设备。")
            else:
                self.wireless_selected_var.set("")
                self.wireless_status_var.set("没有发现无线调试设备。请确认手机无线调试页面保持打开，且与电脑在同一 Wi-Fi。")

        run_wireless_task(self, "正在自动发现局域网无线调试设备...", worker, done)

    def connect_selected_wireless_device(self):
        from .wireless_adb import WirelessDevice, connect_device, save_connected_device

        try:
            device = selected_wireless_device(self) or manual_wireless_device(self, pairing=False)
        except RuntimeError as exc:
            self.wireless_status_var.set(str(exc))
            return
        if device is None:
            self.wireless_status_var.set("请先点击自动发现并选择一台设备，或填写手动地址 IP:端口。")
            return
        if not device.connect_port:
            self.wireless_status_var.set("这台设备只有配对端口，请先输入配对码并点击配对并连接。")
            return

        def worker():
            message = connect_device(device.host, int(device.connect_port))
            saved = save_connected_device(device)
            return device, saved, message

        def done(result):
            connected_device, _saved, message = result
            self.serial_var.set(connected_device.serial)
            self.wireless_manual_address_var.set(connected_device.serial)
            self.wireless_status_var.set(f"{message}；已写入设备 serial：{connected_device.serial}")
            with _suppress(Exception):
                self._log(f"无线 ADB: {message}")

        run_wireless_task(self, f"正在连接 {device.host}:{device.connect_port}...", worker, done)

    def pair_selected_wireless_device(self):
        from .wireless_adb import (
            WirelessDevice,
            connect_device,
            discover_wireless_devices,
            pair_device,
            save_connected_device,
        )

        try:
            device = selected_wireless_device(self) or manual_wireless_device(self, pairing=True)
        except RuntimeError as exc:
            self.wireless_status_var.set(str(exc))
            return
        if device is None:
            self.wireless_status_var.set("请先点击自动发现并选择一台设备，或填写手机配对页面显示的 IP:端口。")
            return
        if not device.pairing_port:
            self.wireless_status_var.set("没有发现配对端口；如果已配对，请直接点击连接选中。")
            return
        pairing_code = self.wireless_pair_code_var.get().strip()
        if not pairing_code:
            self.wireless_status_var.set("请输入手机无线调试页面显示的配对码。")
            return

        def worker():
            pair_message = ""
            try:
                pair_message = pair_device(device.host, int(device.pairing_port), pairing_code)
            except Exception as exc:
                # If this computer is already paired, the user often enters the
                # normal wireless debugging address here. In that case skip
                # pairing and try connecting to the same address.
                if device.connect_port or "pairing client" in str(exc).lower():
                    connect_port = int(device.connect_port or device.pairing_port)
                    connect_message = connect_device(device.host, connect_port)
                    connected = WirelessDevice(
                        host=device.host,
                        name=device.name or "手动输入",
                        pairing_port=device.pairing_port,
                        connect_port=connect_port,
                    )
                    saved = save_connected_device(connected)
                    return [], connected, saved, "已跳过配对", connect_message
                raise
            refreshed = discover_wireless_devices()
            target = next((item for item in refreshed if item.host == device.host and item.connect_port), None)
            if target is None and device.connect_port:
                target = device
            if target is None:
                raise RuntimeError("配对成功，但没有发现连接端口；请保持无线调试页面打开后再点自动发现。")
            connect_message = connect_device(target.host, int(target.connect_port))
            saved = save_connected_device(target)
            return refreshed, target, saved, pair_message, connect_message

        def done(result):
            refreshed, connected_device, _saved, pair_message, connect_message = result
            self.wireless_devices = refreshed
            self.wireless_device_labels = [item.label for item in refreshed]
            with _suppress(Exception):
                self.wireless_device_combo.configure(values=self.wireless_device_labels)
            if connected_device.label in self.wireless_device_labels:
                self.wireless_selected_var.set(connected_device.label)
            self.serial_var.set(connected_device.serial)
            self.wireless_manual_address_var.set(connected_device.serial)
            self.wireless_pair_code_var.set("")
            self.wireless_status_var.set(f"{pair_message}；{connect_message}；已写入设备 serial：{connected_device.serial}")
            with _suppress(Exception):
                self._log(f"无线 ADB: {connect_message}")

        run_wireless_task(self, f"正在配对并连接 {device.host}...", worker, done)

    def connect_saved_wireless_device(self):
        from .wireless_adb import auto_connect_saved

        def worker():
            return auto_connect_saved()

        def done(result):
            connected, serial, message = result
        if connected and serial:
            self.serial_var.set(serial)
            self.wireless_manual_address_var.set(serial)
            self.wireless_status_var.set(message if not serial else f"{message}；已写入设备 serial：{serial}")
            with _suppress(Exception):
                self._log(f"无线 ADB: {message}")

        run_wireless_task(self, "正在连接上次保存的无线设备...", worker, done)

    def disconnect_wireless_device(self):
        from .wireless_adb import disconnect_device, load_config

        serial = self.serial_var.get().strip()
        if not is_wireless_serial(serial):
            serial = str(load_config().get("serial") or "").strip()
        if not serial:
            self.wireless_status_var.set("没有可断开的无线设备。")
            return

        def worker():
            return disconnect_device(serial)

        def done(message):
            self.wireless_status_var.set(message)
            with _suppress(Exception):
                self._log(f"无线 ADB: {message}")

        run_wireless_task(self, f"正在断开 {serial}...", worker, done)

    def auto_connect_for_task(self, logger=None):
        from .wireless_adb import connect_device

        serial = self.serial_var.get().strip()
        if not is_wireless_serial(serial):
            return
        host, port = serial.rsplit(":", 1)
        if logger is not None:
            with _suppress(Exception):
                logger.log(f"无线 ADB: 正在确认连接 {serial}")
        message = connect_device(host, int(port))
        if logger is not None:
            with _suppress(Exception):
                logger.log(f"无线 ADB: {message}")

    def run_worker_with_wireless(self, name, target):
        def target_with_wireless(logger):
            auto_connect_for_task(self, logger)
            return target(logger)

        return original_run_worker(self, name, target_with_wireless)

    def start_schedule_with_wireless(self):
        serial = self.serial_var.get().strip()
        if not is_wireless_serial(serial):
            return original_start_schedule(self)

        def worker():
            host, port = serial.rsplit(":", 1)
            from .wireless_adb import connect_device

            return connect_device(host, int(port))

        def done(message):
            with _suppress(Exception):
                self._log(f"无线 ADB: {message}")
            original_start_schedule(self)

        run_wireless_task(self, f"启动定时前正在连接无线设备 {serial}...", worker, done)

    def page_device_with_wireless(self, parent):
        original_page_device(self, parent)

        panel = ttk.LabelFrame(parent, text="无线 ADB", padding=(12, 10, 12, 10))
        panel.pack(fill="x", pady=(16, 0))
        panel.columnconfigure(1, weight=1)

        ttk.Label(panel, text="发现设备").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.wireless_device_combo = ttk.Combobox(
            panel,
            textvariable=self.wireless_selected_var,
            values=getattr(self, "wireless_device_labels", []),
            state="readonly",
        )
        self.wireless_device_combo.grid(row=0, column=1, columnspan=4, sticky="ew", pady=4)

        ttk.Label(panel, text="配对码").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(panel, textvariable=self.wireless_pair_code_var, width=18).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(panel, text="手动地址").grid(row=1, column=2, sticky="w", padx=(18, 8), pady=4)
        ttk.Entry(panel, textvariable=self.wireless_manual_address_var, width=26).grid(
            row=1,
            column=3,
            columnspan=2,
            sticky="w",
            pady=4,
        )

        buttons = ttk.Frame(panel)
        buttons.grid(row=2, column=0, columnspan=5, sticky="w", pady=(8, 0))
        self.wireless_buttons = []
        for text, command, accent in (
            ("自动发现", self.refresh_wireless_devices, True),
            ("配对并连接", self.pair_selected_wireless_device, False),
            ("连接选中", self.connect_selected_wireless_device, False),
            ("连接上次设备", self.connect_saved_wireless_device, False),
            ("断开无线", self.disconnect_wireless_device, False),
        ):
            button = self._button(buttons, text, command, accent=accent)
            button.pack(side="left", padx=(0, 8))
            self.wireless_buttons.append(button)

        ttk.Label(panel, textvariable=self.wireless_status_var, style="Hint.TLabel", wraplength=760).grid(
            row=3,
            column=0,
            columnspan=5,
            sticky="w",
            pady=(10, 0),
        )

    DesktopApp.__init__ = init_with_wireless_adb
    DesktopApp._page_device = page_device_with_wireless
    DesktopApp.refresh_wireless_devices = refresh_wireless_devices
    DesktopApp.connect_selected_wireless_device = connect_selected_wireless_device
    DesktopApp.pair_selected_wireless_device = pair_selected_wireless_device
    DesktopApp.connect_saved_wireless_device = connect_saved_wireless_device
    DesktopApp.disconnect_wireless_device = disconnect_wireless_device
    DesktopApp._run_worker = run_worker_with_wireless
    DesktopApp.start_schedule = start_schedule_with_wireless


_patch_wireless_adb_ui()
del _patch_wireless_adb_ui


def _patch_delta_force_calibrator_ui():
    original_page_device = DesktopApp._page_device

    def open_delta_force_calibrator(self):
        existing = getattr(self, "_delta_force_calibrator_window", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        try:
            from .delta_force_calibrator import CalibratorApp
        except Exception as exc:
            from tkinter import messagebox as _messagebox

            _messagebox.showerror("坐标校准工具", f"无法加载坐标校准工具：{exc}", parent=self.root)
            return

        window = tk.Toplevel(self.root)
        self._delta_force_calibrator_window = window

        def cleanup():
            self._delta_force_calibrator_window = None
            with _suppress(Exception):
                window.destroy()

        window.protocol("WM_DELETE_WINDOW", cleanup)
        CalibratorApp(window, initial_serial=self.serial_var.get().strip())

    def page_device_with_calibrator(self, parent):
        original_page_device(self, parent)

        panel = ttk.LabelFrame(parent, text="坐标校准", padding=(12, 10, 12, 10))
        children = parent.winfo_children()
        pack_options = {"fill": "x", "pady": (16, 0)}
        for child in reversed(children):
            if child is panel:
                continue
            try:
                child.pack_info()
            except Exception:
                continue
            pack_options["before"] = child
            break
        panel.pack(**pack_options)
        panel.columnconfigure(1, weight=1)

        ttk.Label(
            panel,
            text="截图标记 QQ / 三角洲点位，保存后写入 device_profiles 目录。",
            style="Hint.TLabel",
            wraplength=560,
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        self._button(panel, "打开坐标校准工具", self.open_delta_force_calibrator, accent=True).grid(row=0, column=0, sticky="w")

    DesktopApp._page_device = page_device_with_calibrator
    DesktopApp.open_delta_force_calibrator = open_delta_force_calibrator


_patch_delta_force_calibrator_ui()
del _patch_delta_force_calibrator_ui


_CONNECTION_MODE_LABELS = {
    "usb": "USB 调试",
    "wireless": "无线调试",
}


def _connection_mode_to_label(mode):
    return _CONNECTION_MODE_LABELS.get(str(mode or "").strip(), _CONNECTION_MODE_LABELS["usb"])


def _connection_label_to_mode(label):
    for mode, mode_label in _CONNECTION_MODE_LABELS.items():
        if label == mode_label:
            return mode
    return "usb"


def _looks_wireless_serial(value):
    text = str(value or "").strip()
    if ":" not in text:
        return False
    host, port = text.rsplit(":", 1)
    return bool(host.strip()) and port.isdigit()


def _patch_connection_modes_and_modern_ui():
    original_init = DesktopApp.__init__
    original_configure_style = DesktopApp._configure_style
    original_page_device = DesktopApp._page_device
    original_schedule_config = DesktopApp._schedule_config
    original_run_worker = DesktopApp._run_worker
    original_start_schedule = DesktopApp.start_schedule
    original_connect_selected = DesktopApp.connect_selected_wireless_device
    original_pair_selected = DesktopApp.pair_selected_wireless_device

    def load_ui_config():
        try:
            return load_schedule_config("schedule_config.json")
        except Exception:
            return {}

    def saved_wireless_serial():
        try:
            from .wireless_adb import load_config

            return str(load_config().get("serial") or "").strip()
        except Exception:
            return ""

    def selected_mode(self):
        var = getattr(self, "connection_mode_var", None)
        if var is None:
            return "usb"
        return _connection_label_to_mode(var.get())

    def resolve_wireless_serial(self):
        values = []
        for attr in ("wireless_manual_address_var", "serial_var"):
            var = getattr(self, attr, None)
            if var is not None:
                with _suppress(Exception):
                    values.append(var.get())
        values.append(saved_wireless_serial())
        for value in values:
            text = str(value or "").strip()
            if _looks_wireless_serial(text):
                return text
        return ""

    def set_connection_mode(self, mode):
        label = _connection_mode_to_label(mode)
        with _suppress(Exception):
            self.connection_mode_var.set(label)
        apply_connection_mode(self)

    def refresh_connection_mode_buttons(self):
        mode = selected_mode(self)
        for button_mode, button in getattr(self, "connection_mode_buttons", {}).items():
            active = button_mode == mode
            with _suppress(Exception):
                button.configure(
                    bg=(self.colors["accent"] if active else self.colors["surface"]),
                    fg=("#ffffff" if active else self.colors["text"]),
                    activebackground=(self.colors["accent"] if active else self.colors["sidebar_hover"]),
                    activeforeground=("#ffffff" if active else self.colors["text"]),
                    highlightbackground=(self.colors["accent"] if active else self.colors["line"]),
                )

    def update_connection_status(self):
        mode = selected_mode(self)
        if mode == "wireless":
            serial = resolve_wireless_serial(self)
            text = (
                f"无线调试模式：当前使用 {serial}；定时任务每轮开始前会自动 adb connect。"
                if serial
                else "无线调试模式：请先自动发现/连接，或填写手动地址 IP:端口。"
            )
        else:
            serial = str(getattr(self, "serial_var", tk.StringVar(value="")).get() or "").strip()
            if _looks_wireless_serial(serial):
                serial = ""
            text = f"USB 调试模式：当前 serial 为 {serial or '自动选择唯一在线设备'}。"
        with _suppress(Exception):
            self.connection_mode_status_var.set(text)
        refresh_connection_mode_buttons(self)

    def apply_connection_mode(self):
        mode = selected_mode(self)
        if mode == "wireless":
            serial = resolve_wireless_serial(self)
            if serial:
                with _suppress(Exception):
                    self.serial_var.set(serial)
                with _suppress(Exception):
                    self.wireless_manual_address_var.set(serial)
        else:
            with _suppress(Exception):
                if _looks_wireless_serial(self.serial_var.get()):
                    self.serial_var.set("")
        update_connection_status(self)

    def configure_style_modern(self):
        original_configure_style(self)
        self.colors = {
            "bg": "#f7f9fc",
            "sidebar": "#ffffff",
            "sidebar_active": "#2563eb",
            "sidebar_hover": "#eff6ff",
            "surface": "#ffffff",
            "line": "#e5eaf2",
            "text": "#0f172a",
            "muted": "#64748b",
            "accent": "#2563eb",
            "danger": "#ef4444",
            "success": "#10b981",
        }
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        with _suppress(Exception):
            style.theme_use("clam")
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Surface.TFrame", background=self.colors["surface"])
        style.configure("Card.TFrame", background=self.colors["surface"], relief="solid", borderwidth=1)
        style.configure(
            "TLabel",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "Surface.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            font=("Microsoft YaHei UI", 10),
        )
        style.configure("Muted.TLabel", background=self.colors["bg"], foreground=self.colors["muted"])
        style.configure(
            "Title.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            font=("Microsoft YaHei UI", 18, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            font=("Microsoft YaHei UI", 13, "bold"),
        )
        style.configure(
            "Hint.TLabel",
            background=self.colors["surface"],
            foreground=self.colors["muted"],
            font=("Microsoft YaHei UI", 9),
        )
        style.configure("TCheckbutton", background=self.colors["surface"], font=("Microsoft YaHei UI", 10))
        style.configure("TRadiobutton", background=self.colors["surface"], font=("Microsoft YaHei UI", 10))
        style.configure(
            "TEntry",
            fieldbackground="#ffffff",
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            padding=(8, 6),
        )
        style.configure(
            "TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            padding=(8, 6),
        )
        style.configure(
            "TSpinbox",
            fieldbackground="#ffffff",
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            padding=(8, 6),
        )
        style.configure(
            "TLabelframe",
            background=self.colors["surface"],
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            relief="solid",
        )
        style.configure(
            "TLabelframe.Label",
            background=self.colors["surface"],
            foreground=self.colors["text"],
            font=("Microsoft YaHei UI", 11, "bold"),
        )

    def button_modern(self, parent, text, command, accent=False, danger=False):
        bg = self.colors["surface"]
        fg = self.colors["text"]
        border = self.colors["line"]
        if accent:
            bg = self.colors["accent"]
            fg = "#ffffff"
            border = self.colors["accent"]
        if danger:
            bg = self.colors["danger"]
            fg = "#ffffff"
            border = self.colors["danger"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=bg,
            activeforeground=fg,
            bd=0,
            highlightthickness=1,
            highlightbackground=border,
            padx=14,
            pady=8,
            cursor="hand2",
            font=("Microsoft YaHei UI", 10, "bold"),
            relief="flat",
        )

    def form_modern(self, parent):
        frame = ttk.Frame(parent, style="Surface.TFrame", padding=(14, 10, 14, 10))
        frame.pack(fill="x", pady=(0, 12))
        frame.grid_columnconfigure(1, weight=1)
        return frame

    def page_title_modern(self, parent, title, hint):
        ttk.Label(parent, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(parent, text=hint, style="Muted.TLabel", wraplength=820).pack(anchor="w", pady=(4, 16))

    def build_sidebar_modern(self, parent):
        parent.configure(bg=self.colors["sidebar"])
        brand = tk.Frame(parent, bg=self.colors["sidebar"])
        brand.pack(fill="x", padx=18, pady=(18, 18))

        logo = tk.Label(
            brand,
            text="三角洲",
            bg=self.colors["accent"],
            fg="#ffffff",
            width=4,
            height=2,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        logo.pack(side="left", padx=(0, 10))
        tk.Label(
            brand,
            text="三角洲助手",
            bg=self.colors["sidebar"],
            fg=self.colors["text"],
            anchor="w",
            font=("Microsoft YaHei UI", 15, "bold"),
        ).pack(side="left")

        pages = [
            ("device", "概览"),
            ("qq", "QQ 切换"),
            ("delta", "三角洲制作"),
            ("full", "完整流程"),
            ("schedule", "定时任务"),
            ("logs", "日志与截图"),
        ]
        for key, label in pages:
            button = tk.Button(
                parent,
                text=label,
                command=lambda page=key: self._show_page(page),
                anchor="w",
                bg=self.colors["sidebar"],
                fg="#334155",
                activebackground=self.colors["sidebar_hover"],
                activeforeground=self.colors["text"],
                bd=0,
                highlightthickness=0,
                padx=18,
                pady=12,
                cursor="hand2",
                font=("Microsoft YaHei UI", 10, "bold"),
                relief="flat",
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = button

        tk.Label(
            parent,
            text="连接优先级由设备页选择\n定时任务会保存当前配置",
            bg=self.colors["sidebar"],
            fg=self.colors["muted"],
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(side="bottom", anchor="w", padx=20, pady=22)

    def show_page_modern(self, page):
        self.active_page = page
        for key, button in self.nav_buttons.items():
            active = key == page
            button.configure(
                bg=(self.colors["sidebar_active"] if active else self.colors["sidebar"]),
                fg=("#ffffff" if active else "#334155"),
                activebackground=(self.colors["sidebar_active"] if active else self.colors["sidebar_hover"]),
                activeforeground=("#ffffff" if active else self.colors["text"]),
            )
        for child in self.page_frame.winfo_children():
            child.destroy()
        builders = {
            "device": self._page_device,
            "qq": self._page_qq,
            "delta": self._page_delta,
            "full": self._page_full,
            "schedule": self._page_schedule,
            "logs": self._page_logs,
        }
        builder = builders.get(page, self._page_device)
        builder(self.page_frame)

    def init_with_connection_mode(self, root):
        config = load_ui_config()
        configured_mode = str(config.get("connection_mode") or "").strip()
        if configured_mode not in _CONNECTION_MODE_LABELS:
            configured_mode = "wireless" if _looks_wireless_serial(config.get("serial")) else "usb"
        self.connection_mode_var = tk.StringVar(value=_connection_mode_to_label(configured_mode))
        self.connection_mode_status_var = tk.StringVar(value="")
        self.connection_mode_buttons = {}
        original_init(self, root)
        apply_connection_mode(self)

    def build_connection_mode_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="连接模式", padding=(14, 12, 14, 12))
        panel.columnconfigure(1, weight=1)

        mode_row = ttk.Frame(panel, style="Surface.TFrame")
        mode_row.grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.connection_mode_buttons = {}
        for mode, label in _CONNECTION_MODE_LABELS.items():
            button = tk.Button(
                mode_row,
                text=label,
                command=lambda selected=mode: set_connection_mode(self, selected),
                bd=0,
                highlightthickness=1,
                padx=16,
                pady=8,
                cursor="hand2",
                font=("Microsoft YaHei UI", 10, "bold"),
                relief="flat",
            )
            button.pack(side="left", padx=(0, 8))
            self.connection_mode_buttons[mode] = button

        ttk.Label(
            panel,
            textvariable=self.connection_mode_status_var,
            style="Hint.TLabel",
            wraplength=620,
        ).grid(row=0, column=1, sticky="ew")
        refresh_connection_mode_buttons(self)
        return panel

    def page_device_with_connection_mode(self, parent):
        original_page_device(self, parent)
        panel = build_connection_mode_panel(self, parent)
        children = parent.winfo_children()
        pack_options = {"fill": "x", "pady": (0, 14)}
        if len(children) >= 3:
            pack_options["before"] = children[2]
        panel.pack(**pack_options)
        update_connection_status(self)

    def schedule_config_with_connection_mode(self):
        config = original_schedule_config(self)
        mode = selected_mode(self)
        config["connection_mode"] = mode
        wireless_serial = resolve_wireless_serial(self)
        if mode == "wireless":
            if _looks_wireless_serial(wireless_serial):
                config["serial"] = wireless_serial
                config["wireless_serial"] = wireless_serial
                with _suppress(Exception):
                    self.serial_var.set(wireless_serial)
            else:
                config["serial"] = ""
                config["wireless_serial"] = ""
            return config
            if not _looks_wireless_serial(wireless_serial):
                raise ValueError("无线调试模式需要先填写或连接无线地址 IP:端口")
            config["serial"] = wireless_serial
            config["wireless_serial"] = wireless_serial
            with _suppress(Exception):
                self.serial_var.set(wireless_serial)
        else:
            if _looks_wireless_serial(config.get("serial")):
                config["serial"] = ""
            if wireless_serial:
                config["wireless_serial"] = wireless_serial
        return config

    def auto_connect_and_continue(self, action, status_var=None):
        def worker():
            from .wireless_adb import auto_connect_saved

            return auto_connect_saved()

        def done(result):
            connected, serial, message = result
            if connected and serial:
                self.serial_var.set(serial)
                with _suppress(Exception):
                    self.wireless_manual_address_var.set(serial)
                with _suppress(Exception):
                    self.wireless_status_var.set(message)
                if status_var is not None:
                    with _suppress(Exception):
                        status_var.set(message)
                with _suppress(Exception):
                    self._log(f"Wireless ADB: {message}")
                update_connection_status(self)
                action()
                return
            fallback = message or "No saved or unique wireless device is available."
            with _suppress(Exception):
                self.wireless_status_var.set(fallback)
            if status_var is not None:
                with _suppress(Exception):
                    status_var.set(fallback)
            with _suppress(Exception):
                self._log(f"Wireless ADB: {fallback}")
            update_connection_status(self)

        run_connection_task(self, "Auto detecting wireless ADB device...", worker, done)

    def run_worker_with_connection_mode(self, name, target):
        if selected_mode(self) == "wireless":
            serial = resolve_wireless_serial(self)
            if not serial:
                auto_connect_and_continue(self, lambda: original_run_worker(self, name, target))
                return None
                self._log("无线调试模式需要先填写或连接无线地址 IP:端口")
                return None
            self.serial_var.set(serial)
        elif _looks_wireless_serial(self.serial_var.get()):
            self.serial_var.set("")
        update_connection_status(self)
        return original_run_worker(self, name, target)

    def start_schedule_with_connection_mode(self):
        if selected_mode(self) == "wireless":
            serial = resolve_wireless_serial(self)
            if not serial:
                auto_connect_and_continue(self, lambda: original_start_schedule(self), self.schedule_status_var)
                return None
                message = "无线调试模式需要先填写或连接无线地址 IP:端口"
                self.schedule_status_var.set(message)
                self._log(message)
                return None
            self.serial_var.set(serial)
        elif _looks_wireless_serial(self.serial_var.get()):
            self.serial_var.set("")
        update_connection_status(self)
        return original_start_schedule(self)

    def run_connection_task(self, message, worker, on_success):
        if getattr(self, "wireless_busy", False):
            with _suppress(Exception):
                self.wireless_status_var.set("无线 ADB 操作正在处理中，请稍等。")
            return
        self.wireless_busy = True
        with _suppress(Exception):
            self.wireless_status_var.set(message)

        def job():
            result = None
            error = None
            try:
                result = worker()
            except Exception as exc:
                error = str(exc)

            def finish():
                self.wireless_busy = False
                if error:
                    with _suppress(Exception):
                        self.wireless_status_var.set(error)
                    with _suppress(Exception):
                        self._log(f"无线 ADB: {error}")
                    update_connection_status(self)
                    return
                on_success(result)
                update_connection_status(self)

            with _suppress(Exception):
                self.root.after(0, finish)

        _threading.Thread(target=job, name="ConnectionModeTask", daemon=True).start()

    def connect_selected_with_mode(self):
        set_connection_mode(self, "wireless")
        result = original_connect_selected(self)
        for delay in (600, 1600, 3200):
            with _suppress(Exception):
                self.root.after(delay, lambda: update_connection_status(self))
        return result

    def pair_selected_with_mode(self):
        set_connection_mode(self, "wireless")
        result = original_pair_selected(self)
        for delay in (800, 2200, 4200):
            with _suppress(Exception):
                self.root.after(delay, lambda: update_connection_status(self))
        return result

    def connect_saved_wireless_device_fixed(self):
        from .wireless_adb import auto_connect_saved

        set_connection_mode(self, "wireless")

        def worker():
            return auto_connect_saved()

        def done(result):
            connected, serial, message = result
            if connected and serial:
                self.serial_var.set(serial)
                self.wireless_manual_address_var.set(serial)
            self.wireless_status_var.set(message if not serial else f"{message}；已写入设备 serial：{serial}")
            with _suppress(Exception):
                self._log(f"无线 ADB: {message}")

        run_connection_task(self, "正在连接上次保存的无线设备...", worker, done)

    DesktopApp.__init__ = init_with_connection_mode
    DesktopApp._configure_style = configure_style_modern
    DesktopApp._build_sidebar = build_sidebar_modern
    DesktopApp._button = button_modern
    DesktopApp._form = form_modern
    DesktopApp._page_title = page_title_modern
    DesktopApp._show_page = show_page_modern
    DesktopApp._page_device = page_device_with_connection_mode
    DesktopApp._schedule_config = schedule_config_with_connection_mode
    DesktopApp._run_worker = run_worker_with_connection_mode
    DesktopApp.start_schedule = start_schedule_with_connection_mode
    DesktopApp.connect_selected_wireless_device = connect_selected_with_mode
    DesktopApp.pair_selected_wireless_device = pair_selected_with_mode
    DesktopApp.connect_saved_wireless_device = connect_saved_wireless_device_fixed
    DesktopApp.apply_connection_mode = apply_connection_mode


_patch_connection_modes_and_modern_ui()
del _patch_connection_modes_and_modern_ui


def _patch_terminal_page_and_rounded_ui():
    original_init = DesktopApp.__init__
    original_configure_style = DesktopApp._configure_style

    def widget_background(widget, fallback):
        try:
            value = widget.cget("background")
            return value or fallback
        except Exception:
            return fallback

    def draw_round_rect(canvas, x1, y1, x2, y2, radius, fill, outline="", width=1, tags=None):
        target_width = max(1, int(round(x2 - x1 + 1)))
        target_height = max(1, int(round(y2 - y1 + 1)))
        scale = 4
        scaled_width = target_width * scale
        scaled_height = target_height * scale
        scaled_radius = max(0, min(radius * scale, scaled_width // 2, scaled_height // 2))
        stroke_width = max(1, int(width) * scale)
        image = Image.new("RGBA", (scaled_width, scaled_height), (0, 0, 0, 0))
        draw = _ImageDraw.Draw(image)
        inset = max(1, stroke_width // 2)
        draw.rounded_rectangle(
            (inset, inset, scaled_width - inset - 1, scaled_height - inset - 1),
            radius=scaled_radius,
            fill=fill,
            outline=(outline or None),
            width=stroke_width if outline else 1,
        )
        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        if not hasattr(canvas, "_rounded_rect_images"):
            canvas._rounded_rect_images = []
        canvas._rounded_rect_images.append(photo)
        if len(canvas._rounded_rect_images) > 24:
            canvas._rounded_rect_images = canvas._rounded_rect_images[-24:]
        canvas.create_image(x1, y1, image=photo, anchor="nw", tags=tags)

    class RoundedButton(tk.Canvas):
        def __init__(
            self,
            parent,
            text,
            command=None,
            bg="#ffffff",
            fg="#0f172a",
            activebackground=None,
            activeforeground=None,
            border="#dbe3ef",
            parent_bg=None,
            radius=16,
            padx=18,
            height=38,
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="center",
            **kwargs,
        ):
            self._text = text
            self._command = command
            self._fill = bg
            self._fg = fg
            self._active_fill = activebackground or bg
            self._active_fg = activeforeground or fg
            self._border = border
            self._radius = radius
            self._padx = padx
            self._height = height
            self._font = font
            self._anchor = anchor
            self._state = kwargs.pop("state", "normal")
            self._hover = False
            requested_width = max(78, len(str(text)) * 15 + padx * 2)
            super().__init__(
                parent,
                width=requested_width,
                height=height,
                bg=parent_bg or widget_background(parent, "#ffffff"),
                highlightthickness=0,
                bd=0,
                cursor=("arrow" if self._state == "disabled" else "hand2"),
                **kwargs,
            )
            self.bind("<Configure>", lambda event: self._redraw())
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<ButtonRelease-1>", self._on_release)
            self._redraw()

        def configure(self, cnf=None, **kwargs):
            if cnf:
                kwargs.update(cnf)
            redraw = False
            for key in list(kwargs):
                value = kwargs.pop(key)
                if key in ("bg", "background"):
                    self._fill = value
                    redraw = True
                elif key == "fg":
                    self._fg = value
                    redraw = True
                elif key == "activebackground":
                    self._active_fill = value
                    redraw = True
                elif key == "activeforeground":
                    self._active_fg = value
                    redraw = True
                elif key in ("highlightbackground", "border", "bordercolor"):
                    self._border = value
                    redraw = True
                elif key == "text":
                    self._text = value
                    redraw = True
                elif key == "command":
                    self._command = value
                elif key == "state":
                    self._state = value
                    super().configure(cursor=("arrow" if value == "disabled" else "hand2"))
                    redraw = True
                else:
                    super().configure(**{key: value})
            if redraw:
                self._redraw()

        config = configure

        def _on_enter(self, event=None):
            if self._state == "disabled":
                return
            self._hover = True
            self._redraw()

        def _on_leave(self, event=None):
            self._hover = False
            self._redraw()

        def _on_release(self, event=None):
            if self._state == "disabled" or self._command is None:
                return
            self._command()

        def _redraw(self):
            width = self.winfo_width()
            height = self.winfo_height()
            if width <= 2:
                width = int(float(self.cget("width")))
            if height <= 2:
                height = int(float(self.cget("height")))
            width = max(4, width)
            height = max(4, height)
            fill = self._active_fill if self._hover else self._fill
            fg = self._active_fg if self._hover else self._fg
            border = self._border
            if self._state == "disabled":
                fill = "#edf2f7"
                fg = "#94a3b8"
                border = "#e2e8f0"
            self.delete("all")
            draw_round_rect(self, 1, 1, width - 2, height - 2, self._radius, fill, border, 1)
            anchor = "w" if self._anchor == "w" else "center"
            x = self._padx if anchor == "w" else width / 2
            self.create_text(x, height / 2, text=self._text, fill=fg, font=self._font, anchor=anchor)

    def rounded_frame(parent, app, fill=None, outline=None, radius=18, padding=(16, 12, 16, 12), parent_bg=None):
        fill = fill or app.colors["surface"]
        outline = outline or app.colors["line"]
        parent_bg = parent_bg or widget_background(parent, app.colors["bg"])
        canvas = tk.Canvas(parent, bg=parent_bg, highlightthickness=0, bd=0)
        inner = tk.Frame(canvas, bg=fill, highlightthickness=0, bd=0)
        left, top, right, bottom = padding
        window_id = canvas.create_window(left, top, anchor="nw", window=inner)

        def redraw(event=None):
            width = max(1, canvas.winfo_width() or inner.winfo_reqwidth() + left + right)
            requested_height = inner.winfo_reqheight() + top + bottom
            height = max(canvas.winfo_height(), requested_height, 48)
            canvas.delete("rounded-bg")
            draw_round_rect(canvas, 1, 1, width - 2, height - 2, radius, fill, outline, 1, "rounded-bg")
            canvas.tag_lower("rounded-bg")
            canvas.coords(window_id, left, top)
            canvas.itemconfigure(window_id, width=max(1, width - left - right))
            canvas.itemconfigure(window_id, height=max(1, height - top - bottom))
            if abs(int(canvas.cget("height")) - requested_height) > 1:
                canvas.configure(height=requested_height)

        canvas.bind("<Configure>", redraw)
        inner.bind("<Configure>", lambda event: canvas.after_idle(redraw))
        inner._rounded_canvas = canvas
        return canvas, inner

    def configure_style_rounder(self):
        original_configure_style(self)
        self.colors.update(
            {
                "bg": "#f4f7fb",
                "sidebar": "#ffffff",
                "sidebar_active": "#2563eb",
                "sidebar_hover": "#eaf2ff",
                "surface": "#ffffff",
                "line": "#dbe3ef",
                "text": "#111827",
                "muted": "#64748b",
                "accent": "#2563eb",
                "danger": "#ef4444",
                "success": "#0ea66b",
            }
        )
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Surface.TFrame", background=self.colors["surface"])
        style.configure("Card.TFrame", background=self.colors["surface"], relief="flat", borderwidth=0)
        style.configure("Surface.TLabel", background=self.colors["surface"], foreground=self.colors["text"])
        style.configure("Hint.TLabel", background=self.colors["surface"], foreground=self.colors["muted"])
        style.configure("Muted.TLabel", background=self.colors["bg"], foreground=self.colors["muted"])
        style.configure("TEntry", padding=(10, 8))
        style.configure("TCombobox", padding=(10, 8))
        style.configure("TSpinbox", padding=(10, 8))

    def init_with_terminal_page(self, root):
        self._terminal_log_buffer = []
        self.log_text = None
        original_init(self, root)

    def build_layout_without_bottom_terminal(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(self.root, bg=self.colors["sidebar"], width=224)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        self._build_sidebar(sidebar)

        main = ttk.Frame(self.root, padding=(18, 16, 18, 18))
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        self._build_header(main)
        self._build_content(main)

    def build_content_scrollable(self, parent):
        content = ttk.Frame(parent)
        content.grid(row=1, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        page_shell = ttk.Frame(content, style="Surface.TFrame", padding=0)
        page_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        page_shell.grid_columnconfigure(0, weight=1)
        page_shell.grid_rowconfigure(0, weight=1)

        page_canvas = tk.Canvas(
            page_shell,
            bg=self.colors["surface"],
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        page_canvas.grid(row=0, column=0, sticky="nsew")
        page_scrollbar = ttk.Scrollbar(page_shell, orient="vertical", command=page_canvas.yview)
        page_scrollbar.grid(row=0, column=1, sticky="ns")
        page_canvas.configure(yscrollcommand=page_scrollbar.set)

        self.page_frame = ttk.Frame(page_canvas, style="Surface.TFrame", padding=16)
        page_window = page_canvas.create_window(0, 0, anchor="nw", window=self.page_frame)
        self._content_frame = content
        self._page_shell = page_shell
        self._page_canvas = page_canvas
        self._page_scrollbar = page_scrollbar
        self._page_window = page_window

        def update_scroll_region(event=None):
            try:
                page_canvas.configure(scrollregion=page_canvas.bbox("all"))
            except Exception:
                pass

        def fit_page_width(event):
            try:
                page_canvas.itemconfigure(page_window, width=max(1, event.width))
                if getattr(self, "active_page", None) == "logs":
                    page_canvas.itemconfigure(page_window, height=max(1, event.height))
            except Exception:
                pass
            update_scroll_region()

        def is_descendant(widget, ancestor):
            current = widget
            while current is not None and ancestor is not None:
                if current == ancestor:
                    return True
                parent_name = current.winfo_parent()
                if not parent_name:
                    return False
                try:
                    current = current.nametowidget(parent_name)
                except Exception:
                    return False
            return False

        def on_mouse_wheel(event):
            try:
                x_root = getattr(event, "x_root", 0) or self.root.winfo_pointerx()
                y_root = getattr(event, "y_root", 0) or self.root.winfo_pointery()
                hovered = self.root.winfo_containing(x_root, y_root)
                if hovered is None or not is_descendant(hovered, page_canvas):
                    return None
                log_widget = getattr(self, "log_text", None)
                if log_widget is not None and is_descendant(hovered, log_widget):
                    return None
                delta = getattr(event, "delta", 0)
                units = int(-delta / 120) if delta else 0
                if units == 0:
                    units = -1 if delta > 0 else 1
                page_canvas.yview_scroll(units, "units")
                return "break"
            except Exception:
                return None

        self.page_frame.bind("<Configure>", update_scroll_region)
        page_canvas.bind("<Configure>", fit_page_width)
        if not getattr(self.root, "_adb_automation_page_wheel_bound", False):
            self.root.bind_all("<MouseWheel>", on_mouse_wheel, add="+")
            self.root._adb_automation_page_wheel_bound = True

        side_canvas, side = rounded_frame(content, self, radius=20, padding=(14, 12, 14, 12), parent_bg=self.colors["bg"])
        side_canvas.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._status_side_canvas = side_canvas
        side.grid_columnconfigure(0, weight=1)

        ttk.Label(side, text="状态", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self._status_line(side, "设备", self.device_var, 1)
        self._status_line(side, "预设", self.profile_var, 2)
        self._status_line(side, "轮数", self.rounds_var, 3)
        self._status_line(side, "QQ账号", self.qq_account_count_var, 4)
        connection_mode_var = getattr(self, "connection_mode_var", tk.StringVar(value="USB 调试"))
        self._status_line(side, "连接模式", connection_mode_var, 5)
        self._status_line(side, "日志", self.log_path_var, 6)
        ttk.Label(side, text="截图预览", style="Section.TLabel").grid(row=7, column=0, sticky="w", pady=(14, 6))
        self.preview_label = tk.Label(
            side,
            text="尚未截图",
            bg="#eef3f9",
            fg=self.colors["muted"],
            height=11,
            font=("Microsoft YaHei UI", 10),
        )
        self.preview_label.grid(row=8, column=0, sticky="nsew")
        side.grid_rowconfigure(8, weight=1)

    def button_rounder(self, parent, text, command, accent=False, danger=False):
        bg = self.colors["surface"]
        fg = self.colors["text"]
        border = self.colors["line"]
        active_bg = self.colors["sidebar_hover"]
        active_fg = self.colors["text"]
        if accent:
            bg = self.colors["accent"]
            fg = "#ffffff"
            border = self.colors["accent"]
            active_bg = "#1d4ed8"
            active_fg = "#ffffff"
        if danger:
            bg = self.colors["danger"]
            fg = "#ffffff"
            border = self.colors["danger"]
            active_bg = "#dc2626"
            active_fg = "#ffffff"
        return RoundedButton(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=active_fg,
            border=border,
            parent_bg=widget_background(parent, self.colors["bg"]),
            radius=16,
            height=40,
        )

    def form_rounder(self, parent):
        outer, frame = rounded_frame(parent, self, radius=20, padding=(16, 12, 16, 12))
        outer.pack(fill="x", pady=(0, 14))
        frame.grid_columnconfigure(1, weight=1)
        return frame

    def page_title_rounder(self, parent, title, hint):
        ttk.Label(parent, text=title, style="Title.TLabel").pack(anchor="w")
        if hint:
            ttk.Label(parent, text=hint, style="Muted.TLabel", wraplength=820).pack(anchor="w", pady=(4, 16))

    def build_sidebar_rounder(self, parent):
        parent.configure(bg=self.colors["sidebar"])
        brand = tk.Frame(parent, bg=self.colors["sidebar"])
        brand.pack(fill="x", padx=18, pady=(18, 20))

        logo_photo = _load_asset_photo("app_header.png", (46, 46))
        if logo_photo is not None:
            logo = tk.Label(brand, image=logo_photo, bg=self.colors["sidebar"], bd=0)
            logo.image = logo_photo
            logo.pack(side="left", padx=(0, 10))
            self._delta_assistant_sidebar_logo = logo_photo
        else:
            logo = tk.Canvas(brand, width=46, height=46, bg=self.colors["sidebar"], highlightthickness=0, bd=0)
            draw_round_rect(logo, 1, 1, 45, 45, 15, self.colors["accent"], self.colors["accent"], 1)
            logo.create_text(23, 23, text="Δ", fill="#ffffff", font=("Microsoft YaHei UI", 15, "bold"))
            logo.pack(side="left", padx=(0, 10))
        tk.Label(
            brand,
            text="三角洲助手",
            bg=self.colors["sidebar"],
            fg=self.colors["text"],
            anchor="w",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(side="left")

        pages = [
            ("device", "概览"),
            ("qq", "QQ 切换"),
            ("delta", "三角洲制作"),
            ("full", "完整流程"),
            ("schedule", "定时任务"),
            ("logs", "终端"),
        ]
        self.nav_buttons = {}
        for key, label in pages:
            button = RoundedButton(
                parent,
                text=label,
                command=lambda page=key: self._show_page(page),
                bg=self.colors["sidebar"],
                fg="#334155",
                activebackground=self.colors["sidebar_hover"],
                activeforeground=self.colors["text"],
                border=self.colors["sidebar"],
                parent_bg=self.colors["sidebar"],
                radius=16,
                height=42,
                padx=18,
                anchor="w",
            )
            button.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[key] = button

        tk.Label(
            parent,
            text="连接模式在概览页选择\n终端日志已移到独立页面",
            bg=self.colors["sidebar"],
            fg=self.colors["muted"],
            justify="left",
            font=("Microsoft YaHei UI", 9),
        ).pack(side="bottom", anchor="w", padx=20, pady=22)

    def show_page_rounder(self, page):
        self.active_page = page
        for key, button in self.nav_buttons.items():
            active = key == page
            button.configure(
                bg=(self.colors["sidebar_active"] if active else self.colors["sidebar"]),
                fg=("#ffffff" if active else "#334155"),
                activebackground=("#1d4ed8" if active else self.colors["sidebar_hover"]),
                activeforeground=("#ffffff" if active else self.colors["text"]),
                highlightbackground=(self.colors["sidebar_active"] if active else self.colors["sidebar"]),
            )
        for child in self.page_frame.winfo_children():
            child.destroy()
        if page != "logs":
            self.log_text = None
        content = getattr(self, "_content_frame", None)
        page_shell = getattr(self, "_page_shell", None)
        side_canvas = getattr(self, "_status_side_canvas", None)
        page_scrollbar = getattr(self, "_page_scrollbar", None)
        page_canvas = getattr(self, "_page_canvas", None)
        if content is not None and page_shell is not None:
            if page == "logs":
                with _suppress(Exception):
                    side_canvas.grid_remove()
                with _suppress(Exception):
                    page_scrollbar.grid_remove()
                content.grid_columnconfigure(0, weight=1)
                content.grid_columnconfigure(1, weight=0)
                page_shell.grid_configure(column=0, columnspan=2, sticky="nsew", padx=0)
                if page_canvas is not None:
                    with _suppress(Exception):
                        page_canvas.configure(yscrollcommand=None)
            else:
                content.grid_columnconfigure(0, weight=2)
                content.grid_columnconfigure(1, weight=1)
                page_shell.grid_configure(column=0, columnspan=1, sticky="nsew", padx=(0, 10))
                with _suppress(Exception):
                    side_canvas.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
                with _suppress(Exception):
                    page_scrollbar.grid(row=0, column=1, sticky="ns")
                if page_canvas is not None and page_scrollbar is not None:
                    with _suppress(Exception):
                        page_canvas.configure(yscrollcommand=page_scrollbar.set)
        builders = {
            "device": self._page_device,
            "qq": self._page_qq,
            "delta": self._page_delta,
            "full": self._page_full,
            "schedule": self._page_schedule,
            "logs": self._page_logs,
        }
        builders.get(page, self._page_device)(self.page_frame)
        canvas = getattr(self, "_page_canvas", None)
        if canvas is not None:
            with _suppress(Exception):
                canvas.update_idletasks()
                page_window = getattr(self, "_page_window", None)
                if page_window is not None:
                    canvas.itemconfigure(page_window, width=max(1, canvas.winfo_width()))
                    if page == "logs":
                        canvas.itemconfigure(page_window, height=max(1, canvas.winfo_height()))
                    else:
                        canvas.itemconfigure(page_window, height=0)
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.yview_moveto(0)

    def log_buffered(self, message):
        text = str(message).rstrip()
        if not (
            text.startswith("[")
            and len(text) >= 10
            and text[3:4] == ":"
            and text[6:7] == ":"
            and text[9:10] == "]"
        ):
            text = f"[{_datetime.now().strftime('%H:%M:%S')}] {text}"
        buffer = getattr(self, "_terminal_log_buffer", None)
        if buffer is not None:
            buffer.append(text)
            if len(buffer) > 1500:
                del buffer[: len(buffer) - 1500]
        widget = getattr(self, "log_text", None)
        if widget is None:
            return
        try:
            if not widget.winfo_exists():
                return
            widget.configure(state="normal")
            widget.insert("end", text + "\n")
            widget.see("end")
            widget.configure(state="disabled")
        except Exception:
            pass

    def clear_log_rounder(self):
        buffer = getattr(self, "_terminal_log_buffer", None)
        if buffer is not None:
            buffer.clear()
        widget = getattr(self, "log_text", None)
        if widget is None:
            return
        with _suppress(Exception):
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.configure(state="disabled")

    def page_terminal(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=1)
        ttk.Label(parent, text="终端", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            parent,
            text="运行输出集中显示在这里，不再占用其它页面空间。",
            style="Muted.TLabel",
            wraplength=920,
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))
        toolbar = ttk.Frame(parent, style="Surface.TFrame")
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        toolbar_buttons = []
        for text, command, accent, danger in (
            ("完整流程", self.run_full_flow, True, False),
            ("三角洲", self.run_delta_force, False, False),
            ("QQ切号", self.run_qq_switch, False, False),
            ("手机截图", self.take_screenshot, False, False),
            ("打开目录", self.open_project_dir, False, False),
            ("清空日志", self.clear_log_view, False, False),
        ):
            toolbar_buttons.append(self._button(toolbar, text, command, accent=accent, danger=danger))

        def reflow_toolbar_buttons(event=None):
            available_width = max(260, toolbar.winfo_width())
            row = 0
            column = 0
            used_width = 0
            for button in toolbar_buttons:
                with _suppress(Exception):
                    button.grid_forget()
            for button in toolbar_buttons:
                requested_width = max(88, button.winfo_reqwidth()) + 10
                if column > 0 and used_width + requested_width > available_width:
                    row += 1
                    column = 0
                    used_width = 0
                with _suppress(Exception):
                    button.grid(row=row, column=column, sticky="w", padx=(0, 10), pady=(0, 8))
                used_width += requested_width
                column += 1

        with _suppress(Exception):
            toolbar.bind("<Configure>", lambda _event: toolbar.after_idle(reflow_toolbar_buttons), add="+")
            toolbar.after_idle(reflow_toolbar_buttons)

        outer, terminal = rounded_frame(
            parent,
            self,
            fill="#0b1220",
            outline="#1e293b",
            radius=22,
            padding=(12, 12, 12, 12),
            parent_bg=self.colors["surface"],
        )
        outer.grid(row=3, column=0, sticky="nsew", pady=(2, 0))
        terminal.grid_columnconfigure(0, weight=1)
        terminal.grid_rowconfigure(0, weight=1)
        self.log_text = tk.Text(
            terminal,
            height=20,
            bg="#0b1220",
            fg="#dbeafe",
            insertbackground="#dbeafe",
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=14,
            pady=12,
            font=("Microsoft YaHei", 10),
            wrap="word",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(terminal, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.configure(state="normal")
        for line in getattr(self, "_terminal_log_buffer", []):
            self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    DesktopApp.__init__ = init_with_terminal_page
    DesktopApp._configure_style = configure_style_rounder
    DesktopApp._build_layout = build_layout_without_bottom_terminal
    DesktopApp._build_content = build_content_scrollable
    DesktopApp._build_sidebar = build_sidebar_rounder
    DesktopApp._button = button_rounder
    DesktopApp._form = form_rounder
    DesktopApp._page_title = page_title_rounder
    DesktopApp._show_page = show_page_rounder
    DesktopApp._log = log_buffered
    DesktopApp.clear_log_view = clear_log_rounder
    DesktopApp._page_logs = page_terminal


_patch_terminal_page_and_rounded_ui()
del _patch_terminal_page_and_rounded_ui


def _patch_responsive_device_page_ui():
    original_page_device = DesktopApp._page_device

    def children_recursive(widget):
        for child in widget.winfo_children():
            yield child
            yield from children_recursive(child)

    def labelframe_text(widget):
        try:
            return str(widget.cget("text"))
        except Exception:
            return ""

    def find_panel(parent, title):
        for child in parent.winfo_children():
            if labelframe_text(child) == title:
                return child
        return None

    def wrap_label_to_parent(label, parent, margin=44, minimum=220):
        def update(event=None):
            with _suppress(Exception):
                width = max(minimum, parent.winfo_width() - margin)
                label.configure(wraplength=width, justify="left")

        update()
        with _suppress(Exception):
            parent.bind("<Configure>", update, add="+")

    def layout_wrapped_buttons(frame, buttons):
        for button in buttons:
            with _suppress(Exception):
                button.pack_forget()

        def relayout(event=None):
            available = max(220, frame.winfo_width())
            row = 0
            column = 0
            used = 0
            for button in buttons:
                requested = 120
                with _suppress(Exception):
                    requested = max(int(float(button.cget("width"))), button.winfo_reqwidth())
                padded = requested + 10
                if column > 0 and used + padded > available:
                    row += 1
                    column = 0
                    used = 0
                with _suppress(Exception):
                    button.grid(row=row, column=column, sticky="w", padx=(0, 10), pady=(0, 8))
                used += padded
                column += 1

        frame.after_idle(relayout)
        with _suppress(Exception):
            frame.bind("<Configure>", relayout, add="+")

    def adapt_connection_panel(self, parent):
        panel = find_panel(parent, "连接模式")
        if panel is None:
            return
        with _suppress(Exception):
            panel.columnconfigure(0, weight=1)
            panel.columnconfigure(1, weight=0)
        status_var = getattr(self, "connection_mode_status_var", None)
        for child in panel.winfo_children():
            with _suppress(Exception):
                if status_var is not None and str(child.cget("textvariable")) == str(status_var):
                    child.grid_configure(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
                    wrap_label_to_parent(child, panel, margin=54)

    def adapt_calibration_panel(parent):
        panel = find_panel(parent, "坐标校准")
        if panel is None:
            return
        with _suppress(Exception):
            panel.columnconfigure(0, weight=0)
            panel.columnconfigure(1, weight=1)
        for child in panel.winfo_children():
            with _suppress(Exception):
                text = str(child.cget("text"))
            if "截图标记" in text:
                with _suppress(Exception):
                    child.grid_configure(row=0, column=1, sticky="ew", padx=(12, 0))
                wrap_label_to_parent(child, panel, margin=300, minimum=260)

    def adapt_wireless_panel(self, parent):
        panel = find_panel(parent, "无线 ADB")
        if panel is None:
            return
        for column in range(4):
            with _suppress(Exception):
                panel.columnconfigure(column, weight=(1 if column in (1, 3) else 0))

        status_var = getattr(self, "wireless_status_var", None)
        for child in panel.winfo_children():
            info = {}
            with _suppress(Exception):
                info = child.grid_info()
            if not info:
                continue
            row = int(info.get("row", -1))
            if row == 2:
                with _suppress(Exception):
                    child.grid_configure(columnspan=4, sticky="ew")
                buttons = [button for button in child.winfo_children()]
                layout_wrapped_buttons(child, buttons)
            with _suppress(Exception):
                if status_var is not None and str(child.cget("textvariable")) == str(status_var):
                    child.grid_configure(column=0, columnspan=4, sticky="ew")
                    wrap_label_to_parent(child, panel, margin=54)

        with _suppress(Exception):
            self.wireless_device_combo.grid_configure(columnspan=3, sticky="ew")
        with _suppress(Exception):
            for child in panel.grid_slaves(row=1, column=1):
                child.grid_configure(sticky="ew")
        with _suppress(Exception):
            for child in panel.grid_slaves(row=1, column=3):
                child.grid_configure(sticky="ew")

    def page_device_responsive(self, parent):
        original_page_device(self, parent)
        adapt_connection_panel(self, parent)
        adapt_calibration_panel(parent)
        adapt_wireless_panel(self, parent)

    DesktopApp._page_device = page_device_responsive


_patch_responsive_device_page_ui()
del _patch_responsive_device_page_ui


def _patch_adaptive_text_wrapping_ui():
    page_methods = (
        "_page_device",
        "_page_qq",
        "_page_delta",
        "_page_full",
        "_page_schedule",
        "_page_logs",
    )
    originals = {name: getattr(DesktopApp, name) for name in page_methods if hasattr(DesktopApp, name)}

    def labelframe_text(widget):
        try:
            return str(widget.cget("text"))
        except Exception:
            return ""

    def find_panel(parent, title):
        for child in parent.winfo_children():
            if labelframe_text(child) == title:
                return child
        return None

    def widget_text(widget):
        try:
            return str(widget.cget("text"))
        except Exception:
            return ""

    def widget_textvariable(widget):
        try:
            return str(widget.cget("textvariable"))
        except Exception:
            return ""

    def variable_name(variable):
        try:
            return str(variable)
        except Exception:
            return ""

    def safe_grid(widget, **kwargs):
        with _suppress(Exception):
            widget.grid_configure(**kwargs)

    def wrap_label_to_available_width(label, minimum=180, margin=28):
        parent = getattr(label, "master", None)
        if parent is None:
            return

        def update(event=None):
            with _suppress(Exception):
                parent_width = max(parent.winfo_width(), parent.winfo_reqwidth())
                label_x = max(0, label.winfo_x())
                available = parent_width - label_x - margin
                if available < minimum:
                    available = parent_width - margin
                label.configure(wraplength=max(minimum, int(available)), justify="left")

        update()
        with _suppress(Exception):
            parent.bind("<Configure>", update, add="+")
            label.after_idle(update)

    def auto_wrap_labels(container):
        for child in container.winfo_children():
            class_name = child.winfo_class()
            text = widget_text(child)
            textvariable = widget_textvariable(child)
            if class_name in ("TLabel", "Label") and (text or textvariable):
                if text == "尚未截图":
                    continue
                minimum = 180
                style = ""
                with _suppress(Exception):
                    style = str(child.cget("style"))
                if style == "Title.TLabel":
                    minimum = 240
                wrap_label_to_available_width(child, minimum=minimum)
                manager = ""
                with _suppress(Exception):
                    manager = child.winfo_manager()
                if manager == "grid":
                    safe_grid(child, sticky="ew")
            auto_wrap_labels(child)

    def reflow_wireless_panel(self, parent):
        panel = find_panel(parent, "无线 ADB")
        if panel is None:
            return
        for column in range(5):
            with _suppress(Exception):
                panel.columnconfigure(column, weight=(1 if column in (1, 3, 4) else 0))

        pair_var = variable_name(getattr(self, "wireless_pair_code_var", None))
        manual_var = variable_name(getattr(self, "wireless_manual_address_var", None))
        status_var = variable_name(getattr(self, "wireless_status_var", None))

        for child in panel.winfo_children():
            text = widget_text(child)
            textvariable = widget_textvariable(child)
            info = {}
            with _suppress(Exception):
                info = child.grid_info()

            if text == "发现设备":
                safe_grid(child, row=0, column=0, sticky="w", padx=(0, 8), pady=4)
            elif text == "配对码":
                safe_grid(child, row=1, column=0, sticky="w", padx=(0, 8), pady=4)
            elif text == "手动地址":
                safe_grid(child, row=2, column=0, sticky="w", padx=(0, 8), pady=4)
            elif textvariable and textvariable == pair_var:
                safe_grid(child, row=1, column=1, columnspan=4, sticky="ew", pady=4)
            elif textvariable and textvariable == manual_var:
                safe_grid(child, row=2, column=1, columnspan=4, sticky="ew", pady=4)
            elif textvariable and textvariable == status_var:
                safe_grid(child, row=4, column=0, columnspan=5, sticky="ew", pady=(10, 0))
                wrap_label_to_available_width(child, minimum=220)
            elif info and int(info.get("row", -1)) == 2:
                safe_grid(child, row=3, column=0, columnspan=5, sticky="ew", pady=(8, 0))
                with _suppress(Exception):
                    buttons = list(child.winfo_children())
                    for button in buttons:
                        button.grid_forget()
                    row = 0
                    column = 0
                    used = 0
                    available = max(240, panel.winfo_width() - 28)
                    for button in buttons:
                        requested = max(96, button.winfo_reqwidth())
                        if column > 0 and used + requested + 10 > available:
                            row += 1
                            column = 0
                            used = 0
                        button.grid(row=row, column=column, sticky="w", padx=(0, 10), pady=(0, 8))
                        used += requested + 10
                        column += 1

        with _suppress(Exception):
            self.wireless_device_combo.grid_configure(row=0, column=1, columnspan=4, sticky="ew", pady=4)

    def apply_page_adjustments(self, parent):
        if getattr(self, "active_page", None) == "device":
            reflow_wireless_panel(self, parent)
        auto_wrap_labels(parent)

    def wrap_page_method(name, original):
        def wrapped(self, parent):
            result = original(self, parent)
            apply_page_adjustments(self, parent)
            with _suppress(Exception):
                parent.after_idle(lambda: apply_page_adjustments(self, parent))
            return result

        wrapped.__name__ = getattr(original, "__name__", name)
        return wrapped

    for method_name, original in originals.items():
        setattr(DesktopApp, method_name, wrap_page_method(method_name, original))


_patch_adaptive_text_wrapping_ui()
del _patch_adaptive_text_wrapping_ui


def _patch_wireless_debug_keepalive_page():
    original_init = DesktopApp.__init__
    original_build_sidebar = DesktopApp._build_sidebar
    original_show_page = DesktopApp._show_page
    original_on_close = DesktopApp.on_close

    def _saved_wireless_debug_serial():
        try:
            from .wireless_adb import load_config

            return str(load_config().get("serial") or "").strip()
        except Exception:
            return ""

    def _saved_wireless_debug_interval():
        try:
            from .wireless_adb import load_config

            return int(load_config().get("keepalive_interval_seconds") or 60)
        except Exception:
            return 60

    def _saved_wireless_debug_enabled():
        try:
            from .wireless_adb import load_config

            return bool(load_config().get("keepalive_enabled", False))
        except Exception:
            return False

    def _current_serial_value(self):
        for attr in ("serial_var", "wireless_manual_address_var"):
            var = getattr(self, attr, None)
            if var is None:
                continue
            with _suppress(Exception):
                value = str(var.get() or "").strip()
            if value:
                return value
        return _saved_wireless_debug_serial()

    def _set_mode_wireless(self, serial):
        if serial:
            with _suppress(Exception):
                self.serial_var.set(serial)
            with _suppress(Exception):
                self.wireless_manual_address_var.set(serial)
        with _suppress(Exception):
            self.connection_mode_var.set(_connection_mode_to_label("wireless"))
        with _suppress(Exception):
            self.apply_connection_mode()

    def _set_keepalive_buttons_busy(self, busy, message=None):
        self.wireless_debug_busy = bool(busy)
        for button in getattr(self, "wireless_debug_buttons", []):
            with _suppress(Exception):
                button.configure(state=("disabled" if busy else "normal"))
        if message:
            with _suppress(Exception):
                self.wireless_debug_result_var.set(message)

    def _set_connection_status_text(self, snapshot):
        current = snapshot.current_label
        line = f"当前连接：{snapshot.mode_label}；当前使用：{current}"
        if snapshot.mode_label == "有线 + 无线" and "无线" in current:
            line += "；USB 可作为重新开启无线连接的备用通道"
        elif snapshot.mode_label == "有线 + 无线":
            line += "；建议开启后优先使用无线"
        with _suppress(Exception):
            self.connection_mode_status_var.set(line)

    def _update_wireless_debug_status(self, snapshot=None, event=None):
        if snapshot is None:
            try:
                from .adb_keepalive import get_connection_snapshot

                snapshot = get_connection_snapshot(_current_serial_value(self))
            except Exception as exc:
                with _suppress(Exception):
                    self.wireless_debug_connection_var.set("当前连接：连接异常")
                    self.wireless_debug_result_var.set(str(exc))
                return

        keepalive = getattr(self, "_adb_keepalive", None)
        keepalive_running = bool(keepalive is not None and keepalive.is_running)
        saved_enabled = _saved_wireless_debug_enabled()
        keepalive_text = "已开启" if keepalive_running or saved_enabled else "未开启"
        serial = getattr(keepalive, "serial", "") if keepalive_running else _saved_wireless_debug_serial()

        with _suppress(Exception):
            self.wireless_debug_connection_var.set(f"当前连接：{snapshot.mode_label}")
            self.wireless_debug_current_var.set(f"当前使用：{snapshot.current_label}")
            self.wireless_debug_usb_var.set(f"USB 设备：{snapshot.usb_label}")
            self.wireless_debug_wireless_var.set(f"无线设备：{snapshot.wireless_label}")
            self.wireless_debug_abnormal_var.set(f"异常设备：{snapshot.abnormal_label}")
            self.wireless_debug_keepalive_var.set(
                f"24小时连接：{keepalive_text}" + (f"（{serial}）" if serial else "")
            )
            if event is not None:
                self.wireless_debug_last_check_var.set(
                    f"最后检查：{event.checked_at.strftime('%H:%M:%S')}"
                )
                self.wireless_debug_result_var.set(f"最后结果：{event.message}")
        _set_connection_status_text(self, snapshot)

    def _start_keepalive_thread(self, serial, interval_seconds=None):
        from .adb_keepalive import AdbKeepAlive, save_keepalive_config

        target = str(serial or "").strip()
        if not target:
            raise RuntimeError("没有无线地址，无法开启24小时连接")
        interval = int(interval_seconds or _saved_wireless_debug_interval() or 60)
        existing = getattr(self, "_adb_keepalive", None)
        if existing is not None and existing.is_running and existing.serial == target:
            return existing
        if existing is not None:
            existing.stop()

        def log(message):
            with _suppress(Exception):
                self._log(f"无线保活: {message}")

        def on_event(event):
            def apply_event():
                _update_wireless_debug_status(self, event=event)

            with _suppress(Exception):
                self.root.after(0, apply_event)

        keeper = AdbKeepAlive(target, interval_seconds=interval, log=log, on_event=on_event)
        self._adb_keepalive = keeper
        save_keepalive_config(target, enabled=True, interval_seconds=interval)
        keeper.start()
        _set_mode_wireless(self, target)
        _update_wireless_debug_status(self)
        return keeper

    def _run_wireless_debug_task(self, message, worker, on_success):
        if getattr(self, "wireless_debug_busy", False):
            with _suppress(Exception):
                self.wireless_debug_result_var.set("无线调试操作正在处理中，请稍等。")
            return
        _set_keepalive_buttons_busy(self, True, message)

        def job():
            result = None
            error = None
            try:
                result = worker()
            except Exception as exc:
                error = str(exc)

            def finish():
                _set_keepalive_buttons_busy(self, False)
                if error:
                    with _suppress(Exception):
                        self.wireless_debug_result_var.set(f"最后结果：{error}")
                    with _suppress(Exception):
                        self._log(f"无线调试: {error}")
                    _update_wireless_debug_status(self)
                    return
                on_success(result)
                _update_wireless_debug_status(self)

            with _suppress(Exception):
                self.root.after(0, finish)

        _threading.Thread(target=job, name="WirelessDebugTask", daemon=True).start()

    def refresh_wireless_debug_status(self):
        from .adb_keepalive import get_connection_snapshot

        def worker():
            return get_connection_snapshot(_current_serial_value(self))

        def done(snapshot):
            _update_wireless_debug_status(self, snapshot=snapshot)
            with _suppress(Exception):
                self.wireless_debug_last_check_var.set(f"最后检查：{_datetime.now().strftime('%H:%M:%S')}")
                self.wireless_debug_result_var.set("最后结果：状态已刷新")

        _run_wireless_debug_task(self, "正在刷新连接状态...", worker, done)

    def enable_24h_wireless_debug(self):
        from .adb_keepalive import enable_long_wireless_debug

        preferred = _current_serial_value(self)
        if ":" in preferred:
            preferred = ""

        def worker():
            return enable_long_wireless_debug(usb_serial=preferred, port=5555, interval_seconds=60)

        def done(result):
            _set_mode_wireless(self, result.serial)
            _start_keepalive_thread(self, result.serial, 60)
            with _suppress(Exception):
                self.wireless_debug_result_var.set(f"最后结果：{result.message}")
            with _suppress(Exception):
                self._log(f"无线调试: 已开启24小时连接 {result.serial}")

        _run_wireless_debug_task(self, "正在开启24小时无线连接...", worker, done)

    def stop_24h_wireless_debug(self):
        from .adb_keepalive import disable_keepalive_config

        keeper = getattr(self, "_adb_keepalive", None)
        if keeper is not None:
            keeper.stop()
        self._adb_keepalive = None
        disable_keepalive_config()
        with _suppress(Exception):
            self.wireless_debug_result_var.set("最后结果：已停止24小时无线保活，当前无线连接不会被主动断开")
        with _suppress(Exception):
            self._log("无线调试: 已停止24小时无线保活")
        _update_wireless_debug_status(self)

    def test_wireless_debug_connection(self):
        from .adb_keepalive import AdbKeepAlive

        serial = _saved_wireless_debug_serial() or _current_serial_value(self)

        def worker():
            if not serial or ":" not in serial:
                from .adb_keepalive import get_connection_snapshot

                return get_connection_snapshot(serial)
            keeper = getattr(self, "_adb_keepalive", None)
            if keeper is None or not keeper.is_running or keeper.serial != serial:
                keeper = AdbKeepAlive(serial, interval_seconds=60)
            return keeper.ensure_connected()

        def done(result):
            if hasattr(result, "devices"):
                _update_wireless_debug_status(self, snapshot=result)
                self.wireless_debug_result_var.set("最后结果：没有无线地址，仅刷新当前连接状态")
                return
            _set_mode_wireless(self, result.serial)
            self.wireless_debug_last_check_var.set(f"最后检查：{result.checked_at.strftime('%H:%M:%S')}")
            self.wireless_debug_result_var.set(f"最后结果：{result.message}")

        _run_wireless_debug_task(self, "正在测试无线连接...", worker, done)

    def init_with_wireless_debug_page(self, root):
        self.wireless_debug_connection_var = tk.StringVar(value="当前连接：检查中")
        self.wireless_debug_current_var = tk.StringVar(value="当前使用：未指定")
        self.wireless_debug_usb_var = tk.StringVar(value="USB 设备：检查中")
        self.wireless_debug_wireless_var = tk.StringVar(value="无线设备：检查中")
        self.wireless_debug_abnormal_var = tk.StringVar(value="异常设备：无")
        self.wireless_debug_keepalive_var = tk.StringVar(value="24小时连接：未开启")
        self.wireless_debug_last_check_var = tk.StringVar(value="最后检查：尚未检查")
        self.wireless_debug_result_var = tk.StringVar(value="最后结果：尚无")
        self.wireless_debug_busy = False
        self.wireless_debug_buttons = []
        self._adb_keepalive = None
        original_init(self, root)
        with _suppress(Exception):
            root.title("三角洲助手")
        with _suppress(Exception):
            root.after(800, lambda: _update_wireless_debug_status(self))
        if _saved_wireless_debug_enabled():
            serial = _saved_wireless_debug_serial()
            if serial:
                with _suppress(Exception):
                    root.after(1500, lambda: _start_keepalive_thread(self, serial, _saved_wireless_debug_interval()))

    def build_sidebar_with_wireless_debug(self, parent):
        original_build_sidebar(self, parent)
        button = self._button(parent, "无线调试", lambda: self._show_page("wireless"))
        with _suppress(Exception):
            button.configure(
                bg=self.colors["sidebar"],
                fg="#334155",
                activebackground=self.colors["sidebar_hover"],
                activeforeground=self.colors["text"],
                highlightbackground=self.colors["sidebar"],
            )
        with _suppress(Exception):
            button._anchor = "w"
            button._padx = 18
            button._redraw()
        pack_options = {"fill": "x", "padx": 12, "pady": 4}
        logs_button = getattr(self, "nav_buttons", {}).get("logs")
        if logs_button is not None:
            pack_options["before"] = logs_button
        button.pack(**pack_options)
        self.nav_buttons["wireless"] = button

    def show_page_with_wireless_debug(self, page):
        if page == "wireless":
            self.active_page = page
            for key, button in self.nav_buttons.items():
                active = key == page
                with _suppress(Exception):
                    button.configure(
                        bg=(self.colors["sidebar_active"] if active else self.colors["sidebar"]),
                        fg=("#ffffff" if active else "#334155"),
                        activebackground=("#1d4ed8" if active else self.colors["sidebar_hover"]),
                        activeforeground=("#ffffff" if active else self.colors["text"]),
                        highlightbackground=(self.colors["sidebar_active"] if active else self.colors["sidebar"]),
                    )
            for child in self.page_frame.winfo_children():
                child.destroy()
            content = getattr(self, "_content_frame", None)
            page_shell = getattr(self, "_page_shell", None)
            side_canvas = getattr(self, "_status_side_canvas", None)
            page_scrollbar = getattr(self, "_page_scrollbar", None)
            page_canvas = getattr(self, "_page_canvas", None)
            if content is not None and page_shell is not None:
                content.grid_columnconfigure(0, weight=2)
                content.grid_columnconfigure(1, weight=1)
                with _suppress(Exception):
                    page_shell.grid_configure(column=0, columnspan=1, sticky="nsew", padx=(0, 10))
                with _suppress(Exception):
                    side_canvas.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
                with _suppress(Exception):
                    page_scrollbar.grid(row=0, column=1, sticky="ns")
                if page_canvas is not None and page_scrollbar is not None:
                    with _suppress(Exception):
                        page_canvas.configure(yscrollcommand=page_scrollbar.set)
            self._page_wireless_debug(self.page_frame)
            canvas = getattr(self, "_page_canvas", None)
            if canvas is not None:
                with _suppress(Exception):
                    canvas.update_idletasks()
                    page_window = getattr(self, "_page_window", None)
                    if page_window is not None:
                        canvas.itemconfigure(page_window, width=max(1, canvas.winfo_width()))
                        canvas.itemconfigure(page_window, height=0)
                    canvas.configure(scrollregion=canvas.bbox("all"))
                    canvas.yview_moveto(0)
            return
        if page != "wireless":
            return original_show_page(self, page)

    def _wireless_debug_line(parent, row, variable, strong=False):
        style = "Section.TLabel" if strong else "Surface.TLabel"
        label = ttk.Label(parent, textvariable=variable, style=style, wraplength=760)
        label.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        return label

    def page_wireless_debug(self, parent):
        self._page_title(
            parent,
            "无线调试",
            "开启后程序会优先使用无线 ADB，并在电脑端持续检查和自动重连。",
        )

        panel = ttk.LabelFrame(parent, text="连接状态", padding=(16, 14, 16, 14))
        panel.pack(fill="x", pady=(0, 14))
        panel.columnconfigure(0, weight=1)
        _wireless_debug_line(panel, 0, self.wireless_debug_connection_var, strong=True)
        _wireless_debug_line(panel, 1, self.wireless_debug_current_var)
        _wireless_debug_line(panel, 2, self.wireless_debug_usb_var)
        _wireless_debug_line(panel, 3, self.wireless_debug_wireless_var)
        _wireless_debug_line(panel, 4, self.wireless_debug_abnormal_var)

        keepalive_panel = ttk.LabelFrame(parent, text="24小时无线连接", padding=(16, 14, 16, 14))
        keepalive_panel.pack(fill="x", pady=(0, 14))
        keepalive_panel.columnconfigure(0, weight=1)
        _wireless_debug_line(keepalive_panel, 0, self.wireless_debug_keepalive_var, strong=True)
        _wireless_debug_line(keepalive_panel, 1, self.wireless_debug_last_check_var)
        _wireless_debug_line(keepalive_panel, 2, self.wireless_debug_result_var)

        buttons = ttk.Frame(keepalive_panel, style="Surface.TFrame")
        buttons.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.wireless_debug_buttons = []
        for text, command, accent, danger in (
            ("开启24小时无线连接", self.enable_24h_wireless_debug, True, False),
            ("停止24小时连接", self.stop_24h_wireless_debug, False, True),
            ("测试连接", self.test_wireless_debug_connection, False, False),
            ("刷新设备", self.refresh_wireless_debug_status, False, False),
        ):
            button = self._button(buttons, text, command, accent=accent, danger=danger)
            self.wireless_debug_buttons.append(button)

        def reflow_wireless_debug_buttons(event=None):
            available_width = max(220, buttons.winfo_width())
            row = 0
            column = 0
            used_width = 0
            for child in getattr(self, "wireless_debug_buttons", []):
                with _suppress(Exception):
                    child.grid_forget()
            for child in getattr(self, "wireless_debug_buttons", []):
                requested_width = max(96, child.winfo_reqwidth()) + 12
                if column > 0 and used_width + requested_width > available_width:
                    row += 1
                    column = 0
                    used_width = 0
                with _suppress(Exception):
                    child.grid(row=row, column=column, sticky="w", padx=(0, 10), pady=(0, 8))
                used_width += requested_width
                column += 1

        with _suppress(Exception):
            buttons.bind("<Configure>", lambda _event: buttons.after_idle(reflow_wireless_debug_buttons), add="+")
            buttons.after_idle(reflow_wireless_debug_buttons)

        note = ttk.LabelFrame(parent, text="使用限制", padding=(16, 14, 16, 14))
        note.pack(fill="x")
        ttk.Label(
            note,
            text=(
                "未 Root 手机无法由电脑永久打开系统无线调试。此功能会通过 USB 执行 adb tcpip 5555，"
                "然后在电脑端保活重连；手机重启后需要重新插 USB 开启一次。只建议在可信 Wi-Fi 下使用。"
            ),
            style="Hint.TLabel",
            wraplength=820,
        ).pack(anchor="w")
        _update_wireless_debug_status(self)

    def on_close_with_wireless_debug(self):
        keeper = getattr(self, "_adb_keepalive", None)
        if keeper is not None:
            with _suppress(Exception):
                keeper.stop()
        return original_on_close(self)

    DesktopApp.__init__ = init_with_wireless_debug_page
    DesktopApp._build_sidebar = build_sidebar_with_wireless_debug
    DesktopApp._show_page = show_page_with_wireless_debug
    DesktopApp._page_wireless_debug = page_wireless_debug
    DesktopApp.refresh_wireless_debug_status = refresh_wireless_debug_status
    DesktopApp.enable_24h_wireless_debug = enable_24h_wireless_debug
    DesktopApp.stop_24h_wireless_debug = stop_24h_wireless_debug
    DesktopApp.test_wireless_debug_connection = test_wireless_debug_connection
    DesktopApp.on_close = on_close_with_wireless_debug


_patch_wireless_debug_keepalive_page()
del _patch_wireless_debug_keepalive_page


def _patch_wait_settings_page():
    original_init = DesktopApp.__init__
    original_build_sidebar = DesktopApp._build_sidebar
    original_show_page = DesktopApp._show_page

    def _format_seconds(value):
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return f"{number:.2f}".rstrip("0").rstrip(".")

    def init_with_wait_settings_page(self, root):
        from .wait_settings import load_wait_settings, wait_setting_items

        self.wait_setting_items = wait_setting_items()
        settings = load_wait_settings()
        self.wait_setting_vars = {
            item["key"]: tk.StringVar(value=_format_seconds(settings.get(item["key"], item["default"])))
            for item in self.wait_setting_items
        }
        self.wait_settings_status_var = tk.StringVar(value="等待时间已加载")
        original_init(self, root)

    def build_sidebar_with_wait_settings(self, parent):
        original_build_sidebar(self, parent)
        button = self._button(parent, "等待时间", lambda: self._show_page("waits"))
        with _suppress(Exception):
            button.configure(
                bg=self.colors["sidebar"],
                fg="#334155",
                activebackground=self.colors["sidebar_hover"],
                activeforeground=self.colors["text"],
                highlightbackground=self.colors["sidebar"],
            )
        with _suppress(Exception):
            button._anchor = "w"
            button._padx = 18
            button._redraw()
        pack_options = {"fill": "x", "padx": 12, "pady": 4}
        before_button = getattr(self, "nav_buttons", {}).get("wireless") or getattr(self, "nav_buttons", {}).get("logs")
        if before_button is not None:
            pack_options["before"] = before_button
        button.pack(**pack_options)
        self.nav_buttons["waits"] = button

    def _show_regular_scroll_page(self, page, builder):
        self.active_page = page
        for key, button in self.nav_buttons.items():
            active = key == page
            with _suppress(Exception):
                button.configure(
                    bg=(self.colors["sidebar_active"] if active else self.colors["sidebar"]),
                    fg=("#ffffff" if active else "#334155"),
                    activebackground=("#1d4ed8" if active else self.colors["sidebar_hover"]),
                    activeforeground=("#ffffff" if active else self.colors["text"]),
                    highlightbackground=(self.colors["sidebar_active"] if active else self.colors["sidebar"]),
                )
        for child in self.page_frame.winfo_children():
            child.destroy()
        self.log_text = None
        content = getattr(self, "_content_frame", None)
        page_shell = getattr(self, "_page_shell", None)
        side_canvas = getattr(self, "_status_side_canvas", None)
        page_scrollbar = getattr(self, "_page_scrollbar", None)
        page_canvas = getattr(self, "_page_canvas", None)
        if content is not None and page_shell is not None:
            content.grid_columnconfigure(0, weight=2)
            content.grid_columnconfigure(1, weight=1)
            with _suppress(Exception):
                page_shell.grid_configure(column=0, columnspan=1, sticky="nsew", padx=(0, 10))
            with _suppress(Exception):
                side_canvas.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            with _suppress(Exception):
                page_scrollbar.grid(row=0, column=1, sticky="ns")
            if page_canvas is not None and page_scrollbar is not None:
                with _suppress(Exception):
                    page_canvas.configure(yscrollcommand=page_scrollbar.set)
        builder(self.page_frame)
        canvas = getattr(self, "_page_canvas", None)
        if canvas is not None:
            with _suppress(Exception):
                canvas.update_idletasks()
                page_window = getattr(self, "_page_window", None)
                if page_window is not None:
                    canvas.itemconfigure(page_window, width=max(1, canvas.winfo_width()))
                    canvas.itemconfigure(page_window, height=0)
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.yview_moveto(0)

    def show_page_with_wait_settings(self, page):
        if page == "waits":
            return _show_regular_scroll_page(self, page, self._page_wait_settings)
        return original_show_page(self, page)

    def _read_wait_settings_from_vars(self):
        values = {}
        for index, item in enumerate(getattr(self, "wait_setting_items", []), start=1):
            key = item["key"]
            raw = self.wait_setting_vars[key].get().strip()
            try:
                seconds = float(raw)
            except ValueError as exc:
                raise ValueError(f"第 {index} 项“{item['label']}”必须是数字") from exc
            minimum = float(item["minimum"])
            maximum = float(item["maximum"])
            if seconds < minimum or seconds > maximum:
                raise ValueError(
                    f"第 {index} 项“{item['label']}”必须在 {_format_seconds(minimum)} 到 {_format_seconds(maximum)} 秒之间"
                )
            values[key] = seconds
        return values

    def _apply_wait_settings_to_vars(self, settings):
        for item in getattr(self, "wait_setting_items", []):
            key = item["key"]
            var = self.wait_setting_vars.get(key)
            if var is not None:
                var.set(_format_seconds(settings.get(key, item["default"])))

    def save_wait_settings_page(self):
        from tkinter import messagebox as _messagebox
        from .wait_settings import save_wait_settings

        try:
            values = _read_wait_settings_from_vars(self)
            normalized = save_wait_settings(values)
        except Exception as exc:
            with _suppress(Exception):
                self.wait_settings_status_var.set(str(exc))
            _messagebox.showerror("等待时间", str(exc), parent=self.root)
            return
        _apply_wait_settings_to_vars(self, normalized)
        self.wait_settings_status_var.set("已保存，下一次启动任务会使用新的等待时间")
        with _suppress(Exception):
            self._log("等待时间: 已保存")

    def reset_wait_settings_page(self):
        from .wait_settings import reset_wait_settings

        settings = reset_wait_settings()
        _apply_wait_settings_to_vars(self, settings)
        self.wait_settings_status_var.set("已恢复默认等待时间")
        with _suppress(Exception):
            self._log("等待时间: 已恢复默认")

    def _wait_row(parent, row, label_text, item, variable, wrap_labels):
        label = ttk.Label(parent, text=label_text, style="Surface.TLabel", wraplength=560, justify="left")
        label.grid(row=row, column=0, sticky="ew", pady=6, padx=(0, 12))
        wrap_labels.append(label)
        spinbox = ttk.Spinbox(
            parent,
            from_=float(item["minimum"]),
            to=float(item["maximum"]),
            increment=0.1,
            textvariable=variable,
            width=8,
            justify="center",
        )
        spinbox.grid(row=row, column=1, sticky="e", pady=6, padx=(0, 8))
        ttk.Label(parent, text="秒", style="Surface.TLabel").grid(row=row, column=2, sticky="w", pady=6)

    def page_wait_settings(self, parent):
        self._page_title(parent, "等待时间", "调整每个关键步骤后停顿的秒数。")

        panel = ttk.LabelFrame(parent, text="流程等待", padding=(16, 14, 16, 14))
        panel.pack(fill="x", pady=(0, 14))
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=0)
        wrap_labels = []

        for index, item in enumerate(getattr(self, "wait_setting_items", []), start=1):
            key = item["key"]
            variable = self.wait_setting_vars[key]
            _wait_row(panel, index - 1, f"{index}. {item['label']}", item, variable, wrap_labels)

        def update_wrap(event=None):
            with _suppress(Exception):
                width = max(260, panel.winfo_width() - 180)
                for label in wrap_labels:
                    label.configure(wraplength=width)

        update_wrap()
        with _suppress(Exception):
            panel.bind("<Configure>", update_wrap, add="+")

        actions = ttk.Frame(parent, style="Surface.TFrame")
        actions.pack(fill="x", pady=(0, 10))
        self._button(actions, "保存", self.save_wait_settings_page, accent=True).pack(side="left", padx=(0, 10))
        self._button(actions, "恢复默认", self.reset_wait_settings_page).pack(side="left", padx=(0, 10))

        ttk.Label(
            parent,
            textvariable=self.wait_settings_status_var,
            style="Muted.TLabel",
            wraplength=820,
        ).pack(anchor="w")

    DesktopApp.__init__ = init_with_wait_settings_page
    DesktopApp._build_sidebar = build_sidebar_with_wait_settings
    DesktopApp._show_page = show_page_with_wait_settings
    DesktopApp._show_regular_scroll_page = _show_regular_scroll_page
    DesktopApp._page_wait_settings = page_wait_settings
    DesktopApp.save_wait_settings_page = save_wait_settings_page
    DesktopApp.reset_wait_settings_page = reset_wait_settings_page


_patch_wait_settings_page()
del _patch_wait_settings_page


def _patch_power_control_page():
    original_init = DesktopApp.__init__
    original_build_sidebar = DesktopApp._build_sidebar
    original_show_page = DesktopApp._show_page

    def init_with_power_control(self, root):
        from .power_control import action_label, load_power_config

        config = load_power_config()
        self.power_action_var = tk.StringVar(value=action_label(config.get("power_action", "shutdown")))
        self.power_time_var = tk.StringVar(value=str(config.get("power_time", "23:30")))
        self.power_force_var = tk.BooleanVar(value=bool(config.get("force_close", False)))
        self.power_wake_time_var = tk.StringVar(value=str(config.get("wake_time", "08:00")))
        self.power_status_var = tk.StringVar(value="电脑电源计划已加载")
        original_init(self, root)

    def build_sidebar_with_power(self, parent):
        original_build_sidebar(self, parent)
        button = self._button(parent, "电脑电源", lambda: self._show_page("power"))
        with _suppress(Exception):
            button.configure(
                bg=self.colors["sidebar"],
                fg="#334155",
                activebackground=self.colors["sidebar_hover"],
                activeforeground=self.colors["text"],
                highlightbackground=self.colors["sidebar"],
            )
        with _suppress(Exception):
            button._anchor = "w"
            button._padx = 18
            button._redraw()
        pack_options = {"fill": "x", "padx": 12, "pady": 4}
        logs_button = getattr(self, "nav_buttons", {}).get("logs")
        if logs_button is not None:
            pack_options["before"] = logs_button
        button.pack(**pack_options)
        self.nav_buttons["power"] = button

    def show_page_with_power(self, page):
        if page == "power":
            return self._show_regular_scroll_page(page, self._page_power_control)
        return original_show_page(self, page)

    def _power_config_from_vars(self):
        from .power_control import action_from_label, normalize_hhmm

        return {
            "power_action": action_from_label(self.power_action_var.get()),
            "power_time": normalize_hhmm(self.power_time_var.get()),
            "force_close": bool(self.power_force_var.get()),
            "wake_time": normalize_hhmm(self.power_wake_time_var.get()),
        }

    def _apply_power_config_to_vars(self, config):
        from .power_control import action_label

        self.power_action_var.set(action_label(config.get("power_action", "shutdown")))
        self.power_time_var.set(str(config.get("power_time", "23:30")))
        self.power_force_var.set(bool(config.get("force_close", False)))
        self.power_wake_time_var.set(str(config.get("wake_time", "08:00")))

    def _run_power_task(self, message, worker):
        self.power_status_var.set(message)

        def job():
            result = None
            error = None
            try:
                result = worker()
            except Exception as exc:
                error = str(exc)

            def finish():
                if error:
                    self.power_status_var.set(error)
                    with _suppress(Exception):
                        self._log(f"电脑电源: {error}")
                    return
                self.power_status_var.set(str(result))
                with _suppress(Exception):
                    self._log(f"电脑电源: {result}")

            with _suppress(Exception):
                self.root.after(0, finish)

        _threading.Thread(target=job, name="PowerControlTask", daemon=True).start()

    def save_power_settings(self):
        from tkinter import messagebox as _messagebox
        from .power_control import save_power_config

        try:
            config = save_power_config(_power_config_from_vars(self))
        except Exception as exc:
            self.power_status_var.set(str(exc))
            _messagebox.showerror("电脑电源", str(exc), parent=self.root)
            return
        _apply_power_config_to_vars(self, config)
        self.power_status_var.set("已保存电脑电源设置")

    def create_power_action_task(self):
        from tkinter import messagebox as _messagebox
        from .power_control import action_label, save_power_config, schedule_power_action

        try:
            config = save_power_config(_power_config_from_vars(self))
        except Exception as exc:
            self.power_status_var.set(str(exc))
            _messagebox.showerror("电脑电源", str(exc), parent=self.root)
            return
        label = action_label(config["power_action"])
        if not _messagebox.askyesno(
            "电脑电源",
            f"创建计划后，电脑会在 {config['power_time']} 自动{label}。确认创建？",
            parent=self.root,
        ):
            return

        def worker():
            return schedule_power_action(config["power_action"], config["power_time"], config["force_close"])

        _run_power_task(self, "正在创建电脑电源计划...", worker)

    def cancel_power_action_task(self):
        from .power_control import cancel_power_action

        _run_power_task(self, "正在取消电脑电源计划...", cancel_power_action)

    def create_wake_task(self):
        from tkinter import messagebox as _messagebox
        from .power_control import save_power_config, schedule_wake

        try:
            config = save_power_config(_power_config_from_vars(self))
        except Exception as exc:
            self.power_status_var.set(str(exc))
            _messagebox.showerror("电脑电源", str(exc), parent=self.root)
            return
        if not _messagebox.askyesno(
            "电脑电源",
            f"创建计划后，电脑会在 {config['wake_time']} 尝试从睡眠/休眠唤醒。确认创建？",
            parent=self.root,
        ):
            return

        def worker():
            return schedule_wake(config["wake_time"])

        _run_power_task(self, "正在创建唤醒计划...", worker)

    def cancel_wake_task(self):
        from .power_control import cancel_wake

        _run_power_task(self, "正在取消唤醒计划...", cancel_wake)

    def create_daily_sleep_wake_cycle(self):
        from tkinter import messagebox as _messagebox
        from .power_control import save_power_config, schedule_daily_sleep_wake_cycle

        try:
            config = save_power_config(_power_config_from_vars(self))
        except Exception as exc:
            self.power_status_var.set(str(exc))
            _messagebox.showerror("电脑电源", str(exc), parent=self.root)
            return
        if not _messagebox.askyesno(
            "电脑电源",
            f"创建后，电脑会每天 {config['power_time']} 睡眠，并每天 {config['wake_time']} 从睡眠唤醒。确认创建？",
            parent=self.root,
        ):
            return

        def worker():
            return schedule_daily_sleep_wake_cycle(config["power_time"], config["wake_time"], config["force_close"])

        _run_power_task(self, "正在创建每天省电循环...", worker)

    def cancel_daily_sleep_wake_cycle(self):
        from .power_control import cancel_power_action, cancel_wake

        def worker():
            first = cancel_power_action()
            second = cancel_wake()
            return f"{first}；{second}"

        _run_power_task(self, "正在取消每天省电循环...", worker)

    def _power_button_row(app, parent, buttons):
        row = ttk.Frame(parent, style="Surface.TFrame")
        row.grid(sticky="ew", pady=(10, 0))
        for text, command, accent, danger in buttons:
            button = app._button(row, text, command, accent=accent, danger=danger)
            button.pack(side="left", padx=(0, 10), pady=(0, 8))
        return row

    def _wrap_power_label(label, container, minimum=220, margin=34):
        def update(event=None):
            with _suppress(Exception):
                width = max(minimum, container.winfo_width() - margin)
                label.configure(wraplength=width, justify="left")

        update()
        with _suppress(Exception):
            container.bind("<Configure>", update, add="+")
            label.after_idle(update)

    def page_power_control(self, parent):
        from .power_control import power_action_items

        self._page_title(parent, "电脑电源", "管理 Windows 自动关机、睡眠、休眠、重启和定时唤醒。")

        power_panel = ttk.LabelFrame(parent, text="自动关机/睡眠", padding=(16, 14, 16, 14))
        power_panel.pack(fill="x", pady=(0, 14))
        power_panel.columnconfigure(1, weight=1)

        ttk.Label(power_panel, text="动作", style="Surface.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 12))
        action_labels = [label for _key, label in power_action_items()]
        ttk.Combobox(
            power_panel,
            textvariable=self.power_action_var,
            values=action_labels,
            state="readonly",
            width=12,
        ).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(power_panel, text="执行/睡眠时间", style="Surface.TLabel").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Entry(power_panel, textvariable=self.power_time_var, width=12).grid(row=1, column=1, sticky="w", pady=6)
        ttk.Checkbutton(
            power_panel,
            text="强制关闭正在运行的程序",
            variable=self.power_force_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        _power_button_row(
            self,
            power_panel,
            (
                ("保存设置", self.save_power_settings, False, False),
                ("创建计划", self.create_power_action_task, True, False),
                ("取消计划", self.cancel_power_action_task, False, True),
            ),
        )

        wake_panel = ttk.LabelFrame(parent, text="自动开机/唤醒", padding=(16, 14, 16, 14))
        wake_panel.pack(fill="x", pady=(0, 14))
        wake_panel.columnconfigure(1, weight=1)

        ttk.Label(wake_panel, text="唤醒时间", style="Surface.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 12))
        ttk.Entry(wake_panel, textvariable=self.power_wake_time_var, width=12).grid(row=0, column=1, sticky="w", pady=6)
        wake_hint = ttk.Label(
            wake_panel,
            text="完全关机后自动开机需要 BIOS 定时开机或 Wake-on-LAN；这里创建的是从睡眠/休眠唤醒的 Windows 计划。",
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        )
        wake_hint.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        _wrap_power_label(wake_hint, wake_panel)

        _power_button_row(
            self,
            wake_panel,
            (
                ("创建唤醒计划", self.create_wake_task, True, False),
                ("取消唤醒计划", self.cancel_wake_task, False, True),
            ),
        )

        cycle_panel = ttk.LabelFrame(parent, text="每天省电循环", padding=(16, 14, 16, 14))
        cycle_panel.pack(fill="x", pady=(0, 14))
        cycle_panel.columnconfigure(1, weight=1)

        cycle_hint = ttk.Label(
            cycle_panel,
            text="使用上面的执行时间作为每天睡眠时间，使用唤醒时间作为每天恢复时间。唤醒后程序会继续运行；建议让定时任务负责重连 ADB 和执行流程。",
            style="Hint.TLabel",
            wraplength=760,
            justify="left",
        )
        cycle_hint.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        _wrap_power_label(cycle_hint, cycle_panel)

        _power_button_row(
            self,
            cycle_panel,
            (
                ("创建每天省电循环", self.create_daily_sleep_wake_cycle, True, False),
                ("取消每天省电循环", self.cancel_daily_sleep_wake_cycle, False, True),
            ),
        )

        status_label = ttk.Label(
            parent,
            textvariable=self.power_status_var,
            style="Muted.TLabel",
            wraplength=820,
            justify="left",
        )
        status_label.pack(anchor="w", fill="x")
        _wrap_power_label(status_label, parent, minimum=240, margin=20)

    DesktopApp.__init__ = init_with_power_control
    DesktopApp._build_sidebar = build_sidebar_with_power
    DesktopApp._show_page = show_page_with_power
    DesktopApp._page_power_control = page_power_control
    DesktopApp.save_power_settings = save_power_settings
    DesktopApp.create_power_action_task = create_power_action_task
    DesktopApp.cancel_power_action_task = cancel_power_action_task
    DesktopApp.create_wake_task = create_wake_task
    DesktopApp.cancel_wake_task = cancel_wake_task
    DesktopApp.create_daily_sleep_wake_cycle = create_daily_sleep_wake_cycle
    DesktopApp.cancel_daily_sleep_wake_cycle = cancel_daily_sleep_wake_cycle


_patch_power_control_page()
del _patch_power_control_page


def _patch_power_event_log_bridge():
    original_init = DesktopApp.__init__

    def current_power_event_log_size():
        try:
            from .power_control import power_event_log_path

            path = power_event_log_path()
            return path.stat().st_size if path.exists() else 0
        except Exception:
            return 0

    def poll_power_event_log(self):
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            from .power_control import power_event_log_path

            path = power_event_log_path()
            offset = int(getattr(self, "_power_event_log_offset", 0) or 0)
            if path.exists():
                size = path.stat().st_size
                if offset > size:
                    offset = 0
                if size > offset:
                    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
                        handle.seek(offset)
                        text = handle.read()
                        self._power_event_log_offset = handle.tell()
                    for line in text.splitlines():
                        line = line.strip()
                        if line:
                            with _suppress(Exception):
                                self._log(line)
                else:
                    self._power_event_log_offset = size
        except Exception:
            pass
        with _suppress(Exception):
            root.after(1500, lambda: poll_power_event_log(self))

    def init_with_power_event_log_bridge(self, root):
        original_init(self, root)
        self._power_event_log_offset = current_power_event_log_size()
        with _suppress(Exception):
            root.after(1500, lambda: poll_power_event_log(self))

    DesktopApp.__init__ = init_with_power_event_log_bridge


_patch_power_event_log_bridge()
del _patch_power_event_log_bridge


def _patch_profile_reload_before_actions():
    original_schedule_config = DesktopApp._schedule_config
    original_start_schedule = DesktopApp.start_schedule
    original_run_qq_switch = DesktopApp.run_qq_switch
    original_run_qq_open = DesktopApp.run_qq_open
    original_run_delta_force = DesktopApp.run_delta_force
    original_run_full_flow = DesktopApp.run_full_flow

    def reload_profiles(self):
        try:
            from . import workflows as _workflows

            qq_profiles, delta_profiles = _workflows.refresh_device_profiles()
            globals()["QQ_DEVICE_PROFILES"] = qq_profiles
            globals()["DELTA_FORCE_DEVICE_PROFILES"] = delta_profiles
            with _suppress(Exception):
                self._refresh_profile_status()
        except Exception as exc:
            with _suppress(Exception):
                self._log(f"坐标预设刷新失败: {exc}")

    def schedule_config_with_profile_reload(self):
        reload_profiles(self)
        return original_schedule_config(self)

    def start_schedule_with_profile_reload(self):
        reload_profiles(self)
        return original_start_schedule(self)

    def run_qq_switch_with_profile_reload(self):
        reload_profiles(self)
        return original_run_qq_switch(self)

    def run_qq_open_with_profile_reload(self):
        reload_profiles(self)
        return original_run_qq_open(self)

    def run_delta_force_with_profile_reload(self):
        reload_profiles(self)
        return original_run_delta_force(self)

    def run_full_flow_with_profile_reload(self):
        reload_profiles(self)
        return original_run_full_flow(self)

    DesktopApp._reload_device_profiles = reload_profiles
    DesktopApp._schedule_config = schedule_config_with_profile_reload
    DesktopApp.start_schedule = start_schedule_with_profile_reload
    DesktopApp.run_qq_switch = run_qq_switch_with_profile_reload
    DesktopApp.run_qq_open = run_qq_open_with_profile_reload
    DesktopApp.run_delta_force = run_delta_force_with_profile_reload
    DesktopApp.run_full_flow = run_full_flow_with_profile_reload


_patch_profile_reload_before_actions()
del _patch_profile_reload_before_actions


def _patch_preflight_before_actions():
    original_init = DesktopApp.__init__
    original_run_worker = DesktopApp._run_worker
    original_page_device = DesktopApp._page_device
    original_run_qq_switch = DesktopApp.run_qq_switch
    original_run_qq_open = DesktopApp.run_qq_open
    original_run_delta_force = DesktopApp.run_delta_force
    original_run_full_flow = DesktopApp.run_full_flow

    def init_with_preflight(self, root):
        self.preflight_status_var = tk.StringVar(value="运行前体检：尚未检查")
        self._preflight_required = False
        original_init(self, root)

    def connection_mode(self):
        var = getattr(self, "connection_mode_var", None)
        text = ""
        with _suppress(Exception):
            text = str(var.get() if var is not None else "")
        lower = text.lower()
        if "wireless" in lower or "无线" in text:
            return "wireless"
        return "usb"

    def current_serial(self):
        for attr in ("serial_var", "wireless_manual_address_var"):
            var = getattr(self, attr, None)
            with _suppress(Exception):
                value = str(var.get() if var is not None else "").strip()
            if value:
                return value
        return ""

    def workflow_config(self):
        try:
            return self._schedule_config()
        except Exception as exc:
            with _suppress(Exception):
                self._log(f"Preflight config read warning: {exc}")
            return {}

    def run_manual_preflight(self):
        with _suppress(Exception):
            self.preflight_status_var.set("运行前体检：检查中...")
        serial = current_serial(self)
        mode = connection_mode(self)
        config = workflow_config(self)

        def job():
            result = None
            error = None
            try:
                from .preflight import run_preflight

                result = run_preflight(
                    serial=serial,
                    connection_mode=mode,
                    workflow_config=config,
                    auto_fix=True,
                )
            except Exception as exc:
                error = str(exc)

            def finish():
                if error:
                    with _suppress(Exception):
                        self.preflight_status_var.set(f"运行前体检失败：{error}")
                    with _suppress(Exception):
                        self._log(f"Preflight failed: {error}")
                    return
                if result is None:
                    return
                for line in result.lines():
                    with _suppress(Exception):
                        self._log(line)
                if result.serial:
                    with _suppress(Exception):
                        self.serial_var.set(result.serial)
                    if ":" in result.serial:
                        with _suppress(Exception):
                            self.wireless_manual_address_var.set(result.serial)
                if result.ok:
                    with _suppress(Exception):
                        self.preflight_status_var.set("运行前体检：通过")
                else:
                    with _suppress(Exception):
                        self.preflight_status_var.set("运行前体检：未通过")

            with _suppress(Exception):
                self.root.after(0, finish)

        _threading.Thread(target=job, name="PreflightManualCheck", daemon=True).start()

    def run_worker_with_preflight(self, name, target):
        if not getattr(self, "_preflight_required", False):
            return original_run_worker(self, name, target)
        preflight_serial = current_serial(self)
        preflight_mode = connection_mode(self)
        preflight_config = workflow_config(self)

        def guarded_target(*args, **kwargs):
            from .preflight import run_preflight

            result = run_preflight(
                serial=preflight_serial,
                connection_mode=preflight_mode,
                workflow_config=preflight_config,
                auto_fix=True,
            )
            for line in result.lines():
                self._log(line)
            if result.serial:
                with _suppress(Exception):
                    self.serial_var.set(result.serial)
                if ":" in result.serial:
                    with _suppress(Exception):
                        self.wireless_manual_address_var.set(result.serial)
            if not result.ok:
                with _suppress(Exception):
                    self.preflight_status_var.set("运行前体检：未通过，已阻止本次运行")
                with _suppress(Exception):
                    self._log(f"Preflight blocked task: {name}")
                return None
            with _suppress(Exception):
                self.preflight_status_var.set("运行前体检：通过")
            return target(*args, **kwargs)

        return original_run_worker(self, name, guarded_target)

    def mark_preflight_required(self, callback):
        self._preflight_required = True
        try:
            return callback()
        finally:
            self._preflight_required = False

    def run_qq_switch_with_preflight(self):
        return mark_preflight_required(self, lambda: original_run_qq_switch(self))

    def run_qq_open_with_preflight(self):
        return mark_preflight_required(self, lambda: original_run_qq_open(self))

    def run_delta_force_with_preflight(self):
        return mark_preflight_required(self, lambda: original_run_delta_force(self))

    def run_full_flow_with_preflight(self):
        return mark_preflight_required(self, lambda: original_run_full_flow(self))

    def page_device_with_preflight(self, parent):
        original_page_device(self, parent)
        panel = ttk.LabelFrame(parent, text="运行前体检", padding=(14, 12, 14, 12))
        panel.pack(fill="x", pady=(0, 14))
        self._button(panel, "立即体检", self.run_preflight_check, accent=True).pack(side="left", padx=(0, 10))
        ttk.Label(
            panel,
            textvariable=self.preflight_status_var,
            style="Hint.TLabel",
            wraplength=620,
        ).pack(side="left", fill="x", expand=True)

    DesktopApp.__init__ = init_with_preflight
    DesktopApp._run_worker = run_worker_with_preflight
    DesktopApp._page_device = page_device_with_preflight
    DesktopApp.run_qq_switch = run_qq_switch_with_preflight
    DesktopApp.run_qq_open = run_qq_open_with_preflight
    DesktopApp.run_delta_force = run_delta_force_with_preflight
    DesktopApp.run_full_flow = run_full_flow_with_preflight
    DesktopApp.run_preflight_check = run_manual_preflight


_patch_preflight_before_actions()
del _patch_preflight_before_actions


_desktop_launch = launch


def launch(*args, **kwargs):
    from .license_gate import ensure_license_tk

    if not ensure_license_tk():
        return None
    return _desktop_launch(*args, **kwargs)
