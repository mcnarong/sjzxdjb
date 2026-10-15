from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\workflows.pyc')

del _exec_recovered_module

import sys as _sys
from pathlib import Path as _Path
from .adb import RESOURCE_ROOT as _ADB_RESOURCE_ROOT
from .adb import RUNTIME_ROOT as _ADB_RUNTIME_ROOT
from .wait_settings import get_wait_seconds as _wait_seconds


def _bundle_root():
    bundle_root = getattr(_sys, "_MEIPASS", None)
    return _Path(bundle_root) if bundle_root else _ADB_RESOURCE_ROOT


def _resource_path(name):
    external = _ADB_RUNTIME_ROOT / name
    if external.exists():
        return external
    bundle = _bundle_root()
    if bundle is not None:
        bundled = bundle / name
        if bundled.exists():
            return bundled
    return external


def _refresh_device_profiles_for_onefile():
    global PROJECT_ROOT
    global CUSTOM_PROFILE_PATH
    global DEVICE_PROFILE_DIR
    global DELTA_FORCE_DEVICE_PROFILES
    global DELTA_FORCE_SCREEN
    global DELTA_FORCE_STATIONS
    global DELTA_FORCE_LOBBY_BACK_TAP
    global DELTA_FORCE_DETAIL_BACK_TAP
    global DELTA_FORCE_SETTINGS_TAP
    global DELTA_FORCE_LOGOUT_TAP
    global DELTA_FORCE_LOGOUT_CONFIRM_TAP
    global DELTA_FORCE_LOGIN_AGREEMENT_TAP
    global DELTA_FORCE_ACTION_BUTTON_TAP
    global DELTA_FORCE_REPLENISH_PRICE_TAP
    global QQ_DEVICE_PROFILES

    CUSTOM_PROFILE_PATH = _resource_path("device_profiles.json")
    DEVICE_PROFILE_DIR = _resource_path("device_profiles")
    delta_profiles = _required_profiles("delta_force_profiles", "delta_force")
    qq_profiles = _required_profiles("qq_profiles", "qq")

    DELTA_FORCE_DEVICE_PROFILES = delta_profiles
    DELTA_FORCE_SCREEN = delta_profiles[0]["screen"]
    DELTA_FORCE_STATIONS = delta_profiles[0]["stations"]
    DELTA_FORCE_LOBBY_BACK_TAP = delta_profiles[0]["lobby_back_tap"]
    DELTA_FORCE_DETAIL_BACK_TAP = delta_profiles[0]["detail_back_tap"]
    DELTA_FORCE_SETTINGS_TAP = delta_profiles[0]["settings_tap"]
    DELTA_FORCE_LOGOUT_TAP = delta_profiles[0]["logout_tap"]
    DELTA_FORCE_LOGOUT_CONFIRM_TAP = delta_profiles[0]["logout_confirm_tap"]
    DELTA_FORCE_LOGIN_AGREEMENT_TAP = delta_profiles[0]["login_agreement_tap"]
    DELTA_FORCE_ACTION_BUTTON_TAP = delta_profiles[0]["action_button_tap"]
    DELTA_FORCE_REPLENISH_PRICE_TAP = delta_profiles[0]["replenish_price_tap"]
    QQ_DEVICE_PROFILES = qq_profiles
    PROJECT_ROOT = _ADB_RUNTIME_ROOT


_refresh_device_profiles_for_onefile()
del _refresh_device_profiles_for_onefile


