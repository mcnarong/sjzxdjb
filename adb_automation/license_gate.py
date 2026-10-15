from __future__ import annotations

import ctypes
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
import tkinter.font as tkfont


PRODUCT_ID = "ADBAutomation"
LICENSE_FILENAME = "activation.dat"
CODE_LENGTH = 10
RANDOM_PART_LENGTH = 4
SIGNATURE_PART_LENGTH = CODE_LENGTH - RANDOM_PART_LENGTH
MACHINE_CODE_LENGTH = 20
CONTACT_TEXT = "授权码获取方式 QQ：2337767459，微信：z2337767459"
REVOCATION_URLS = (
    "https://gitee.com/narong258269/nanrong/raw/master/revoked.json",
    "https://gitee.com/narong258269/nanrong/raw/main/revoked.json",
    "https://gitee.com/api/v5/repos/narong258269/nanrong/contents/revoked.json?ref=master",
    "https://gitee.com/api/v5/repos/narong258269/nanrong/contents/revoked.json?ref=main",
    "https://raw.githubusercontent.com/mcnarong/auto/main/revoked.json",
    "https://api.github.com/repos/mcnarong/auto/contents/revoked.json?ref=main",
)
REVOCATION_TIMEOUT_SECONDS = 8
REVOCATION_REQUIRED = False
REVOCATION_CACHE_FILENAME = "revocation_cache.dat"

# Omit easily confused characters while keeping the code alphanumeric.
CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_NORMALIZE_RE = re.compile(r"[^A-Z0-9]+")
_SECRET_PARTS = (
    "ADB",
    "Automation",
    "offline",
    "license",
    "2026",
    "2337767459",
    "z2337767459",
)
_FONT_CANDIDATES = ("Microsoft YaHei UI", "Microsoft YaHei", "SimSun", "Arial")


class LicenseError(ValueError):
    pass


class RevocationError(RuntimeError):
    pass


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def license_path() -> Path:
    return runtime_root() / LICENSE_FILENAME


def _secret(suffix: str) -> bytes:
    text = "|".join(_SECRET_PARTS) + "|" + suffix
    return hashlib.sha256(text.encode("utf-8")).digest()


def _encode_alphabet(data: bytes, length: int) -> str:
    value = int.from_bytes(data, "big")
    chars = []
    base = len(CODE_ALPHABET)
    for _ in range(length):
        value, index = divmod(value, base)
        chars.append(CODE_ALPHABET[index])
    return "".join(chars)


def _group(text: str, size: int = 4) -> str:
    return "-".join(text[index : index + size] for index in range(0, len(text), size))


def normalize_machine_code(value: str) -> str:
    code = _NORMALIZE_RE.sub("", str(value or "").upper())
    if len(code) < 12:
        raise LicenseError("机器码格式不正确")
    return code


def normalize_license_code(value: str) -> str:
    code = _NORMALIZE_RE.sub("", str(value or "").upper())
    if len(code) != CODE_LENGTH:
        raise LicenseError(f"授权码必须是 {CODE_LENGTH} 位字母或数字")
    if any(ch not in CODE_ALPHABET for ch in code):
        raise LicenseError("授权码包含无效字符")
    return code


def _read_machine_guid() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg

        access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            access,
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(value).strip()
    except OSError:
        return ""


def _read_system_volume_serial() -> str:
    if os.name != "nt":
        return ""
    try:
        serial_number = ctypes.c_ulong()
        root = os.environ.get("SystemDrive", "C:").rstrip("\\/") + "\\"
        ok = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root),
            None,
            0,
            ctypes.byref(serial_number),
            None,
            None,
            None,
            0,
        )
        if ok:
            return f"{serial_number.value:08X}"
    except (AttributeError, OSError):
        return ""
    return ""


def _machine_fingerprint() -> str:
    parts = {
        "machine_guid": _read_machine_guid(),
        "volume_serial": _read_system_volume_serial(),
        "processor_architecture": os.environ.get("PROCESSOR_ARCHITECTURE", ""),
    }
    if not parts["machine_guid"]:
        parts["computer_name"] = os.environ.get("COMPUTERNAME", "")
        parts["processor_identifier"] = os.environ.get("PROCESSOR_IDENTIFIER", "")
    text = "\n".join(f"{key}={value.strip().lower()}" for key, value in sorted(parts.items()) if value)
    if not text:
        text = f"fallback={os.environ.get('USERNAME', '')}@{os.environ.get('USERDOMAIN', '')}"
    return text


def get_machine_code() -> str:
    digest = hashlib.sha256(("machine-code-v1\n" + _machine_fingerprint()).encode("utf-8")).digest()
    return _group(_encode_alphabet(digest, MACHINE_CODE_LENGTH))


