from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
import urllib.error
import urllib.parse
import urllib.request

from adb_automation.license_gate import (
    CODE_LENGTH,
    CONTACT_TEXT,
    LicenseError,
    configure_tk_chinese_fonts,
    generate_license_code,
    get_machine_code,
    normalize_license_code,
    normalize_machine_code,
)


REPO = "narong258269/nanrong"
BRANCH = "master"
GITEE_API_BASE = "https://gitee.com/api/v5"
GITEE_TOKEN_FILENAME = "gitee_token.txt"
ISSUED_PATH = "issued.json"
REVOKED_PATH = "revoked.json"
REVOKED_MESSAGE = "当前机器授权已被取消，请联系 QQ：2337767459，微信：z2337767459"
SWITCH_ENABLED_PNG = "iVBORw0KGgoAAAANSUhEUgAAAEwAAAAWCAYAAABqgnq6AAACb0lEQVR42u2ZXUhTYRjHf8d9iNrQMnAYVNK6MOoiSgrblWBmRFAUTZyuqNCLsq+LCvq4SLALGxEJQlCJykYgwchsGNGFlqaUgiUUkcFEcTE/5z5anS5W0+mMo1Bs8/yvnve8z+Ecfjz/933OeQVRFAGwWuqDgayIMhSVCADCb2AyLGkSlFZLvViwZ6+MQoLsz56KCTKGxUkGJgOTgUWVlFITt/efD8Xd2eYlPazxlY1Jr5vyvKKI83Vtj7nb2oAmKQWA74EAE54p0jVpoZyRCRfPLz5Em7o6eoHNhvVnLAXabXsdTV12UpM1Ydef9LwMxQ7XELZztaxNzwTApD/AqXwjAH2Oj9xquc+DkzdD+fvMZdFdYXNhLRZaeZ6B4tz9C84fqTkbn5b8X2p8baO5N1iBvoAf19Q4hdUnZlXkcPwCExGpfWHF0tG8YI7DNTSTL4oc1R+kLM8Qu5bszjZHtKUUO3r8Xs4UmDiUUyDpZQI/f6BWqmLfknOhSd0lJ71uViQmc+zeJQZHRyLC+OJ08L4qWIFT3mmauuw8etMS+5ZcSisx4BzEmKsFoKb0Ghu16+fl7Lox02IMjzsxF18mJ2tL1FrynzWuvoCfgW8OdBnrJN/z7ms/mzJ1y7PTb+1rJ1e3lUSlWiKsD6xZmUFKYtKCOW6fh1H3OCqFIv52yfZPbzm9uzQ0rmiojAhvbHoCgM7PvVTkl4TNKRIUJKuTGBpzUlh9HJVCxbaszaxKSYs/YFWHL4SN7xiv/HUNi/S5lJ25gRrTdQB6Km3Lp3GdvWjPq8Srlpjq9AVRFOnsaJN/UUvQjp16QZAPQVjUIcgvEzfu2sBXH5UAAAAASUVORK5CYII="
SWITCH_DISABLED_PNG = "iVBORw0KGgoAAAANSUhEUgAAAEwAAAAWCAYAAABqgnq6AAACm0lEQVR42u2ZX0hTURzHP1fvTLcsmYbkn4dMHSUJbkF7iLSHKMSK1MywRUQ9zB6Kesn+UD02C/PFRRRBhhti+OZWYU9GpQ9NZU+5Fpg0DRW0LW3q7cG6ObO8gyAn9/v0O/f8Dgc+/H7nd+7vCJIkAeB0NM8bqpZU9VGLACD8AKbCUiZBdDqapb37SlUUCvTU3SHFqRiikwpMBaYCW1ESFZeHqmrZllqdijfovnyFzUeqSC0sBGCku4ehzk6K6i7+5vuu+THeJjuadckAzIXDhCcmWZOql32mRj5T6u4gKT195QJbCOvnWAm08Jcgo289pBgMvKixRMwNtDhk23TtKjmVlQDkWY5RUGsFYNzrpa+hkeL7935VqkPlKzvCFsOKBtqgy0XG7hLyj1uY8PnYVFEuRxpAf0MjacYiNhbvWn0pGa1mgkG8djt5NTXyt75bt9EkJ8vjSf8H0oxFEet8TieDLjcAs9+mmR4bx73/oDwfHBpancC89rsk6lPl8fYb15ddI0kSeRYLW06fit2UlFqdS6blcukoarUYTp4g9CmAq7Tsj4f07NRXdFlZmOttSDMzxCckxH5KLoam5MAvqLXy8dlzGV7JwwdL+k36/Xib7PNFIhjE397O+7YnsZ+S0VwlFmtPWyv9dxoZ7e0DYMI3gDYjEzEpiZzDFZjrbQCEAgHM9TY2mEyxm5L/StvOnZXtV+cvsLXWyvrc3Aif0d5ejJfq1Jv+Qs2Fw4SGh4nTaCJheTzoMjIRdbq/Vt7psXEEUVz9EQbguWkj0PWSFEM+a7OzI+ZGunsoOGONvOvFi4haLaFAAHfZAeI0GtJMRhL1+v/XEHO0PFL7YSjuh6k/31FHmCRJvHndpbaoFWiHeacgqI8gRPUI8h0i3P/aYLX6ywAAAABJRU5ErkJggg=="