def refresh_device_profiles():
    global PROJECT_ROOT
    global CUSTOM_PROFILE_PATH
    global DEVICE_PROFILE_DIR
    global DELTA_FORCE_DEVICE_PROFILES
    global DELTA_FORCE_SCREEN
    global DELTA_FORCE_STATIONS
    global DELTA_FORCE_LOBBY_BACK_TAP
    global DELTA_FORCE_DETAIL_BACK_TAP
    global DELTA_FORCE_SETTINGS_TAP
    global DELTA_FORCE_LOGOUT_TAP
    global DELTA_FORCE_LOGOUT_CONFIRM_TAP
    global DELTA_FORCE_LOGIN_AGREEMENT_TAP
    global DELTA_FORCE_ACTION_BUTTON_TAP
    global DELTA_FORCE_REPLENISH_PRICE_TAP
    global QQ_DEVICE_PROFILES

    CUSTOM_PROFILE_PATH = _resource_path("device_profiles.json")
    DEVICE_PROFILE_DIR = _resource_path("device_profiles")
    delta_profiles = _required_profiles("delta_force_profiles", "delta_force")
    qq_profiles = _required_profiles("qq_profiles", "qq")

    DELTA_FORCE_DEVICE_PROFILES = delta_profiles
    DELTA_FORCE_SCREEN = delta_profiles[0]["screen"]
    DELTA_FORCE_STATIONS = delta_profiles[0]["stations"]
    DELTA_FORCE_LOBBY_BACK_TAP = delta_profiles[0]["lobby_back_tap"]
    DELTA_FORCE_DETAIL_BACK_TAP = delta_profiles[0]["detail_back_tap"]
    DELTA_FORCE_SETTINGS_TAP = delta_profiles[0]["settings_tap"]
    DELTA_FORCE_LOGOUT_TAP = delta_profiles[0]["logout_tap"]
    DELTA_FORCE_LOGOUT_CONFIRM_TAP = delta_profiles[0]["logout_confirm_tap"]
    DELTA_FORCE_LOGIN_AGREEMENT_TAP = delta_profiles[0]["login_agreement_tap"]
    DELTA_FORCE_ACTION_BUTTON_TAP = delta_profiles[0]["action_button_tap"]
    DELTA_FORCE_REPLENISH_PRICE_TAP = delta_profiles[0]["replenish_price_tap"]
    QQ_DEVICE_PROFILES = qq_profiles
    PROJECT_ROOT = _ADB_RUNTIME_ROOT
    return qq_profiles, delta_profiles


def _set_sleep_after_note(steps, note_part, seconds):
    for step in steps:
        if step.get("action") in {"sleep", "wait"} and note_part in str(step.get("note", "")):
            step["seconds"] = seconds


def _set_sleep_after_previous_note(steps, previous_note_part, seconds):
    previous = None
    for step in steps:
        if (
            previous is not None
            and step.get("action") in {"sleep", "wait"}
            and previous_note_part in str(previous.get("note", ""))
        ):
            step["seconds"] = seconds
            return
        previous = step


def _replace_sleep_after_previous_note_with_step(steps, previous_note_part, replacement):
    previous = None
    for index, step in enumerate(steps):
        if (
            previous is not None
            and step.get("action") in {"sleep", "wait"}
            and previous_note_part in str(previous.get("note", ""))
        ):
            steps[index] = replacement
            return True
        previous = step
    return False


def _replace_sleep_seconds(steps, old_seconds, new_seconds):
    for step in steps:
        if step.get("action") in {"sleep", "wait"} and float(step.get("seconds", step.get("duration", 1))) == float(old_seconds):
            step["seconds"] = new_seconds


def _path_endswith(step, path):
    return str(step.get("path", "")).replace("\\", "/").endswith(path)


def _remove_sleep_after_previous_note(steps, previous_note_part):
    filtered = []
    previous = None
    removed = False
    for step in steps:
        if (
            not removed
            and previous is not None
            and step.get("action") in {"sleep", "wait"}
            and previous_note_part in str(previous.get("note", ""))
        ):
            removed = True
            previous = step
            continue
        filtered.append(step)
        previous = step
    return filtered


def _remove_delta_login_check_and_mode_steps(steps):
    # 预登录态检查与选择烽火模式依赖屏幕识别，误判会导致脚本中断；
    # 去掉后直接按固定顺序执行 QQ 登录和点击开始游戏，点空不算失败。
    removed_actions = {"ensure_delta_force_login_ready", "select_delta_force_fenghuo_mode"}
    return [step for step in steps if str(step.get("action", "")) not in removed_actions]


