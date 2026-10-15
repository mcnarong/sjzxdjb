# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk


if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parents[1]
    BUNDLE_DIR = APP_DIR
REFERENCE_PROFILE_PATH = APP_DIR / "device_profiles" / "xiaomi_2211133c.txt"
if not REFERENCE_PROFILE_PATH.exists():
    REFERENCE_PROFILE_PATH = BUNDLE_DIR / "device_profiles" / "xiaomi_2211133c.txt"
DEFAULT_ADB_PATH = APP_DIR / "platform-tools" / "adb.exe"
if not DEFAULT_ADB_PATH.exists():
    DEFAULT_ADB_PATH = BUNDLE_DIR / "platform-tools" / "adb.exe"
CAPTURE_DIR = APP_DIR / "captures"
EXPORT_DIR = APP_DIR / "device_profiles"
DEBUG_CROP_DIR = APP_DIR / "debug_crops"

DELTA_PACKAGE = "com.tencent.tmgp.dfm"
QQ_PACKAGE = "com.tencent.mobileqq"


@dataclass(frozen=True)
class CalItem:
    item_id: str
    group: str
    profile_field: str
    title: str
    page: str
    instruction: str
    mode: str
    note: str


@dataclass
class PointRecord:
    x: int
    y: int
    width: int
    height: int
    screenshot_path: str

    @property
    def xp(self) -> float:
        return self.x / self.width if self.width else 0.0

    @property
    def yp(self) -> float:
        return self.y / self.height if self.height else 0.0


@dataclass
class StationRecord:
    point: PointRecord | None = None
    slot_box: list[float] | None = None
    box_screenshot_path: str | None = None


@dataclass
class StationDiagnostics:
    state: str
    crop_path: str
    metrics: dict[str, float] = field(default_factory=dict)


STATIONS: list[tuple[str, str]] = [
    ("tech", "技术中心"),
    ("workbench", "工作台"),
    ("med", "制药台"),
    ("armor", "防具台"),
]

POINT_ITEMS: list[CalItem] = [
    CalItem(
        "qq.avatar_tap",
        "qq",
        "avatar_tap",
        "QQ 左上角头像",
        "QQ 消息首页",
        "请把手机切到 QQ 消息首页, 然后点击左上角头像中心。",
        "point",
        "点击 QQ 左上角头像",
    ),
    CalItem(
        "qq.settings_tap",
        "qq",
        "settings_tap",
        "QQ 侧栏设置",
        "QQ 头像侧栏",
        "请先打开 QQ 左侧个人侧栏, 然后点击底部设置按钮中心。",
        "point",
        "点击个人侧栏底部设置",
    ),
    CalItem(
        "qq.account_security_tap",
        "qq",
        "account_security_tap",
        "QQ 账号与安全",
        "QQ 设置页",
        "请把手机切到 QQ 设置页, 然后点击账号与安全这一行中心。",
        "point",
        "点击设置页账号与安全",
    ),
    CalItem(
        "delta.login_qq_tap",
        "delta_force",
        "login_qq_tap",
        "三角洲 QQ 登录",
        "三角洲登录页",
        "请把手机切到三角洲登录页, 然后点击 QQ 登录按钮中心。",
        "point",
        "如果显示登录页则点击 QQ 登录",
    ),
    CalItem(
        "delta.login_agreement_tap",
        "delta_force",
        "login_agreement_tap",
        "登录协议勾选",
        "三角洲登录页",
        "请把手机切到三角洲登录页, 然后点击协议同意框中心。",
        "point",
        "勾选登录页协议同意框",
    ),
    CalItem(
        "delta.qq_authorize_first_tap",
        "delta_force",
        "qq_authorize_first_tap",
        "QQ 第一层授权",
        "QQ 第一层授权页",
        "请把手机切到 QQ 第一层授权页, 然后点击同意按钮中心。",
        "point",
        "如果显示 QQ 第一层授权则点击同意",
    ),
    CalItem(
        "delta.qq_authorize_second_tap",
        "delta_force",
        "qq_authorize_second_tap",
        "QQ 第二层授权",
        "QQ 第二层授权页",
        "请把手机切到 QQ 第二层授权页, 然后点击同意按钮中心。",
        "point",
        "如果显示 QQ 第二层授权则点击同意",
    ),
    CalItem(
        "delta.fenghuo_mode_tap",
        "delta_force",
        "fenghuo_mode_tap",
        "烽火地带",
        "三角洲模式选择页",
        "请把手机切到模式选择页, 然后点击烽火地带入口中心。",
        "point",
        "选择烽火地带",
    ),
    CalItem(
        "delta.start_game_tap",
        "delta_force",
        "start_game_tap",
        "开始游戏",
        "三角洲模式选择页",
        "请把手机切到模式选择页, 然后点击开始游戏按钮中心。",
        "point",
        "点击开始游戏",
    ),
    CalItem(
        "delta.special_office_tap",
        "delta_force",
        "special_office_tap",
        "特勤处入口",
        "三角洲大厅页",
        "请把手机切到三角洲大厅页, 然后点击底部特勤处按钮中心。",
        "point",
        "点击大厅底部特勤处",
    ),
    CalItem(
        "delta.settings_tap",
        "delta_force",
        "settings_tap",
        "大厅设置",
        "三角洲大厅页",
        "请把手机切到三角洲大厅页, 然后点击右上角设置按钮中心。",
        "point",
        "打开大厅右上角设置",
    ),
    CalItem(
        "delta.lobby_back_tap",
        "delta_force",
        "lobby_back_tap",
        "特勤处返回",
        "三角洲特勤处页",
        "请把手机切到特勤处页, 然后点击返回大厅按钮中心。",
        "point",
        "从特勤处返回大厅",
    ),
    CalItem(
        "delta.detail_back_tap",
        "delta_force",
        "detail_back_tap",
        "详情页返回",
        "三角洲制作详情页",
        "请打开任意制作详情页, 然后点击返回特勤处按钮中心。",
        "point",
        "从制作详情返回特勤处",
    ),
    CalItem(
        "delta.action_button_tap",
        "delta_force",
        "action_button_tap",
        "生产/领取按钮",
        "三角洲制作详情页",
        "请打开任意制作详情页, 然后点击底部生产或领取操作按钮中心。",
        "point",
        "点击生产按钮",
    ),
    CalItem(
        "delta.logout_tap",
        "delta_force",
        "logout_tap",
        "退出登录",
        "三角洲设置页",
        "请打开三角洲设置页, 然后点击退出登录按钮中心。",
        "point",
        "点击设置里的退出登录",
    ),
    CalItem(
        "delta.logout_confirm_tap",
        "delta_force",
        "logout_confirm_tap",
        "退出确认",
        "三角洲退出确认弹窗",
        "请把手机切到退出登录确认弹窗, 然后点击确认按钮中心。",
        "point",
        "确认退出登录",
    ),
    CalItem(
        "delta.replenish_price_tap",
        "delta_force",
        "replenish_price_tap",
        "补齐价格按钮",
        "三角洲一键补齐清单页",
        "请打开材料不足时的一键补齐清单页, 然后点击底部价格按钮中心。",
        "point",
        "点击一键补齐清单底部价格按钮",
    ),
]