def _legacy_license_code(machine_code: str) -> str:
    normalized_machine_code = normalize_machine_code(machine_code)
    digest = hmac.new(
        _secret("activation-code-v1"),
        normalized_machine_code.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _encode_alphabet(digest, CODE_LENGTH)


def _license_code_signature(machine_code: str, random_part: str) -> str:
    normalized_machine_code = normalize_machine_code(machine_code)
    digest = hmac.new(
        _secret("activation-code-v2"),
        f"{normalized_machine_code}:{random_part}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _encode_alphabet(digest, SIGNATURE_PART_LENGTH)


def generate_license_code(machine_code: str) -> str:
    normalize_machine_code(machine_code)
    random_part = "".join(secrets.choice(CODE_ALPHABET) for _ in range(RANDOM_PART_LENGTH))
    return random_part + _license_code_signature(machine_code, random_part)


def check_license_code(machine_code: str, license_code: str) -> bool:
    try:
        actual = normalize_license_code(license_code)
        random_part = actual[:RANDOM_PART_LENGTH]
        signature_part = actual[RANDOM_PART_LENGTH:]
        expected = _license_code_signature(machine_code, random_part)
    except LicenseError:
        return False
    if hmac.compare_digest(expected, signature_part):
        return True
    return hmac.compare_digest(_legacy_license_code(machine_code), actual)


def _json_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _signature(payload: dict) -> str:
    return hmac.new(
        _secret("license-file-v1"),
        _json_payload(payload).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _stored_value_hash(label: str, value: str) -> str:
    return hmac.new(
        _secret("license-value-v1"),
        f"{label}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _load_license_file(path: Path | None = None) -> dict | None:
    target = path or license_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    payload = data.get("payload")
    signature = data.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, str):
        return None
    if not hmac.compare_digest(_signature(payload), signature):
        return None
    return payload


def is_activated(path: Path | None = None) -> bool:
    payload = _load_license_file(path)
    if not payload:
        return False
    if payload.get("product") != PRODUCT_ID:
        return False
    machine_code = get_machine_code()
    if "machine_code_hash" in payload or "license_code_hash" in payload:
        try:
            current_machine_hash = _stored_value_hash("machine", normalize_machine_code(machine_code))
        except LicenseError:
            return False
        return hmac.compare_digest(str(payload.get("machine_code_hash", "")), current_machine_hash) and isinstance(
            payload.get("license_code_hash"),
            str,
        )
    stored_machine_code = payload.get("machine_code", "")
    stored_license_code = payload.get("license_code", "")
    try:
        stored_machine_code = normalize_machine_code(stored_machine_code)
        machine_code = normalize_machine_code(machine_code)
    except LicenseError:
        return False
    return stored_machine_code == machine_code and check_license_code(machine_code, stored_license_code)


def activate_license(license_code: str, path: Path | None = None) -> dict:
    machine_code = get_machine_code()
    normalized_license_code = normalize_license_code(license_code)
    if not check_license_code(machine_code, normalized_license_code):
        raise LicenseError("授权码错误，或授权码不属于当前机器")

    payload = {
        "product": PRODUCT_ID,
        "version": 2,
        "machine_code_hash": _stored_value_hash("machine", normalize_machine_code(machine_code)),
        "license_code_hash": _stored_value_hash("license", normalized_license_code),
        "activated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data = {"payload": payload, "signature": _signature(payload)}
    target = path or license_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise LicenseError(f"授权文件写入失败：{exc}") from exc
    return payload


def _revocation_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "ADBAutomation-License-Check/1.0",
        },
    )


def _decode_revocation_response(raw: bytes) -> dict:
    data = json.loads(raw.decode("utf-8-sig"))
    if isinstance(data, dict) and isinstance(data.get("content"), str):
        content = data["content"].replace("\n", "")
        data = json.loads(base64.b64decode(content).decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise RevocationError("远程授权配置格式错误，请联系管理员")
    return data


def _read_revocation_config() -> dict:
    errors = []
    for url in REVOCATION_URLS:
        try:
            with urllib.request.urlopen(_revocation_request(url), timeout=REVOCATION_TIMEOUT_SECONDS) as response:
                return _decode_revocation_response(response.read(128 * 1024))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                errors.append("HTTP 404")
            else:
                errors.append(f"HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(str(exc) or exc.__class__.__name__)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RevocationError) as exc:
            errors.append(str(exc) or exc.__class__.__name__)
    detail = "；".join(errors) if errors else "未知错误"
    if "HTTP 404" in errors and len(errors) == len(REVOCATION_URLS):
        raise RevocationError("远程授权黑名单文件不存在，请联系管理员")
    raise RevocationError(f"无法连接远程授权服务器，请检查网络后重试：{detail}")


def _revocation_cache_path() -> Path:
    return runtime_root() / REVOCATION_CACHE_FILENAME


def _load_revocation_cache() -> dict | None:
    try:
        data = json.loads(_revocation_cache_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    payload = data.get("payload")
    signature = data.get("signature")
    if not isinstance(payload, dict) or not isinstance(signature, str):
        return None
    if not hmac.compare_digest(_signature(payload), signature):
        return None
    return payload


def _save_revocation_cache(data: dict) -> None:
    payload = dict(data)
    cached = {"payload": payload, "signature": _signature(payload)}
    try:
        _revocation_cache_path().write_text(
            json.dumps(cached, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def check_remote_authorization(machine_code: str | None = None) -> tuple[bool, str]:
    machine_code = machine_code or get_machine_code()
    normalized_machine = normalize_machine_code(machine_code)
    try:
        data = _read_revocation_config()
        _save_revocation_cache(data)
    except RevocationError as exc:
        cached_data = _load_revocation_cache()
        if cached_data is not None:
            data = cached_data
        elif REVOCATION_REQUIRED:
            return False, str(exc)
        else:
            return True, ""

    message = str(data.get("message") or "当前机器授权已被取消，请联系管理员")
    if bool(data.get("disabled", False)):
        return False, message

    revoked_machines = data.get("revoked_machines", [])
    if not isinstance(revoked_machines, list):
        raise RevocationError("远程授权配置格式错误，请联系管理员")
    revoked_normalized = {
        _NORMALIZE_RE.sub("", str(item or "").upper())
        for item in revoked_machines
        if str(item or "").strip()
    }
    if normalized_machine in revoked_normalized:
        return False, message

    revoked_hashes = data.get("revoked_hashes", [])
    if isinstance(revoked_hashes, list):
        machine_hash = hashlib.sha256(normalized_machine.encode("ascii")).hexdigest()
        if machine_hash in {str(item or "").lower() for item in revoked_hashes}:
            return False, message
    return True, ""


def _center_window(window: tk.Tk, width: int, height: int) -> None:
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, int((screen_width - width) / 2))
    y = max(0, int((screen_height - height) / 2))
    window.geometry(f"{width}x{height}+{x}+{y}")


def configure_tk_chinese_fonts(root: tk.Tk) -> str:
    families = set(tkfont.families(root))
    family = next((name for name in _FONT_CANDIDATES if name in families), "Arial")
    for font_name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkFixedFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
    ):
        try:
            tkfont.nametofont(font_name).configure(family=family, size=10)
        except tk.TclError:
            pass
    root.option_add("*Font", f"{{{family}}} 10")
    return family


def _check_remote_or_show_error(parent: tk.Tk, machine_code: str) -> bool:
    try:
        allowed, message = check_remote_authorization(machine_code)
    except RevocationError as exc:
        allowed, message = False, str(exc)
    if allowed:
        return True
    messagebox.showerror("授权不可用", message, parent=parent)
    return False


def ensure_license_tk() -> bool:
    machine_code = get_machine_code()

    if is_activated():
        return True

    result = {"ok": False}
    root = tk.Tk()
    root.title("三角洲助手授权验证")
    root.resizable(False, False)
    font_family = configure_tk_chinese_fonts(root)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", font=(font_family, 10))
    style.configure("TButton", font=(font_family, 10))
    style.configure("TLabel", font=(font_family, 10))
    style.configure("TEntry", font=(font_family, 10))

    frame = ttk.Frame(root, padding=(22, 20, 22, 18))
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="三角洲助手授权验证", font=(font_family, 14, "bold")).pack(anchor="w")
    ttk.Label(frame, text="机器码", padding=(0, 14, 0, 4)).pack(anchor="w")

    machine_row = ttk.Frame(frame)
    machine_row.pack(fill="x")
    machine_var = tk.StringVar(value=machine_code)
    machine_entry = ttk.Entry(machine_row, textvariable=machine_var, state="readonly", width=36)
    machine_entry.pack(side="left", fill="x", expand=True)

    def copy_machine_code() -> None:
        root.clipboard_clear()
        root.clipboard_append(machine_code)

    ttk.Button(machine_row, text="复制机器码", command=copy_machine_code, width=12).pack(side="left", padx=(8, 0))

    ttk.Label(frame, text="请输入授权码", padding=(0, 14, 0, 4)).pack(anchor="w")
    code_var = tk.StringVar()
    code_row = ttk.Frame(frame)
    code_row.pack(fill="x")
    code_entry = ttk.Entry(code_row, textvariable=code_var, width=36)
    code_entry.pack(side="left", fill="x", expand=True)

    error_var = tk.StringVar()

    def close() -> None:
        result["ok"] = False
        root.destroy()

    def verify() -> None:
        try:
            activate_license(code_var.get())
        except LicenseError as exc:
            error_var.set(str(exc))
            code_entry.focus_set()
            code_entry.selection_range(0, tk.END)
            return
        result["ok"] = True
        messagebox.showinfo("授权成功", "授权验证通过，可以正常使用。", parent=root)
        root.destroy()

    ttk.Button(code_row, text="确认授权", command=verify, width=12).pack(side="left", padx=(8, 0))
    ttk.Label(frame, text=CONTACT_TEXT, padding=(0, 12, 0, 0)).pack(anchor="w")
    ttk.Label(frame, textvariable=error_var, foreground="#b00020", padding=(0, 8, 0, 0)).pack(anchor="w")

    button_row = ttk.Frame(frame)
    button_row.pack(fill="x", pady=(8, 0))
    ttk.Button(button_row, text="退出", command=close, width=12).pack(side="right")

    root.protocol("WM_DELETE_WINDOW", close)
    root.bind("<Return>", lambda _event: verify())
    _center_window(root, 560, 310)
    code_entry.focus_set()
    root.mainloop()
    return result["ok"]