def _patch_fast_waits():
    original_entry = AutomationWorkflow.build_delta_force_entry_steps
    original_exit = AutomationWorkflow.build_delta_force_exit_steps
    original_qq_open = AutomationWorkflow.build_qq_open_account_list_steps
    original_qq_payload = AutomationWorkflow.build_qq_switch_account_payload
    original_station_open = AutomationWorkflow.build_delta_force_station_open_steps
    original_collect = AutomationWorkflow.build_delta_force_collect_steps
    original_produce = AutomationWorkflow.build_delta_force_produce_steps
    original_replenish = AutomationWorkflow.build_delta_force_replenish_steps
    original_delta_payload = AutomationWorkflow.build_delta_force_payload

    def build_delta_force_entry_steps_fast(self):
        steps = original_entry(self)
        steps = _remove_delta_login_check_and_mode_steps(steps)
        # Keep the shortened route, but leave enough time for slower wireless/UI transitions.
        _set_sleep_after_note(steps, "等待登录页加载", _wait_seconds("launch_game_load"))
        _set_sleep_after_previous_note(steps, "QQ 登录", _wait_seconds("after_qq_login"))
        _set_sleep_after_previous_note(steps, "第一层授权", _wait_seconds("after_first_authorization"))
        _set_sleep_after_previous_note(steps, "第二层授权", _wait_seconds("after_second_authorization"))
        _replace_sleep_after_previous_note_with_step(
            steps,
            "QQ 登录",
            {
                "action": "wait_foreground_package",
                "packages": ["com.tencent.mobileqq"],
                "timeout": _wait_seconds("qq_login_open_timeout"),
                "settle_seconds": _wait_seconds("after_qq_login"),
                "allow_dynamic_screen": True,
                "note": "等待 QQ 授权页打开",
            },
        )
        _replace_sleep_after_previous_note_with_step(
            steps,
            "第二层授权",
            {
                "action": "wait_foreground_package",
                "packages": ["com.tencent.tmgp.dfm"],
                "timeout": _wait_seconds("qq_login_return_timeout"),
                "settle_seconds": _wait_seconds("after_second_authorization"),
                "allow_dynamic_screen": True,
                "note": "等待 QQ 授权完成并返回三角洲",
            },
        )
        _set_sleep_after_previous_note(steps, "点击开始游戏", _wait_seconds("after_start_game"))
        _set_sleep_after_previous_note(steps, "特勤处", _wait_seconds("after_special_office"))
        steps = [step for step in steps if step.get("action") != "dismiss_delta_force_lobby_overlay"]
        for step in steps:
            if step.get("action") == "dismiss_delta_force_start_popup":
                step["wait_after"] = _wait_seconds("start_popup_check")
        return steps

    def build_delta_force_exit_steps_fast(self):
        steps = original_exit(self)
        _set_sleep_after_note(steps, "等待退出登录加载到登录页", _wait_seconds("login_page_after_logout"))
        _set_sleep_after_note(steps, "等待协议勾选生效", _wait_seconds("agreement_effect"))
        _set_sleep_after_previous_note(steps, "从特勤处返回大厅", _wait_seconds("back_to_lobby"))
        _set_sleep_after_previous_note(steps, "右上角设置", _wait_seconds("open_settings"))
        _set_sleep_after_previous_note(steps, "退出登录", _wait_seconds("logout_confirm"))
        _set_sleep_after_previous_note(steps, "关闭游戏进程", _wait_seconds("close_game_process"))
        steps = [
            step
            for step in steps
            if not _path_endswith(step, "captures/gui_logout_04_login_page.png")
            and "等级解锁预览" not in str(step.get("note", ""))
            and "等待预览页关闭" not in str(step.get("note", ""))
            and not _path_endswith(step, "captures/gui_production_after_exit.png")
        ]
        steps = _remove_sleep_after_previous_note(steps, "返回手机桌面")
        return steps

    def build_qq_open_account_list_steps_fast(self, profile=None):
        steps = original_qq_open(self, profile)
        _set_sleep_after_note(steps, "等待 QQ 首页加载", _wait_seconds("qq_home_load"))
        _set_sleep_after_note(steps, "等待安全提醒处理完成", _wait_seconds("qq_security"))
        _set_sleep_after_note(steps, "等待 QQ 设置页打开", _wait_seconds("qq_settings_open"))
        _set_sleep_after_note(steps, "等待账号与安全页打开", _wait_seconds("qq_account_security_open"))
        _set_sleep_after_previous_note(steps, "重置 QQ 当前页面", _wait_seconds("qq_reset"))
        return steps

    def build_qq_switch_account_payload_fast(self, include_select=True):
        payload = original_qq_payload(self, include_select)
        steps = payload.get("steps", [])
        if isinstance(steps, list):
            _set_sleep_after_note(steps, "等待 QQ 完成账号切换", _wait_seconds("qq_switch_complete"))
            _set_sleep_after_note(steps, "等待手机桌面显示", _wait_seconds("phone_home_show"))
        return payload

    def build_delta_force_station_open_steps_fast(self, station):
        steps = original_station_open(self, station)
        _replace_sleep_seconds(steps, 4, _wait_seconds("station_action"))
        return steps

    def build_delta_force_collect_steps_fast(self, station):
        steps = original_collect(self, station)
        _replace_sleep_seconds(steps, 4, _wait_seconds("station_action"))
        return steps

    def build_delta_force_produce_steps_fast(self, screenshot_suffix=None):
        steps = original_produce(self, screenshot_suffix)
        _replace_sleep_seconds(steps, 4, _wait_seconds("station_action"))
        return steps

    def build_delta_force_replenish_steps_fast(self, screenshot_prefix):
        steps = original_replenish(self, screenshot_prefix)
        _replace_sleep_seconds(steps, 4, _wait_seconds("station_action"))
        return steps

    def build_delta_force_payload_fast(self):
        payload = original_delta_payload(self)
        steps = payload.get("steps", [])
        if isinstance(steps, list):
            _replace_sleep_seconds(steps, 4, _wait_seconds("station_action"))
            _set_sleep_after_note(steps, "等待登录页加载", _wait_seconds("launch_game_load"))
            _set_sleep_after_previous_note(steps, "QQ 登录", _wait_seconds("after_qq_login"))
            _set_sleep_after_previous_note(steps, "第一层授权", _wait_seconds("after_first_authorization"))
            _set_sleep_after_previous_note(steps, "第二层授权", _wait_seconds("after_second_authorization"))
            _replace_sleep_after_previous_note_with_step(
                steps,
                "QQ 登录",
                {
                    "action": "wait_foreground_package",
                    "packages": ["com.tencent.mobileqq"],
                    "timeout": _wait_seconds("qq_login_open_timeout"),
                    "settle_seconds": _wait_seconds("after_qq_login"),
                    "allow_dynamic_screen": True,
                    "note": "等待 QQ 授权页打开",
                },
            )
            _replace_sleep_after_previous_note_with_step(
                steps,
                "第二层授权",
                {
                    "action": "wait_foreground_package",
                    "packages": ["com.tencent.tmgp.dfm"],
                    "timeout": _wait_seconds("qq_login_return_timeout"),
                    "settle_seconds": _wait_seconds("after_second_authorization"),
                    "allow_dynamic_screen": True,
                    "note": "等待 QQ 授权完成并返回三角洲",
                },
            )
            _set_sleep_after_previous_note(steps, "点击开始游戏", _wait_seconds("after_start_game"))
            _set_sleep_after_previous_note(steps, "特勤处", _wait_seconds("after_special_office"))
            _set_sleep_after_previous_note(steps, "从特勤处返回大厅", _wait_seconds("back_to_lobby"))
            _set_sleep_after_previous_note(steps, "右上角设置", _wait_seconds("open_settings"))
            _set_sleep_after_previous_note(steps, "退出登录", _wait_seconds("logout_confirm"))
            _set_sleep_after_previous_note(steps, "关闭游戏进程", _wait_seconds("close_game_process"))
            _set_sleep_after_note(steps, "等待退出登录加载到登录页", _wait_seconds("login_page_after_logout"))
            _set_sleep_after_note(steps, "等待协议勾选生效", _wait_seconds("agreement_effect"))
            for step in steps:
                if step.get("action") == "dismiss_delta_force_start_popup":
                    step["wait_after"] = _wait_seconds("start_popup_check")
        return payload

    AutomationWorkflow.build_delta_force_entry_steps = build_delta_force_entry_steps_fast
    AutomationWorkflow.build_delta_force_exit_steps = build_delta_force_exit_steps_fast
    AutomationWorkflow.build_qq_open_account_list_steps = build_qq_open_account_list_steps_fast
    AutomationWorkflow.build_qq_switch_account_payload = build_qq_switch_account_payload_fast
    AutomationWorkflow.build_delta_force_station_open_steps = build_delta_force_station_open_steps_fast
    AutomationWorkflow.build_delta_force_collect_steps = build_delta_force_collect_steps_fast
    AutomationWorkflow.build_delta_force_produce_steps = build_delta_force_produce_steps_fast
    AutomationWorkflow.build_delta_force_replenish_steps = build_delta_force_replenish_steps_fast
    AutomationWorkflow.build_delta_force_payload = build_delta_force_payload_fast