STATION_ITEMS: list[CalItem] = [
    CalItem(
        f"station.{key}",
        "delta_force",
        key,
        f"{label}制作台",
        "三角洲特勤处页",
        f"请把手机切到特勤处页: 单击{label}卡片中心, 再拖框圈住完整卡片状态区域。",
        "station",
        f"{label}制作台格子",
    )
    for key, label in STATIONS
]

_ALL_ITEMS_BY_ID = {item.item_id: item for item in POINT_ITEMS + STATION_ITEMS}
CALIBRATION_FLOW_ORDER = [
    "delta.login_agreement_tap",
    "delta.login_qq_tap",
    "delta.qq_authorize_first_tap",
    "delta.qq_authorize_second_tap",
    "delta.fenghuo_mode_tap",
    "delta.start_game_tap",
    "delta.special_office_tap",
    "station.tech",
    "station.workbench",
    "station.med",
    "station.armor",
    "delta.action_button_tap",
    "delta.detail_back_tap",
    "delta.replenish_price_tap",
    "delta.lobby_back_tap",
    "delta.settings_tap",
    "delta.logout_tap",
    "delta.logout_confirm_tap",
    "qq.avatar_tap",
    "qq.settings_tap",
    "qq.account_security_tap",
]
CAL_ITEMS: list[CalItem] = [_ALL_ITEMS_BY_ID[item_id] for item_id in CALIBRATION_FLOW_ORDER]
ITEM_BY_ID = {item.item_id: item for item in CAL_ITEMS}
DELTA_EXPORT_FIELD_ORDER = [
    "login_qq_tap",
    "qq_authorize_first_tap",
    "qq_authorize_second_tap",
    "fenghuo_mode_tap",
    "start_game_tap",
    "special_office_tap",
    "lobby_back_tap",
    "detail_back_tap",
    "settings_tap",
    "logout_tap",
    "logout_confirm_tap",
    "login_agreement_tap",
    "action_button_tap",
    "replenish_price_tap",
]


class AdbError(RuntimeError):
    pass


def ensure_dirs() -> None:
    for path in (CAPTURE_DIR, EXPORT_DIR, DEBUG_CROP_DIR):
        path.mkdir(parents=True, exist_ok=True)


def locate_adb() -> str:
    env_path = os.environ.get("ADB_PATH")
    if env_path and Path(env_path).exists():
        return env_path
    if DEFAULT_ADB_PATH.exists():
        return str(DEFAULT_ADB_PATH)
    found = shutil.which("adb")
    if found:
        return found
    return str(DEFAULT_ADB_PATH)


def creation_flags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


class AdbClient:
    def __init__(self, adb_path: str, serial: str | None = None) -> None:
        self.adb_path = adb_path
        self.serial = serial or None

    def _base(self) -> list[str]:
        cmd = [self.adb_path]
        if self.serial:
            cmd.extend(["-s", self.serial])
        return cmd

    def run_text(self, args: list[str], timeout: int = 30, use_serial: bool = True) -> str:
        cmd = [self.adb_path]
        if use_serial and self.serial:
            cmd.extend(["-s", self.serial])
        cmd.extend(args)
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creation_flags(),
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "ADB command failed"
            raise AdbError(message)
        return completed.stdout.strip()

    def run_bytes(self, args: list[str], timeout: int = 30) -> bytes:
        cmd = self._base() + args
        completed = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=creation_flags(),
        )
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", "replace").strip() or "ADB command failed"
            raise AdbError(message)
        return completed.stdout

    def devices(self) -> list[str]:
        output = self.run_text(["devices"], use_serial=False)
        serials: list[str] = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        return serials

    def shell(self, *args: str, timeout: int = 30) -> str:
        return self.run_text(["shell", *args], timeout=timeout)

    def getprop(self, name: str) -> str:
        return self.shell("getprop", name).strip()

    def device_info(self) -> dict[str, Any]:
        size_text = self.shell("wm", "size")
        density_text = self.shell("wm", "density")
        width, height = parse_wm_size(size_text)
        density = parse_wm_density(density_text)
        return {
            "manufacturer": self.getprop("ro.product.manufacturer") or "",
            "model": self.getprop("ro.product.model") or "",
            "product": self.getprop("ro.product.device") or "",
            "screen_width": width,
            "screen_height": height,
            "display_width": width,
            "display_height": height,
            "density": density,
        }

    def screenshot(self, output_path: Path) -> Image.Image:
        data = self.run_bytes(["exec-out", "screencap", "-p"], timeout=30)
        if not data.startswith(b"\x89PNG"):
            data = data.replace(b"\r\r\n", b"\n").replace(b"\r\n", b"\n")
        output_path.write_bytes(data)
        with Image.open(io.BytesIO(data)) as image:
            return image.convert("RGB").copy()

    def launch(self, package: str) -> str:
        return self.shell(
            "monkey",
            "-p",
            package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
            timeout=20,
        )


def parse_wm_size(text: str) -> tuple[int, int]:
    matches = re.findall(r"(\d+)x(\d+)", text)
    if not matches:
        return 0, 0
    width, height = matches[-1]
    return int(width), int(height)


def parse_wm_density(text: str) -> int:
    matches = re.findall(r"(\d+)", text)
    return int(matches[-1]) if matches else 0