class GitHubError(RuntimeError):
    pass


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_license_code(machine_code: str) -> str:
    return generate_license_code(normalize_machine_code(machine_code))


def normalize_for_compare(machine_code: str) -> str:
    return normalize_machine_code(machine_code)


def find_gh() -> str:
    exe = shutil.which("gh")
    if exe:
        return exe
    candidate = Path.home() / "tools" / "gh" / "bin" / "gh.exe"
    if candidate.is_file():
        return str(candidate)
    raise GitHubError("找不到 GitHub CLI：请先安装并登录 gh")


def gh_api(args: list[str], payload: dict | None = None) -> dict:
    command = [find_gh(), "api", *args]
    input_text = None
    if payload is not None:
        input_text = json.dumps(payload, ensure_ascii=False)
        command.extend(["--input", "-"])
    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    completed = subprocess.run(
        command,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise GitHubError(detail or f"GitHub API 调用失败：{completed.returncode}")
    if not completed.stdout.strip():
        return {}
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise GitHubError("GitHub 返回内容不是 JSON") from exc


def gitee_token_path() -> Path:
    return runtime_root() / GITEE_TOKEN_FILENAME


def read_gitee_token() -> str:
    token = os.environ.get("GITEE_ACCESS_TOKEN", "").strip()
    if token:
        return token
    try:
        token = gitee_token_path().read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if token:
        return token
    raise GitHubError(
        f"找不到 Gitee 私人令牌：请在授权管理器同目录创建 {GITEE_TOKEN_FILENAME}，"
        "或设置环境变量 GITEE_ACCESS_TOKEN"
    )


def _gitee_contents_url(path: str, query: dict[str, str] | None = None) -> str:
    owner, repo = REPO.split("/", 1)
    encoded_path = urllib.parse.quote(path.strip("/"), safe="")
    url = f"{GITEE_API_BASE}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/contents/{encoded_path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return url


def gitee_api(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    token = read_gitee_token()
    query = {"access_token": token}
    if method == "GET":
        query["ref"] = BRANCH
    data = None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "ADBAutomation-License-Manager/1.0",
    }
    if payload is not None:
        body = dict(payload)
        body["access_token"] = token
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        _gitee_contents_url(path, query if data is None else None),
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace").strip()
        except OSError:
            pass
        raise GitHubError(detail or f"Gitee API 调用失败：HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GitHubError(f"Gitee API 连接失败：{exc}") from exc
    if not raw.strip():
        return {}
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitHubError("Gitee 返回内容不是 JSON") from exc


def default_issued() -> dict:
    return {"version": 1, "machines": []}


def default_revoked() -> dict:
    return {
        "version": 1,
        "revoked_machines": [],
        "revoked_hashes": [],
        "disabled": False,
        "message": REVOKED_MESSAGE,
    }


def read_github_json(path: str, default: dict) -> tuple[dict, str | None]:
    try:
        data = gitee_api(path, "GET")
    except GitHubError as exc:
        if "Not Found" in str(exc) or "404" in str(exc):
            return default, None
        raise
    if isinstance(data, list):
        return default, None
    content = data.get("content")
    if not isinstance(content, str):
        return default, data.get("sha")
    try:
        raw = base64.b64decode(content).decode("utf-8-sig")
        parsed = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise GitHubError(f"{path} 格式错误") from exc
    if not isinstance(parsed, dict):
        raise GitHubError(f"{path} 格式错误")
    return parsed, data.get("sha")


def write_github_json(path: str, data: dict, sha: str | None, message: str) -> None:
    payload = {
        "message": message,
        "content": base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii"),
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    gitee_api(path, "PUT" if sha else "POST", payload)


def normalize_issued(data: dict) -> dict:
    machines = data.get("machines")
    if not isinstance(machines, list):
        legacy = data.get("issued_machines")
        machines = legacy if isinstance(legacy, list) else []
    normalized = {"version": int(data.get("version", 1) or 1), "machines": []}
    seen: set[str] = set()
    for item in machines:
        if not isinstance(item, dict):
            continue
        machine = str(item.get("machine_code", "")).strip()
        try:
            key = normalize_for_compare(machine)
        except LicenseError:
            continue
        if key in seen:
            continue
        seen.add(key)
        normalized["machines"].append(
            {
                "machine_code": machine,
                "label": str(item.get("label", "")).strip(),
                "note": str(item.get("note", "")).strip(),
                "issued_count": int(item.get("issued_count", 0) or 0),
                "first_issued_at": str(item.get("first_issued_at", "")).strip(),
                "last_issued_at": str(item.get("last_issued_at", "")).strip(),
                "last_code_hash": str(item.get("last_code_hash", "")).strip(),
            }
        )
    return normalized


def normalize_revoked(data: dict) -> dict:
    revoked = data.get("revoked_machines")
    hashes = data.get("revoked_hashes")
    return {
        "version": int(data.get("version", 1) or 1),
        "revoked_machines": [str(item).strip() for item in revoked if str(item).strip()]
        if isinstance(revoked, list)
        else [],
        "revoked_hashes": [str(item).strip().lower() for item in hashes if str(item).strip()]
        if isinstance(hashes, list)
        else [],
        "disabled": bool(data.get("disabled", False)),
        "message": str(data.get("message") or REVOKED_MESSAGE),
    }


def record_issue(machine_code: str, label: str, note: str, license_code: str) -> None:
    machine_code = machine_code.strip()
    key = normalize_for_compare(machine_code)
    issued, sha = read_github_json(ISSUED_PATH, default_issued())
    issued = normalize_issued(issued)
    timestamp = now_iso()
    code_hash = hashlib.sha256(normalize_license_code(license_code).encode("ascii")).hexdigest()[:16]

    target = None
    for machine in issued["machines"]:
        if normalize_for_compare(machine["machine_code"]) == key:
            target = machine
            break
    if target is None:
        target = {
            "machine_code": machine_code,
            "label": "",
            "note": "",
            "issued_count": 0,
            "first_issued_at": timestamp,
            "last_issued_at": "",
            "last_code_hash": "",
        }
        issued["machines"].append(target)

    target["machine_code"] = machine_code
    target["label"] = label.strip()
    target["note"] = note.strip()
    target["issued_count"] = int(target.get("issued_count", 0) or 0) + 1
    target["first_issued_at"] = target.get("first_issued_at") or timestamp
    target["last_issued_at"] = timestamp
    target["last_code_hash"] = code_hash
    issued["machines"].sort(key=lambda item: (item.get("label") or item.get("machine_code") or "").lower())
    write_github_json(ISSUED_PATH, issued, sha, f"Issue license for {machine_code}")


def load_remote_state() -> tuple[dict, str | None, dict, str | None]:
    issued, issued_sha = read_github_json(ISSUED_PATH, default_issued())
    revoked, revoked_sha = read_github_json(REVOKED_PATH, default_revoked())
    if issued_sha is None:
        write_github_json(ISSUED_PATH, normalize_issued(issued), None, "Initialize issued.json")
        issued, issued_sha = read_github_json(ISSUED_PATH, default_issued())
    if revoked_sha is None:
        write_github_json(REVOKED_PATH, normalize_revoked(revoked), None, "Initialize revoked.json")
        revoked, revoked_sha = read_github_json(REVOKED_PATH, default_revoked())
    return normalize_issued(issued), issued_sha, normalize_revoked(revoked), revoked_sha


def set_machine_revoked(machine_code: str, revoked_state: bool) -> None:
    key = normalize_for_compare(machine_code)
    revoked, sha = read_github_json(REVOKED_PATH, default_revoked())
    revoked = normalize_revoked(revoked)
    machines = []
    found = False
    for item in revoked["revoked_machines"]:
        try:
            item_key = normalize_for_compare(item)
        except LicenseError:
            continue
        if item_key == key:
            found = True
            if revoked_state:
                machines.append(machine_code.strip())
        else:
            machines.append(item)
    if revoked_state and not found:
        machines.append(machine_code.strip())
    revoked["revoked_machines"] = machines
    write_github_json(
        REVOKED_PATH,
        revoked,
        sha,
        ("Revoke " if revoked_state else "Restore ") + machine_code.strip(),
    )


def set_global_disabled(disabled: bool) -> None:
    revoked, sha = read_github_json(REVOKED_PATH, default_revoked())
    revoked = normalize_revoked(revoked)
    revoked["disabled"] = bool(disabled)
    write_github_json(REVOKED_PATH, revoked, sha, "Disable all machines" if disabled else "Enable all machines")


def run_cli(argv: list[str]) -> int:
    if len(argv) != 2:
        print("用法:")
        print("  python license_generator.py <机器码>")
        print("  python license_generator.py --current")
        return 2
    machine_code = get_machine_code() if argv[1] == "--current" else argv[1]
    try:
        license_code = make_license_code(machine_code)
    except LicenseError as exc:
        print(f"错误: {exc}")
        return 1
    print(f"机器码: {machine_code}")
    print(f"授权码: {license_code}")
    return 0


class LicenseManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("三角洲助手授权管理器")
        self.root.minsize(980, 620)
        self.font_family = configure_tk_chinese_fonts(root)
        self.issued: dict = default_issued()
        self.revoked: dict = default_revoked()
        self.current_code = tk.StringVar()
        self.machine_var = tk.StringVar()
        self.label_var = tk.StringVar()
        self.note_var = tk.StringVar()
        self.auth_toggle_text = tk.StringVar(value="请先选择机器")
        self.status_var = tk.StringVar(value=CONTACT_TEXT)
        self.global_var = tk.StringVar(value="全局状态：读取中")
        self._busy = False
        self.github_buttons: list[ttk.Button] = []
        self.switch_images = self._build_switch_images()
        self._build_styles()
        self._build_ui()
        self.root.after(100, self.refresh)

    def _build_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=(self.font_family, 10))
        style.configure("TButton", font=(self.font_family, 10))
        style.configure("TLabel", font=(self.font_family, 10))
        style.configure("TEntry", font=(self.font_family, 10))
        style.configure("Treeview", rowheight=30)

    def _build_switch_images(self) -> dict[str, tk.PhotoImage]:
        return {
            "enabled": tk.PhotoImage(data=SWITCH_ENABLED_PNG),
            "disabled": tk.PhotoImage(data=SWITCH_DISABLED_PNG),
        }

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=(18, 16, 18, 16))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="三角洲助手授权管理器", font=(self.font_family, 14, "bold")).pack(anchor="w")

        form = ttk.Frame(outer)
        form.pack(fill="x", pady=(14, 0))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Label(form, text="机器码").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Entry(form, textvariable=self.machine_var).grid(row=0, column=1, columnspan=3, sticky="ew", pady=5)
        ttk.Label(form, text="标签").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Entry(form, textvariable=self.label_var).grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(form, text="备注").grid(row=1, column=2, sticky="w", padx=(14, 8), pady=5)
        ttk.Entry(form, textvariable=self.note_var).grid(row=1, column=3, sticky="ew", pady=5)
        ttk.Label(form, text=f"授权码（{CODE_LENGTH} 位字母数字）").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=5)
        ttk.Entry(form, textvariable=self.current_code, state="readonly").grid(row=2, column=1, columnspan=3, sticky="ew", pady=5)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(12, 0))
        generate_record_button = ttk.Button(buttons, text="生成并记录", command=self.generate_and_record, width=14)
        generate_record_button.pack(side="left")
        self.github_buttons.append(generate_record_button)
        ttk.Button(buttons, text="仅生成", command=self.generate_only, width=10).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="复制授权码", command=self.copy_code, width=12).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="清空", command=self.clear_form, width=8).pack(side="left", padx=(8, 0))
        refresh_button = ttk.Button(buttons, text="刷新列表", command=self.refresh, width=10)
        refresh_button.pack(side="right")
        self.github_buttons.append(refresh_button)

        ttk.Label(outer, textvariable=self.status_var, padding=(0, 10, 0, 0)).pack(anchor="w")
        ttk.Label(outer, textvariable=self.global_var).pack(anchor="w")

        columns = ("label", "machine", "count", "last", "note")
        self.tree = ttk.Treeview(outer, columns=columns, show=("tree", "headings"), selectmode="browse")
        self.tree.heading("#0", text="授权开关")
        self.tree.column("#0", width=118, anchor="center", stretch=False)
        self.tree.heading("label", text="标签")
        self.tree.heading("machine", text="机器码")
        self.tree.heading("count", text="发码次数")
        self.tree.heading("last", text="最近发码时间")
        self.tree.heading("note", text="备注")
        self.tree.column("label", width=150, stretch=False)
        self.tree.column("machine", width=230, stretch=False)
        self.tree.column("count", width=80, anchor="center", stretch=False)
        self.tree.column("last", width=180, stretch=False)
        self.tree.column("note", width=240, stretch=True)
        self.tree.pack(fill="both", expand=True, pady=(12, 0))
        self.tree.bind("<<TreeviewSelect>>", self.load_selected)
        self.tree.bind("<Double-1>", self.load_selected)
        self.tree.bind("<Button-1>", self.handle_tree_click)

        control = ttk.Frame(outer)
        control.pack(fill="x", pady=(12, 0))
        ttk.Label(control, textvariable=self.auth_toggle_text).pack(side="left")
        disable_all_button = ttk.Button(control, text="暂停全部机器", command=lambda: self.set_global(True), width=14)
        disable_all_button.pack(side="right", padx=(8, 0))
        self.github_buttons.append(disable_all_button)
        enable_all_button = ttk.Button(control, text="恢复全部机器", command=lambda: self.set_global(False), width=14)
        enable_all_button.pack(side="right")
        self.github_buttons.append(enable_all_button)

    def _set_busy(self, busy: bool, message: str | None = None) -> None:
        self._busy = bool(busy)
        state = "disabled" if self._busy else "normal"
        for button in self.github_buttons:
            try:
                button.configure(state=state)
            except tk.TclError:
                pass
        try:
            self.tree.configure(cursor="watch" if self._busy else "")
        except tk.TclError:
            pass
        if message:
            self.status_var.set(message)

    def _run_github_task(self, start_message: str, worker, on_success) -> None:
        if self._busy:
            self.status_var.set("Gitee 操作正在处理中，请稍等。")
            return
        self._set_busy(True, start_message)

        def run() -> None:
            result = None
            error = None
            try:
                result = worker()
            except (GitHubError, LicenseError) as exc:
                error = str(exc)
            except Exception as exc:
                error = f"操作失败：{exc}"

            def finish() -> None:
                self._set_busy(False)
                if error:
                    self.status_var.set(error)
                    return
                on_success(result)

            try:
                self.root.after(0, finish)
            except tk.TclError:
                pass

        threading.Thread(target=run, name="GiteeLicenseTask", daemon=True).start()

    def _selected_machine(self) -> str | None:
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], "values")
        return str(values[1]) if values else None

    def _revoked_set(self) -> set[str]:
        result = set()
        for item in self.revoked.get("revoked_machines", []):
            try:
                result.add(normalize_for_compare(str(item)))
            except LicenseError:
                pass
        return result

    def _selected_machine_is_authorized(self) -> bool | None:
        machine = self._selected_machine()
        if not machine:
            return None
        try:
            return normalize_for_compare(machine) not in self._revoked_set()
        except LicenseError:
            return None

    def _sync_authorization_toggle(self) -> None:
        authorized = self._selected_machine_is_authorized()
        if authorized is None:
            self.auth_toggle_text.set("点击列表左侧 YES/NO 开关，可启用或停用对应机器。")
            return
        self.auth_toggle_text.set("选中机器：YES 允许运行" if authorized else "选中机器：NO 已停用")

    def handle_tree_click(self, event) -> str | None:
        if self.tree.identify_region(event.x, event.y) != "tree":
            return None
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return None
        if self._busy:
            self.status_var.set("Gitee 操作正在处理中，请稍等。")
            return "break"
        self.tree.selection_set(item_id)
        self.tree.focus(item_id)
        values = self.tree.item(item_id, "values")
        if values:
            self.toggle_machine_authorization(str(values[1]))
        return "break"

    def _apply_remote_state(
        self,
        issued: dict,
        revoked: dict,
        selected_machine: str | None,
        status_message: str,
    ) -> None:
        self.issued = issued
        self.revoked = revoked
        for item in self.tree.get_children():
            self.tree.delete(item)
        revoked = self._revoked_set()
        for machine in self.issued.get("machines", []):
            machine_code = machine.get("machine_code", "")
            try:
                key = normalize_for_compare(machine_code)
            except LicenseError:
                continue
            authorized = key not in revoked
            state = "启用" if authorized else "停用"
            item_id = self.tree.insert(
                "",
                "end",
                text="",
                image=self.switch_images["enabled" if authorized else "disabled"],
                tags=(state,),
                values=(
                    machine.get("label", ""),
                    machine_code,
                    machine.get("issued_count", 0),
                    machine.get("last_issued_at", ""),
                    machine.get("note", ""),
                ),
            )
            if selected_machine:
                try:
                    if normalize_for_compare(selected_machine) == key:
                        self.tree.selection_set(item_id)
                        self.tree.focus(item_id)
                except LicenseError:
                    pass
        self.global_var.set("全局状态：全部停用" if self.revoked.get("disabled") else "全局状态：正常")
        self.status_var.set(status_message)
        self._sync_authorization_toggle()

    def refresh(self) -> None:
        selected_machine = self._selected_machine()

        def worker():
            issued, _issued_sha, revoked, _revoked_sha = load_remote_state()
            return issued, revoked

        def done(result):
            issued, revoked = result
            self._apply_remote_state(issued, revoked, selected_machine, "Gitee 记录已刷新。")

        self._run_github_task("正在读取 Gitee 记录...", worker, done)

    def load_selected(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        label, machine, _count, _last, note = self.tree.item(selected[0], "values")
        state = "启用" if self._selected_machine_is_authorized() else "停用"
        self.machine_var.set(machine)
        self.label_var.set(label)
        self.note_var.set(note)
        self.status_var.set(f"已选中：{label or machine}（{state}）")
        self._sync_authorization_toggle()

    def generate_only(self) -> None:
        try:
            code = make_license_code(self.machine_var.get())
        except LicenseError as exc:
            self.status_var.set(str(exc))
            return
        self.current_code.set(code)
        self.status_var.set("已生成授权码，未写入 Gitee 记录。")

    def generate_and_record(self) -> None:
        try:
            machine = self.machine_var.get().strip()
            code = make_license_code(machine)
            label = self.label_var.get()
            note = self.note_var.get()
        except LicenseError as exc:
            self.status_var.set(str(exc))
            return
        selected_machine = machine

        def worker():
            record_issue(machine, label, note, code)
            issued, _issued_sha, revoked, _revoked_sha = load_remote_state()
            return code, issued, revoked

        def done(result):
            generated_code, issued, revoked = result
            self.current_code.set(generated_code)
            self._apply_remote_state(issued, revoked, selected_machine, "已生成授权码，并写入 Gitee 记录。")

        self._run_github_task("正在生成并写入 Gitee 记录...", worker, done)

    def copy_code(self) -> None:
        code = self.current_code.get().strip()
        if not code:
            self.status_var.set("没有可复制的授权码。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        self.status_var.set("授权码已复制。")

    def clear_form(self) -> None:
        self.machine_var.set("")
        self.label_var.set("")
        self.note_var.set("")
        self.current_code.set("")
        self.status_var.set(CONTACT_TEXT)

    def set_selected_revoked(self, revoked_state: bool) -> None:
        machine = self._selected_machine()
        if not machine:
            self.status_var.set("请先在列表中选择一台机器。")
            return
        self.set_machine_revoked_state(machine, revoked_state)

    def set_machine_revoked_state(self, machine: str, revoked_state: bool) -> None:
        selected_machine = machine

        def worker():
            set_machine_revoked(machine, revoked_state)
            issued, _issued_sha, revoked, _revoked_sha = load_remote_state()
            return issued, revoked

        def done(result):
            issued, revoked = result
            message = "已停用选中机器。" if revoked_state else "已恢复选中机器。"
            self._apply_remote_state(issued, revoked, selected_machine, message)

        self._run_github_task("正在写入 Gitee 授权状态...", worker, done)

    def toggle_machine_authorization(self, machine: str) -> None:
        try:
            authorized = normalize_for_compare(machine) not in self._revoked_set()
        except LicenseError as exc:
            self.status_var.set(str(exc))
            return
        self.set_machine_revoked_state(machine, authorized)

    def toggle_selected_authorization(self) -> None:
        authorized = self._selected_machine_is_authorized()
        if authorized is None:
            self.status_var.set("请先在列表中选择一台机器。")
            return
        self.set_selected_revoked(authorized)

    def set_global(self, disabled: bool) -> None:
        text = "暂停全部机器" if disabled else "恢复全部机器"
        if not messagebox.askyesno("确认操作", f"确定要{text}吗？", parent=self.root):
            return

        selected_machine = self._selected_machine()

        def worker():
            set_global_disabled(disabled)
            issued, _issued_sha, revoked, _revoked_sha = load_remote_state()
            return issued, revoked

        def done(result):
            issued, revoked = result
            self._apply_remote_state(issued, revoked, selected_machine, f"已{text}。")

        self._run_github_task(f"正在{text}...", worker, done)


def run_gui() -> int:
    root = tk.Tk()
    app = LicenseManagerApp(root)
    root.update_idletasks()
    width, height = 980, 650
    x = max(0, int((root.winfo_screenwidth() - width) / 2))
    y = max(0, int((root.winfo_screenheight() - height) / 2))
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    if len(argv) > 1:
        return run_cli(argv)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