_patch_fast_waits()
del _patch_fast_waits


def _patch_fast_unattended_runner():
    def runner_without_step_checks(
        self,
        dry_run=False,
        pre_action_screenshots=False,
        stable_screen_before_action=False,
        verify_each_step=None,
    ):
        if verify_each_step is None:
            verify_each_step = False
        return ScriptRunner(
            self.client,
            base_dir=PROJECT_ROOT,
            log=self.log,
            dry_run=dry_run,
            should_stop=self.should_stop,
            log_countdown=True,
            pre_action_screenshots=pre_action_screenshots,
            stable_screen_before_action=stable_screen_before_action,
            verify_each_step=verify_each_step,
            manual_intervention=self.manual_intervention,
        )

    AutomationWorkflow._runner = runner_without_step_checks


_patch_fast_unattended_runner()
del _patch_fast_unattended_runner


def _patch_matching_device_profile_preference():
    original_qq = AutomationWorkflow.selected_qq_device_profile
    original_delta = AutomationWorkflow.selected_delta_force_profile

    def prefer_matching_profile(self, selected, kind):
        info = self.current_device_info()
        if info is None:
            return selected
        matched = matching_device_profile(info, "qq" if kind == "qq" else "delta_force")
        if not matched:
            return selected
        profile, source = matched
        if profile.get("key") == selected.get("key"):
            return selected
        label = profile.get("label") or profile.get("key") or "自动匹配坐标"
        self.log(f"当前手机与所选坐标不一致，已自动切换到 {label} ({source})")
        return profile

    def selected_qq_device_profile_safe(self):
        try:
            selected = original_qq(self)
        except Exception:
            selected = {}
        matched = prefer_matching_profile(self, selected, "qq")
        if matched:
            return matched
        return original_qq(self)

    def selected_delta_force_profile_safe(self):
        try:
            selected = original_delta(self)
        except Exception:
            selected = {}
        matched = prefer_matching_profile(self, selected, "delta_force")
        if matched:
            return matched
        return original_delta(self)

    AutomationWorkflow.selected_qq_device_profile = selected_qq_device_profile_safe
    AutomationWorkflow.selected_delta_force_profile = selected_delta_force_profile_safe