def load_reference_profile() -> dict[str, Any] | None:
    if not REFERENCE_PROFILE_PATH.exists():
        return None
    try:
        return json.loads(REFERENCE_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_key(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", value.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "calibrated_phone"


def pct(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def point_payload(point: PointRecord, note: str) -> dict[str, Any]:
    return {
        "x": int(point.x),
        "y": int(point.y),
        "note": note,
    }


def is_delta_force_yellow(pixel: tuple[int, int, int]) -> bool:
    red, green, blue = pixel
    return red > 140 and green > 110 and blue < 90 and red > blue * 1.8


def is_delta_force_timer_text(pixel: tuple[int, int, int]) -> bool:
    return pixel[0] > 145 and pixel[1] > 145 and pixel[2] > 145 and max(pixel) - min(pixel) < 60


def crop_from_percent(image: Image.Image, box: list[float]) -> Image.Image:
    width, height = image.size
    x1 = max(0, min(width - 1, round(width * box[0])))
    y1 = max(0, min(height - 1, round(height * box[1])))
    x2 = max(x1 + 1, min(width, round(width * box[2])))
    y2 = max(y1 + 1, min(height, round(height * box[3])))
    return image.crop((x1, y1, x2, y2))


def classify_station(image: Image.Image, slot_box: list[float]) -> tuple[str, dict[str, float], Image.Image]:
    crop = crop_from_percent(image.convert("RGB"), slot_box)
    crop_width, crop_height = crop.size
    pixels = crop.load()

    border_width = min(10, max(1, crop_width // 4), max(1, crop_height // 4))
    border_points: list[tuple[int, int]] = []
    for x in range(crop_width):
        for y in list(range(border_width)) + list(range(crop_height - border_width, crop_height)):
            border_points.append((x, y))
    for y in range(crop_height):
        for x in list(range(border_width)) + list(range(crop_width - border_width, crop_width)):
            border_points.append((x, y))

    yellow_border = 0.0
    if border_points:
        yellow_border = sum(1 for x, y in border_points if is_delta_force_yellow(pixels[x, y])) / len(border_points)

    top_right = crop.crop((round(crop_width * 0.78), 0, crop_width, round(crop_height * 0.25)))
    top_right_pixels = list(top_right.getdata())
    yellow_top_right = 0.0
    if top_right_pixels:
        yellow_top_right = sum(1 for pixel in top_right_pixels if is_delta_force_yellow(pixel)) / len(top_right_pixels)

    margin_x = min(30, max(1, crop_width // 5))
    margin_y = min(30, max(1, crop_height // 5))
    inner = crop.crop((margin_x, margin_y, max(margin_x + 1, crop_width - margin_x), max(margin_y + 1, crop_height - margin_y)))
    inner_pixels = list(inner.getdata())
    saturation = 0.0
    if inner_pixels:
        saturation = sum(max(pixel) - min(pixel) for pixel in inner_pixels) / len(inner_pixels)

    timer_region = crop.crop(
        (
            round(crop_width * 0.02),
            round(crop_height * 0.56),
            round(crop_width * 0.72),
            round(crop_height * 0.86),
        )
    )
    timer_pixels = list(timer_region.getdata())
    timer_text = 0.0
    if timer_pixels:
        timer_text = sum(1 for pixel in timer_pixels if is_delta_force_timer_text(pixel)) / len(timer_pixels)

    if saturation >= 8.0 and timer_text >= 0.012:
        state = "busy"
    elif yellow_border >= 0.03 or yellow_top_right >= 0.01:
        state = "ready"
    else:
        state = "empty"

    metrics = {
        "yellow_border": round(yellow_border, 5),
        "yellow_top_right": round(yellow_top_right, 5),
        "saturation": round(saturation, 5),
        "timer_text": round(timer_text, 5),
    }
    return state, metrics, crop


def state_label(state: str) -> str:
    labels = {
        "ready": "可领取",
        "busy": "生产中",
        "empty": "空闲",
    }
    return labels.get(state, state)


class CalibratorApp:
    def __init__(self, root: tk.Tk, initial_serial: str | None = None) -> None:
        ensure_dirs()
        self.root = root
        self.root.title("DeltaForce Calibrator")
        self.root.geometry("1440x900")
        self.root.minsize(1180, 760)

        self.reference = load_reference_profile()
        self.points: dict[str, PointRecord] = {}
        self.stations: dict[str, StationRecord] = {}
        self.station_diagnostics: dict[str, StationDiagnostics] = {}
        self.device_info: dict[str, Any] | None = None

        self.current_image: Image.Image | None = None
        self.current_image_path: Path | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.image_scale = 1.0
        self.image_offset = (0, 0)
        self.drag_start_image: tuple[int, int] | None = None
        self.drag_current_image: tuple[int, int] | None = None

        self.adb_path_var = tk.StringVar(value=locate_adb())
        self.serial_var = tk.StringVar(value=initial_serial or "")
        self.device_key_var = tk.StringVar(value="calibrated_phone")
        self.profile_label_var = tk.StringVar(value="新手机校准坐标")
        self.status_var = tk.StringVar(value="选择设备后截图。标记只画在电脑端, 不会写进识别截图。")
        self.instruction_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="")
        self.auto_screenshot_var = tk.BooleanVar(value=True)
        self._last_selected_item_id: str | None = None
        self._initializing_selection = True

        self._configure_style()
        self._build_ui()
        self._populate_items()
        self.refresh_devices()

    def _configure_style(self) -> None:
        self.colors = {
            "bg": "#edf1f6",
            "panel": "#ffffff",
            "panel_alt": "#f8fafc",
            "border": "#cfd6e2",
            "text": "#172033",
            "muted": "#667085",
            "header": "#111827",
            "header_text": "#f8fafc",
            "canvas": "#121821",
            "accent": "#2563eb",
            "accent_active": "#1d4ed8",
            "success": "#047857",
            "warning": "#b45309",
        }
        self.root.configure(bg=self.colors["bg"])
        self.root.option_add("*Font", "{Microsoft YaHei UI} 9")

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=("Microsoft YaHei UI", 9), foreground=self.colors["text"])
        style.configure("TFrame", background=self.colors["panel"])
        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure("CanvasPanel.TFrame", background=self.colors["canvas"])
        style.configure("Subtle.TFrame", background=self.colors["panel_alt"])
        style.configure("Status.TLabel", background=self.colors["panel"], foreground=self.colors["muted"], padding=(10, 6))
        style.configure("Muted.TLabel", background=self.colors["panel"], foreground=self.colors["muted"])
        style.configure("Panel.TLabel", background=self.colors["panel"], foreground=self.colors["text"])
        style.configure("Title.TLabel", background=self.colors["header"], foreground=self.colors["header_text"], font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Subtitle.TLabel", background=self.colors["header"], foreground="#cbd5e1", font=("Microsoft YaHei UI", 9))

        style.configure("Card.TLabelframe", background=self.colors["panel"], bordercolor=self.colors["border"], relief="solid")
        style.configure("Card.TLabelframe.Label", background=self.colors["panel"], foreground=self.colors["text"], font=("Microsoft YaHei UI", 10, "bold"))

        style.configure("TEntry", fieldbackground="#ffffff", bordercolor=self.colors["border"], lightcolor=self.colors["border"], darkcolor=self.colors["border"], padding=4)
        style.configure("TCombobox", fieldbackground="#ffffff", bordercolor=self.colors["border"], arrowsize=14, padding=4)
        style.configure("TCheckbutton", background=self.colors["panel"], foreground=self.colors["text"])
        style.configure("TButton", padding=(10, 6), bordercolor=self.colors["border"], focusthickness=1, focuscolor=self.colors["accent"])
        style.configure("Primary.TButton", padding=(12, 7), background=self.colors["accent"], foreground="#ffffff", bordercolor=self.colors["accent"])
        style.map("Primary.TButton", background=[("active", self.colors["accent_active"]), ("pressed", "#1e40af")], foreground=[("disabled", "#cbd5e1")])
        style.configure(
            "Save.Horizontal.TProgressbar",
            background=self.colors["accent"],
            troughcolor="#e5e7eb",
            bordercolor="#e5e7eb",
            lightcolor=self.colors["accent"],
            darkcolor=self.colors["accent"],
        )

        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground=self.colors["text"],
            rowheight=30,
            bordercolor=self.colors["border"],
            font=("Microsoft YaHei UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#eef2f7",
            foreground="#344054",
            relief="flat",
            font=("Microsoft YaHei UI", 9, "bold"),
            padding=(6, 7),
        )
        style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", "#111827")])

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame")
        outer.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(outer, bg=self.colors["header"], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        header_inner = tk.Frame(header, bg=self.colors["header"])
        header_inner.pack(fill=tk.BOTH, expand=True, padx=18, pady=11)
        ttk.Label(header_inner, text="DeltaForce Calibrator", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header_inner,
            text="三角洲/QQ 坐标校准  |  原始截图识别, 标记仅显示在电脑端",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(3, 0))

        body = ttk.Frame(outer, style="App.TFrame", padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body, width=540, style="Panel.TFrame", padding=10)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        right = ttk.Frame(body, style="CanvasPanel.TFrame", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))

        adb_frame = ttk.LabelFrame(left, text="设备连接", style="Card.TLabelframe", padding=10)
        adb_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(adb_frame, text="ADB", style="Panel.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=5)
        ttk.Entry(adb_frame, textvariable=self.adb_path_var, width=42).grid(row=0, column=1, sticky=tk.EW, pady=5)
        ttk.Button(adb_frame, text="浏览", command=self.browse_adb).grid(row=0, column=2, padx=(8, 0), pady=5)

        ttk.Label(adb_frame, text="设备", style="Panel.TLabel").grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=5)
        self.serial_combo = ttk.Combobox(adb_frame, textvariable=self.serial_var, width=28, state="readonly")
        self.serial_combo.grid(row=1, column=1, sticky=tk.EW, pady=5)
        ttk.Button(adb_frame, text="刷新", command=self.refresh_devices).grid(row=1, column=2, padx=(8, 0), pady=5)
        adb_frame.columnconfigure(1, weight=1)

        actions = ttk.Frame(adb_frame)
        actions.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=(8, 0))
        ttk.Button(actions, text="启动 QQ", command=lambda: self.launch_app(QQ_PACKAGE)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions, text="启动三角洲", command=lambda: self.launch_app(DELTA_PACKAGE)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions, text="截图", style="Primary.TButton", command=self.take_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(actions, text="打开图片", command=self.open_local_image).pack(side=tk.LEFT)

        profile_frame = ttk.LabelFrame(left, text="导出 Profile", style="Card.TLabelframe", padding=10)
        profile_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(profile_frame, text="device_key", style="Panel.TLabel").grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=5)
        ttk.Entry(profile_frame, textvariable=self.device_key_var).grid(row=0, column=1, sticky=tk.EW, pady=5)
        ttk.Label(profile_frame, text="label", style="Panel.TLabel").grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=5)
        ttk.Entry(profile_frame, textvariable=self.profile_label_var).grid(row=1, column=1, sticky=tk.EW, pady=5)
        ttk.Button(profile_frame, text="保存完整坐标 txt", style="Primary.TButton", command=self.save_profile).grid(
            row=2, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0)
        )
        profile_frame.columnconfigure(1, weight=1)

        item_frame = ttk.LabelFrame(left, text="校准项", style="Card.TLabelframe", padding=10)
        item_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        item_buttons = ttk.Frame(item_frame)
        item_buttons.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(item_buttons, text="清除当前项坐标", command=self.clear_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(item_buttons, text="下一步", style="Primary.TButton", command=self.go_next_item).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(item_buttons, text="状态诊断", command=self.diagnose_selected_station).pack(side=tk.LEFT)
        ttk.Checkbutton(
            item_buttons,
            text="切换校准项自动截图",
            variable=self.auto_screenshot_var,
        ).pack(side=tk.RIGHT)

        tree_wrap = ttk.Frame(item_frame)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_wrap,
            columns=("done", "group", "page", "title", "mode"),
            show="headings",
            height=20,
            selectmode="browse",
        )
        tree_y = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_y.set)
        self.tree.heading("done", text="状态")
        self.tree.heading("group", text="模块")
        self.tree.heading("page", text="页面")
        self.tree.heading("title", text="点位")
        self.tree.heading("mode", text="方式")
        self.tree.column("done", width=48, minwidth=48, anchor=tk.CENTER, stretch=False)
        self.tree.column("group", width=62, minwidth=62, anchor=tk.CENTER, stretch=False)
        self.tree.column("page", width=142, minwidth=120, anchor=tk.W, stretch=False)
        self.tree.column("title", width=170, minwidth=130, anchor=tk.W, stretch=True)
        self.tree.column("mode", width=58, minwidth=58, anchor=tk.CENTER, stretch=False)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        tree_y.grid(row=0, column=1, sticky=tk.NS)
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        self.tree.tag_configure("done", foreground=self.colors["success"])
        self.tree.tag_configure("pending", foreground="#475467")
        self.tree.tag_configure("odd", background="#fbfdff")

        info_frame = ttk.LabelFrame(left, text="当前提示", style="Card.TLabelframe", padding=10)
        info_frame.pack(fill=tk.X)
        ttk.Label(info_frame, textvariable=self.instruction_var, wraplength=540, justify=tk.LEFT, style="Panel.TLabel").pack(
            fill=tk.X
        )
        ttk.Label(info_frame, textvariable=self.detail_var, wraplength=540, justify=tk.LEFT, style="Muted.TLabel").pack(
            fill=tk.X, pady=(8, 0)
        )

        canvas_header = tk.Frame(right, bg=self.colors["canvas"], height=38)
        canvas_header.pack(fill=tk.X)
        canvas_header.pack_propagate(False)
        tk.Label(
            canvas_header,
            text="截图工作区",
            bg=self.colors["canvas"],
            fg="#f8fafc",
            font=("Microsoft YaHei UI", 11, "bold"),
        ).pack(side=tk.LEFT, padx=4, pady=8)
        tk.Label(
            canvas_header,
            text="单击记录点位, 拖拽记录制作台识别框",
            bg=self.colors["canvas"],
            fg="#94a3b8",
            font=("Microsoft YaHei UI", 9),
        ).pack(side=tk.LEFT, padx=(14, 0), pady=9)

        self.canvas = tk.Canvas(right, bg=self.colors["canvas"], highlightthickness=1, highlightbackground="#334155")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.redraw_canvas())
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        ttk.Label(right, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(fill=tk.X, pady=(8, 0))

    def _populate_items(self) -> None:
        for index, item in enumerate(CAL_ITEMS):
            self.tree.insert(
                "",
                tk.END,
                iid=item.item_id,
                values=(self.done_text(item), self.group_label(item.group), item.page, item.title, self.mode_label(item.mode)),
                tags=self.item_tags(item, index),
            )
        if CAL_ITEMS:
            self.tree.selection_set(CAL_ITEMS[0].item_id)
            self._last_selected_item_id = CAL_ITEMS[0].item_id
            self.update_instruction()
        self._initializing_selection = False

    def group_label(self, group: str) -> str:
        return "QQ" if group == "qq" else "三角洲"

    def mode_label(self, mode: str) -> str:
        return "点选" if mode == "point" else "点+框"

    def done_text(self, item: CalItem) -> str:
        if item.mode == "point":
            return "完成" if item.item_id in self.points else "待标"
        record = self.stations.get(item.profile_field)
        return "完成" if record and record.point and record.slot_box else "待标"

    def item_tags(self, item: CalItem, index: int | None = None) -> tuple[str, ...]:
        tags = ["done" if self.done_text(item) == "完成" else "pending"]
        if index is not None and index % 2:
            tags.append("odd")
        return tuple(tags)

    def selected_item(self) -> CalItem | None:
        selected = self.tree.selection()
        if not selected:
            return None
        return ITEM_BY_ID.get(selected[0])

    def on_item_select(self, _event: tk.Event | None = None) -> None:
        item = self.selected_item()
        if not item:
            return
        previous = self._last_selected_item_id
        self._last_selected_item_id = item.item_id
        self.update_instruction()
        if self._initializing_selection or previous == item.item_id:
            return
        if self.auto_screenshot_var.get():
            if self.serial_var.get().strip():
                self.root.after(120, self.take_screenshot)
            else:
                self.status_var.set("已切换校准项。自动截图需要先刷新并选择 ADB 设备。")

    def go_next_item(self) -> None:
        item_ids = [item.item_id for item in CAL_ITEMS]
        selected = self.tree.selection()
        start = item_ids.index(selected[0]) if selected and selected[0] in item_ids else -1

        target_id: str | None = None
        for offset in range(1, len(item_ids) + 1):
            candidate_id = item_ids[(start + offset) % len(item_ids)]
            candidate = ITEM_BY_ID[candidate_id]
            if self.done_text(candidate) != "完成":
                target_id = candidate_id
                break
        if target_id is None:
            target_id = item_ids[(start + 1) % len(item_ids)]

        self.tree.selection_set(target_id)
        self.tree.focus(target_id)
        self.tree.see(target_id)

    def selected_adb(self) -> AdbClient:
        adb_path = self.adb_path_var.get().strip()
        if not Path(adb_path).exists() and not shutil.which(adb_path):
            raise AdbError(f"找不到 adb: {adb_path}")
        serial = self.serial_var.get().strip()
        return AdbClient(adb_path, serial or None)

    def browse_adb(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 adb.exe",
            filetypes=[("adb.exe", "adb.exe"), ("All files", "*.*")],
            initialdir=str(DEFAULT_ADB_PATH.parent if DEFAULT_ADB_PATH.parent.exists() else APP_DIR),
        )
        if path:
            self.adb_path_var.set(path)

    def run_background(self, message: str, worker, done) -> None:
        self.status_var.set(message)

        def job() -> None:
            try:
                result = worker()
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda exc=exc: self.show_error(exc))
                return
            self.root.after(0, lambda result=result: done(result))

        threading.Thread(target=job, daemon=True).start()

    def show_error(self, exc: Exception) -> None:
        self.status_var.set(f"失败: {exc}")
        messagebox.showerror("操作失败", str(exc))

    def refresh_devices(self) -> None:
        def worker() -> tuple[list[str], dict[str, Any] | None]:
            adb = AdbClient(self.adb_path_var.get().strip())
            serials = adb.devices()
            info = None
            if serials:
                serial = self.serial_var.get().strip() or serials[0]
                info = AdbClient(self.adb_path_var.get().strip(), serial).device_info()
            return serials, info

        def done(result: tuple[list[str], dict[str, Any] | None]) -> None:
            serials, info = result
            self.serial_combo["values"] = serials
            if serials and self.serial_var.get() not in serials:
                self.serial_var.set(serials[0])
            self.device_info = info
            if info:
                key = safe_key(f"{info.get('manufacturer', '')}_{info.get('model', '')}")
                if self.device_key_var.get() == "calibrated_phone":
                    self.device_key_var.set(key)
                self.profile_label_var.set(f"{info.get('manufacturer', '')} {info.get('model', '')} 校准坐标".strip())
                self.status_var.set(
                    f"已连接: {self.serial_var.get()}  {info.get('model', '')}  {info.get('screen_width')}x{info.get('screen_height')}"
                )
            else:
                self.status_var.set("未发现 ADB device 状态的设备。")

        self.run_background("正在刷新设备...", worker, done)

    def launch_app(self, package: str) -> None:
        def worker() -> str:
            return self.selected_adb().launch(package)

        def done(_result: str) -> None:
            name = "QQ" if package == QQ_PACKAGE else "三角洲"
            self.status_var.set(f"已发送启动 {name} 命令。请切到校准项要求的页面后截图。")

        self.run_background("正在启动应用...", worker, done)

    def take_screenshot(self) -> None:
        def worker() -> tuple[Path, Image.Image]:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            item = self.selected_item()
            suffix = item.item_id.replace(".", "_") if item else "screen"
            path = CAPTURE_DIR / f"{timestamp}_{suffix}.png"
            image = self.selected_adb().screenshot(path)
            return path, image

        def done(result: tuple[Path, Image.Image]) -> None:
            path, image = result
            self.current_image_path = path
            self.current_image = image
            self.status_var.set(f"截图完成: {path}  尺寸 {image.width}x{image.height}")
            self.redraw_canvas()
            self.update_instruction()

        self.run_background("正在截图...", worker, done)

    def open_local_image(self) -> None:
        path_text = filedialog.askopenfilename(
            title="打开本地截图",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp"), ("All files", "*.*")],
            initialdir=str(CAPTURE_DIR),
        )
        if not path_text:
            return
        path = Path(path_text)
        try:
            with Image.open(path) as image:
                self.current_image = image.convert("RGB").copy()
            self.current_image_path = path
            self.status_var.set(f"已打开图片: {path}  尺寸 {self.current_image.width}x{self.current_image.height}")
            self.redraw_canvas()
            self.update_instruction()
        except Exception as exc:  # noqa: BLE001
            self.show_error(exc)

    def update_instruction(self) -> None:
        item = self.selected_item()
        if not item:
            self.instruction_var.set("")
            self.detail_var.set("")
            return
        if item.mode == "station":
            extra = "操作: 单击设置 slot_xp/slot_yp; 按住左键拖框设置 slot_box。识别只使用原始截图, 不使用覆盖标记。"
        else:
            extra = "操作: 在截图上单击目标中心。"
        self.instruction_var.set(f"{item.page}\n{item.instruction}\n{extra}")
        self.detail_var.set(self.record_summary(item))

    def record_summary(self, item: CalItem) -> str:
        if item.mode == "point":
            record = self.points.get(item.item_id)
            if not record:
                return "未记录。"
            return f"x={record.x}, y={record.y}, xp={record.xp:.4f}, yp={record.yp:.4f}"

        record = self.stations.get(item.profile_field)
        if not record:
            return "未记录。需要单击中心并拖框。"
        lines: list[str] = []
        if record.point:
            lines.append(f"slot_xp={record.point.xp:.4f}, slot_yp={record.point.yp:.4f}")
        else:
            lines.append("未记录中心点。")
        if record.slot_box:
            lines.append("slot_box=" + ", ".join(f"{value:.4f}" for value in record.slot_box))
            diag = self.station_diagnostics.get(item.profile_field)
            if diag:
                metrics = ", ".join(f"{key}={value}" for key, value in diag.metrics.items())
                lines.append(f"诊断={state_label(diag.state)}; {metrics}")
                lines.append(f"裁剪图={diag.crop_path}")
        else:
            lines.append("未记录 slot_box。")
        return "\n".join(lines)

    def clear_selected(self) -> None:
        item = self.selected_item()
        if not item:
            return
        if item.mode == "point":
            self.points.pop(item.item_id, None)
        else:
            self.stations.pop(item.profile_field, None)
            self.station_diagnostics.pop(item.profile_field, None)
        self.refresh_item_row(item)
        self.update_instruction()
        self.redraw_canvas()
        self.status_var.set(f"已清除当前项坐标: {item.title}")

    def image_to_canvas(self, x: int, y: int) -> tuple[float, float]:
        ox, oy = self.image_offset
        return ox + x * self.image_scale, oy + y * self.image_scale

    def canvas_to_image(self, x: int, y: int) -> tuple[int, int] | None:
        if not self.current_image:
            return None
        ox, oy = self.image_offset
        ix = round((x - ox) / self.image_scale)
        iy = round((y - oy) / self.image_scale)
        if ix < 0 or iy < 0 or ix >= self.current_image.width or iy >= self.current_image.height:
            return None
        return ix, iy

    def current_point_record(self, x: int, y: int) -> PointRecord:
        if not self.current_image:
            raise RuntimeError("还没有截图。")
        return PointRecord(
            x=x,
            y=y,
            width=self.current_image.width,
            height=self.current_image.height,
            screenshot_path=str(self.current_image_path or ""),
        )

    def on_canvas_press(self, event: tk.Event) -> None:
        if not self.current_image:
            self.status_var.set("请先截图或打开图片。")
            return
        point = self.canvas_to_image(event.x, event.y)
        if point is None:
            return
        self.drag_start_image = point
        self.drag_current_image = point

    def on_canvas_drag(self, event: tk.Event) -> None:
        item = self.selected_item()
        if not item or item.mode != "station" or not self.drag_start_image:
            return
        point = self.canvas_to_image(event.x, event.y)
        if point is None:
            return
        self.drag_current_image = point
        self.redraw_canvas()

    def on_canvas_release(self, event: tk.Event) -> None:
        item = self.selected_item()
        if not item or not self.current_image or not self.drag_start_image:
            return
        point = self.canvas_to_image(event.x, event.y)
        if point is None:
            self.drag_start_image = None
            self.drag_current_image = None
            self.redraw_canvas()
            return

        sx, sy = self.drag_start_image
        ex, ey = point
        moved = abs(ex - sx) + abs(ey - sy)
        if item.mode == "station" and moved >= 12:
            self.record_station_box(item.profile_field, sx, sy, ex, ey)
        else:
            record = self.current_point_record(ex, ey)
            if item.mode == "point":
                self.points[item.item_id] = record
            else:
                station = self.stations.setdefault(item.profile_field, StationRecord())
                station.point = record
            self.status_var.set(f"已记录 {item.title}: x={ex}, y={ey}, xp={record.xp:.4f}, yp={record.yp:.4f}")

        self.drag_start_image = None
        self.drag_current_image = None
        self.refresh_item_row(item)
        self.update_instruction()
        self.redraw_canvas()

    def record_station_box(self, station_key: str, sx: int, sy: int, ex: int, ey: int) -> None:
        if not self.current_image:
            return
        width, height = self.current_image.size
        x1, x2 = sorted((sx, ex))
        y1, y2 = sorted((sy, ey))
        if x2 - x1 < 20 or y2 - y1 < 20:
            self.status_var.set("框太小, 请拖框圈住完整制作台卡片状态区域。")
            return
        box = [pct(x1 / width), pct(y1 / height), pct(x2 / width), pct(y2 / height)]
        station = self.stations.setdefault(station_key, StationRecord())
        station.slot_box = box
        station.box_screenshot_path = str(self.current_image_path or "")
        self.run_station_diagnostics(station_key)

    def run_station_diagnostics(self, station_key: str) -> None:
        if not self.current_image:
            return
        station = self.stations.get(station_key)
        if not station or not station.slot_box:
            return
        state, metrics, crop = classify_station(self.current_image, station.slot_box)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        crop_path = DEBUG_CROP_DIR / f"{timestamp}_{station_key}_{state}.png"
        crop.save(crop_path)
        self.station_diagnostics[station_key] = StationDiagnostics(
            state=state,
            crop_path=str(crop_path),
            metrics=metrics,
        )
        self.status_var.set(f"{station_key} 框选完成, 当前截图诊断: {state_label(state)}。裁剪图已保存。")

    def diagnose_selected_station(self) -> None:
        item = self.selected_item()
        if not item or item.mode != "station":
            self.status_var.set("状态诊断只用于制作台条目。")
            return
        station = self.stations.get(item.profile_field)
        if not station or not station.slot_box:
            self.status_var.set("请先为该制作台拖框设置 slot_box。")
            return
        self.run_station_diagnostics(item.profile_field)
        self.update_instruction()
        self.redraw_canvas()

    def refresh_item_row(self, item: CalItem) -> None:
        index = CAL_ITEMS.index(item)
        self.tree.item(
            item.item_id,
            values=(self.done_text(item), self.group_label(item.group), item.page, item.title, self.mode_label(item.mode)),
            tags=self.item_tags(item, index),
        )

    def redraw_canvas(self) -> None:
        self.canvas.delete("all")
        if not self.current_image:
            width = max(1, self.canvas.winfo_width())
            height = max(1, self.canvas.winfo_height())
            box_w = min(520, max(320, width - 120))
            box_h = 170
            x1 = (width - box_w) // 2
            y1 = max(60, (height - box_h) // 2)
            x2 = x1 + box_w
            y2 = y1 + box_h
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#334155", fill="#182231", width=1)
            self.canvas.create_text(
                (x1 + x2) // 2,
                y1 + 46,
                fill="#f8fafc",
                text="等待截图",
                font=("Microsoft YaHei UI", 18, "bold"),
            )
            self.canvas.create_text(
                (x1 + x2) // 2,
                y1 + 86,
                fill="#cbd5e1",
                text="连接手机后点击左侧“截图”, 或打开本地图片开始校准。",
                font=("Microsoft YaHei UI", 10),
            )
            self.canvas.create_text(
                (x1 + x2) // 2,
                y1 + 120,
                fill="#94a3b8",
                text="覆盖标记只显示在这里, 不会写入识别截图。",
                font=("Microsoft YaHei UI", 9),
            )
            return

        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        margin = 12
        scale = min((canvas_width - margin * 2) / self.current_image.width, (canvas_height - margin * 2) / self.current_image.height)
        scale = max(0.05, min(scale, 1.5))
        display_width = max(1, round(self.current_image.width * scale))
        display_height = max(1, round(self.current_image.height * scale))
        offset_x = (canvas_width - display_width) // 2
        offset_y = (canvas_height - display_height) // 2
        self.image_scale = scale
        self.image_offset = (offset_x, offset_y)

        resized = self.current_image.resize((display_width, display_height), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        self.canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=self.photo)
        self.canvas.create_rectangle(offset_x, offset_y, offset_x + display_width, offset_y + display_height, outline="#4b5563")
        self.draw_overlays()

    def draw_overlays(self) -> None:
        if not self.current_image:
            return
        current_size = self.current_image.size
        for item in CAL_ITEMS:
            if item.mode == "point":
                record = self.points.get(item.item_id)
                if record and (record.width, record.height) == current_size:
                    self.draw_point(record.x, record.y, item.title, "#5eead4")
            else:
                station = self.stations.get(item.profile_field)
                if station and station.point and (station.point.width, station.point.height) == current_size:
                    self.draw_point(station.point.x, station.point.y, item.title, "#facc15")
                if station and station.slot_box:
                    self.draw_box(station.slot_box, item.title, "#facc15")

        item = self.selected_item()
        if item and item.mode == "station" and self.drag_start_image and self.drag_current_image:
            self.draw_drag_preview(self.drag_start_image, self.drag_current_image)

    def draw_point(self, x: int, y: int, label: str, color: str) -> None:
        cx, cy = self.image_to_canvas(x, y)
        self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline=color, width=2)
        self.canvas.create_line(cx - 12, cy, cx + 12, cy, fill=color, width=2)
        self.canvas.create_line(cx, cy - 12, cx, cy + 12, fill=color, width=2)
        self.canvas.create_text(cx + 8, cy - 8, anchor=tk.SW, fill=color, text=label)

    def draw_box(self, box: list[float], label: str, color: str) -> None:
        if not self.current_image:
            return
        width, height = self.current_image.size
        x1, y1 = self.image_to_canvas(round(width * box[0]), round(height * box[1]))
        x2, y2 = self.image_to_canvas(round(width * box[2]), round(height * box[3]))
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
        self.canvas.create_text(x1 + 4, y1 + 4, anchor=tk.NW, fill=color, text=label)

    def draw_drag_preview(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        x1, y1 = self.image_to_canvas(*start)
        x2, y2 = self.image_to_canvas(*end)
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#38bdf8", dash=(4, 3), width=2)

    def reference_note(self, group: str, field_name: str, fallback: str) -> str:
        if not self.reference:
            return fallback
        profile_key = "qq_profiles" if group == "qq" else "delta_force_profiles"
        try:
            profile = self.reference[profile_key][0]
            value = profile.get(field_name)
            if isinstance(value, dict) and value.get("note"):
                return str(value["note"])
        except Exception:
            pass
        return fallback

    def reference_station(self, key: str) -> dict[str, Any]:
        if not self.reference:
            return {}
        try:
            stations = self.reference["delta_force_profiles"][0]["stations"]
            for station in stations:
                if station.get("key") == key:
                    return station
        except Exception:
            pass
        return {}

    def screen_for(self, group: str) -> dict[str, Any]:
        records: list[PointRecord] = []
        for item in CAL_ITEMS:
            if item.group != group:
                continue
            if item.mode == "point" and item.item_id in self.points:
                records.append(self.points[item.item_id])
            if item.mode == "station":
                station = self.stations.get(item.profile_field)
                if station and station.point:
                    records.append(station.point)
        if records:
            width, height = records[0].width, records[0].height
        elif self.device_info:
            width, height = int(self.device_info.get("screen_width") or 0), int(self.device_info.get("screen_height") or 0)
            if group == "delta_force" and width < height:
                width, height = height, width
        else:
            width, height = (2400, 1080) if group == "delta_force" else (1080, 2400)
        return {
            "orientation": "landscape" if group == "delta_force" else "portrait",
            "dry_run_width": width,
            "dry_run_height": height,
        }

    def validate_before_save(self) -> list[str]:
        missing: list[str] = []
        if not self.device_info:
            missing.append("设备信息, 请先刷新 ADB 设备")
        for item in CAL_ITEMS:
            if item.mode == "point":
                if item.item_id not in self.points:
                    missing.append(f"{item.page} - {item.title}")
            else:
                station = self.stations.get(item.profile_field)
                if not station or not station.point:
                    missing.append(f"{item.page} - {item.title} 中心点")
                if not station or not station.slot_box:
                    missing.append(f"{item.page} - {item.title} slot_box")
        return missing

    def save_profile(self) -> None:
        missing = self.validate_before_save()
        if missing:
            preview = "\n".join(missing[:16])
            if len(missing) > 16:
                preview += f"\n... 还有 {len(missing) - 16} 项"
            messagebox.showerror("不能保存", "还有校准项未完成:\n\n" + preview)
            return

        key = safe_key(self.device_key_var.get())
        label = self.profile_label_var.get().strip() or f"{key} 校准坐标"
        assert self.device_info is not None

        qq_profile: dict[str, Any] = {
            "key": f"{key}_qq",
            "label": f"{label} QQ 坐标",
            "screen": self.screen_for("qq"),
        }
        for item in [entry for entry in POINT_ITEMS if entry.group == "qq"]:
            record = self.points[item.item_id]
            qq_profile[item.profile_field] = point_payload(
                record,
                self.reference_note("qq", item.profile_field, item.note),
            )

        delta_profile: dict[str, Any] = {
            "key": f"{key}_delta",
            "label": f"{label} 三角洲坐标",
            "screen": self.screen_for("delta_force"),
            "stations": [],
        }
        for station_key, station_label_text in STATIONS:
            record = self.stations[station_key]
            assert record.point is not None and record.slot_box is not None
            ref = self.reference_station(station_key)
            station_payload = {
                "key": station_key,
                "label": station_label_text,
                "slot_xp": pct(record.point.xp),
                "slot_yp": pct(record.point.yp),
                "open_xp": pct(float(ref.get("open_xp", record.point.xp))),
                "open_yp": pct(float(ref.get("open_yp", record.point.yp))),
                "slot_box": [pct(value) for value in record.slot_box],
            }
            delta_profile["stations"].append(station_payload)

        delta_items_by_field = {
            entry.profile_field: entry
            for entry in POINT_ITEMS
            if entry.group == "delta_force"
        }
        for field_name in DELTA_EXPORT_FIELD_ORDER:
            item = delta_items_by_field[field_name]
            record = self.points[item.item_id]
            delta_profile[item.profile_field] = point_payload(
                record,
                self.reference_note("delta_force", item.profile_field, item.note),
            )

        profile = {
            "version": 1,
            "device_key": key,
            "label": label,
            "match": self.device_info,
            "qq_profiles": [qq_profile],
            "delta_force_profiles": [delta_profile],
        }

        output_path = EXPORT_DIR / f"{key}.txt"
        self.start_save_progress(output_path, profile)

    def start_save_progress(self, output_path: Path, profile: dict[str, Any]) -> None:
        progress_window = tk.Toplevel(self.root)
        progress_window.title("正在保存")
        progress_window.resizable(False, False)
        progress_window.configure(bg="#ffffff")
        progress_window.transient(self.root)

        percent_var = tk.StringVar(value="0%")
        arrow_var = tk.StringVar(value=">>>>>>>>>>")
        message_var = tk.StringVar(value="准备保存坐标")

        frame = tk.Frame(progress_window, bg="#ffffff", padx=34, pady=24)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            frame,
            textvariable=percent_var,
            bg="#ffffff",
            fg="#0b1020",
            font=("Segoe UI", 34, "bold"),
        ).pack(anchor=tk.W)
        tk.Label(
            frame,
            textvariable=arrow_var,
            bg="#ffffff",
            fg="#1f2937",
            font=("Consolas", 17, "bold"),
        ).pack(anchor=tk.W, pady=(0, 12))
        bar = ttk.Progressbar(
            frame,
            orient=tk.HORIZONTAL,
            length=360,
            mode="determinate",
            maximum=100,
            style="Save.Horizontal.TProgressbar",
        )
        bar.pack(fill=tk.X)
        ttk.Label(frame, textvariable=message_var, style="Muted.TLabel").pack(anchor=tk.W, pady=(12, 0))

        progress_window.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - progress_window.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - progress_window.winfo_height()) // 2)
        progress_window.geometry(f"+{x}+{y}")
        try:
            progress_window.grab_set()
        except tk.TclError:
            pass

        stages = [
            (8, "校验校准项"),
            (24, "整理 QQ 坐标"),
            (42, "整理三角洲坐标"),
            (62, "生成 profile 数据"),
            (80, "写入坐标文件"),
            (100, "打开导出文件夹"),
        ]
        wrote = {"done": False}

        def advance(index: int = 0) -> None:
            if index >= len(stages):
                try:
                    progress_window.destroy()
                except tk.TclError:
                    pass
                self.status_var.set("已保存坐标, 并打开导出文件夹。")
                self.open_output_folder(output_path)
                return

            percent, message = stages[index]
            percent_var.set(f"{percent}%")
            arrow_count = max(3, min(12, percent // 8))
            arrow_var.set(">" * arrow_count)
            message_var.set(message)
            bar["value"] = percent

            if percent >= 80 and not wrote["done"]:
                try:
                    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    wrote["done"] = True
                except Exception as exc:  # noqa: BLE001
                    try:
                        progress_window.destroy()
                    except tk.TclError:
                        pass
                    self.show_error(exc)
                    return

            self.root.after(180, lambda: advance(index + 1))

        self.root.after(80, advance)

    def open_output_folder(self, output_path: Path) -> None:
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", f"/select,{str(output_path)}"], creationflags=creation_flags())
            else:
                os.startfile(str(output_path.parent))  # type: ignore[attr-defined]
        except Exception:
            try:
                os.startfile(str(output_path.parent))  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                self.status_var.set(f"已保存, 但打开文件夹失败: {exc}")


def main() -> None:
    ensure_dirs()
    root = tk.Tk()
    CalibratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