_patch_matching_device_profile_preference()
del _patch_matching_device_profile_preference


def _patch_self_healing_station_inspection():
    global delta_force_special_office_score
    import time as _t
    from .script_runner import delta_force_special_office_score as _sr_so_score

    delta_force_special_office_score = _sr_so_score

    def _safe_sleep(workflow, seconds):
        deadline = _t.monotonic() + float(seconds)
        while _t.monotonic() < deadline:
            if hasattr(workflow, "check_stop_requested"):
                workflow.check_stop_requested()
            _t.sleep(min(0.2, max(0.02, deadline - _t.monotonic())))

    original_inspect = AutomationWorkflow.inspect_delta_force_station

    def inspect_delta_force_station_self_healing(self, station, index, path_prefix, message):
        check_path = PROJECT_ROOT / "captures" / f"{path_prefix}_{index:02d}_{station['key']}.png"
        check_path.parent.mkdir(parents=True, exist_ok=True)
        self.log(f"{station['label']}: {message}")
        self.client.screenshot(check_path)
        self.check_stop_requested()

        # 检查是否在特勤处。如果在，直接通过，0 额外开销！
        for attempt in range(3):
            score = delta_force_special_office_score(check_path)
            if score is not None:
                break

            # 不在特勤处时的自愈页面诊断：
            # 1. 诊断：是否仍停留在工位制作详情页？
            detail_score = delta_force_station_detail_score(check_path)
            if detail_score is not None:
                self.log(f"{station['label']}: 自愈诊断 - 当前停在制作详情页，点击左上角返回特勤处 (自愈尝试 {attempt + 1}/2)")
                profile = self.selected_delta_force_profile() if hasattr(self, "selected_delta_force_profile") else {}
                detail_back = profile.get("detail_back_tap", {"x": 170, "y": 50})
                self.client.tap(int(detail_back.get("x", 170)), int(detail_back.get("y", 50)))
                _safe_sleep(self, 2.5)
                self.client.screenshot(check_path)
                continue

            # 2. 诊断：是否停留在奖励动画界面？
            reward_score = delta_force_reward_screen_score(check_path)
            if reward_score is not None:
                self.log(f"{station['label']}: 自愈诊断 - 当前停在奖励动画界面，点击空白处跳过 (自愈尝试 {attempt + 1}/2)")
                self.client.tap(1800, 820)
                _safe_sleep(self, 2.5)
                self.client.screenshot(check_path)
                continue

            # 3. 诊断：是否停留在大厅或有弹窗遮挡？
            self.log(f"{station['label']}: 自愈诊断 - 当前未在特勤处（可能在大厅或有弹窗），尝试关闭弹窗并重新进入特勤处 (自愈尝试 {attempt + 1}/2)")
            # 关闭弹窗与空白点击
            self.client.tap(2160, 80)
            _safe_sleep(self, 1.0)
            self.client.tap(1800, 820)
            _safe_sleep(self, 1.0)
            # 点击特勤处入口
            profile = self.selected_delta_force_profile() if hasattr(self, "selected_delta_force_profile") else {}
            spec_tap = profile.get("special_office_tap", {"x": 1020, "y": 1032})
            self.client.tap(int(spec_tap.get("x", 1020)), int(spec_tap.get("y", 1032)))
            _safe_sleep(self, 3.5)
            self.client.screenshot(check_path)
        else:
            # 重试 2 次后仍未在特勤处，安全报错
            if delta_force_station_detail_score(check_path):
                raise StepVerificationError(f"{station['label']}: 复查时仍停在制作详情页，未返回特勤处，截图: {check_path}")
            raise StepVerificationError(f"{station['label']}: 复查时未识别到三角洲特勤处，自愈恢复失败，停止以避免继续点错，截图: {check_path}")

        state = self.classify_delta_force_station(check_path, station)
        self.log(f"{station['label']}: {self.delta_force_state_label(state)}")
        return state

    AutomationWorkflow.inspect_delta_force_station = inspect_delta_force_station_self_healing


_patch_self_healing_station_inspection()
del _patch_self_healing_station_inspection

