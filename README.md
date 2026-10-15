# ADB 手机自动化工具

这是一个 Python + ADB 的自动化操作工程，使用当前目录里的 `platform-tools\adb.exe`。源码运行需要安装 `requirements.txt` 里的 Python 依赖；便携版会把依赖一起打包。

## 快速开始

先在手机上开启“开发者选项”和“USB 调试”，连接 USB 后在手机上允许调试授权。

```powershell
python -m pip install -r requirements.txt
python main.py devices
python main.py size
python main.py screenshot -o screen-current.png
python main.py
```

`python main.py` 会启动桌面监控后台，也可以双击 `run_gui.bat`。如果需要旧的浏览器页面，运行 `python main.py web` 或双击 `run_web.bat`。
桌面监控后台可以选择设备、执行 QQ/三角洲/完整流程、截图、停止任务，并查看最近至少 30 行日志。
桌面监控后台、Web 控制台和命令行脚本/定时任务会把终端日志同步保存到 `log\时间_微秒_pid进程号.log`。日志文件会原子创建，多个进程同时启动不会抢同一个文件；超过 6 小时的旧 `.log` 会在后续启动时压缩成 `log\时间_previous_logs.zip`。

旧版 Tkinter 桌面控制台仍保留为备用入口：

```powershell
python main.py tk-gui
```

## 清理日志和截图

真实执行会持续保存过程截图到 `captures\`，建议定期清理。先预览：

```powershell
python main.py cleanup --dry-run
```

正式清理默认保留 14 天内截图、30 天内日志和日志归档：

```powershell
python main.py cleanup
```

也可以指定保留天数：

```powershell
python main.py cleanup --captures-days 7 --logs-days 30
```

源码仓库建议排除 `captures\`、`log\`、`build\`、`dist\`、`dist-build\`、`platform-tools\` 和 `scrcpy\`。当前 `.gitignore` 已按这个策略配置。便携版构建时只创建空的 `log\` 和 `captures\`，不会把历史截图打包进去。

## 发给别人使用

先在本机生成便携版：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1
```

如果提示缺少 Python 依赖，先执行：

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
```

也可以让脚本自动安装构建依赖：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_portable.ps1 -InstallBuildDeps
```

打包完成后，脚本会生成 `dist\ADBAutomation` 和最新的 `dist\ADBAutomation.zip`。把这个 zip 发给别人即可。对方解压后先双击 `00-device-check.bat` 做环境自检，通过后再双击 `01-start-gui.bat` 打开桌面监控后台。便携版自带 `platform-tools\adb.exe`，不要求对方电脑提前安装 Python 或 ADB。

## 新手机校准

当前已删除内置旧坐标预设，只保留 `device_profiles\xiaomi_2211133c.txt` 这一套已验证坐标。项目会在启动/刷新设备时读取手机型号，`auto` 模式只匹配 `device_profiles\*.txt` 里的同机型坐标；找不到会停止，避免用通用坐标误点。

已保留的坐标文件：

```text
device_profiles\xiaomi_2211133c.txt
```

如果新手机点不准，就给这台手机生成自定义 profile。推荐直接在 Web 控制台使用“新手机截图校准”：

1. 连接手机并在网页点“刷新”。
2. 选择 `QQ` 或 `三角洲`。
3. 在“页面阶段”里选择当前要识别的页面，例如 `三角洲登录页`。
4. 软件会询问当前手机是否已经在这个页面。
5. 如果是，点确认后程序会截图并自动分析该页坐标。
6. 如果不是，先把手机切到提示页面，再重新点自动分析。
7. 自动分析失败时，可以点“只截图/手动点选”作为兜底。
8. 全部坐标齐了以后点“保存坐标”。

保存后会生成 `device_profiles\<key>.txt`，之后这台手机会被自动识别，不需要改代码。

命令行触摸校准仍可作为备用。建议 QQ 和三角洲使用同一个 `--key`，这样会写进同一个 txt 文件。

QQ 校准示例：

```powershell
python main.py calibrate-profile qq --key my_phone --label "我的手机 QQ"
```

三角洲校准示例：

```powershell
python main.py calibrate-profile delta_force --key my_phone --label "我的手机三角洲"
```

命令会逐个提示你在手机上点击目标位置，完成后写入 `device_profiles\<key>.txt`。重新启动 Web 控制台后，自定义 profile 会出现在“QQ 坐标预设”和“三角洲坐标预设”下拉框里。

## 命令行用法

```powershell
python main.py tap 540 1200
python main.py swipe 540 1800 540 600 -d 350
python main.py text hello
python main.py key BACK
python main.py launch com.android.settings
python main.py script examples\open_settings.json
```

脚本支持 dry-run，只打印将要执行的动作，不实际点击手机：

```powershell
python main.py script --dry-run examples\qq_switch_account.json
```

## 定时任务

桌面监控后台可以直接启动/停止定时任务。时间模式支持两种：固定时间模式可填写 1-4 个每天固定运行的北京时间，例如 `02:00,08:00,14:00,20:00`；结束后倒计时模式会在每轮脚本结束后按设置的小时和分钟倒计时，例如填 `8` 小时 `30` 分钟时，08:32 结束就会 17:02 再运行。倒计时模式可填写“上次运行完毕时间”，例如 `2026-05-16 12:00`，中途 16:00 启动 8 小时间隔时会推算到 20:00 运行；每轮任务正常结束后会自动写回新的完毕时间。启动后会把当前 serial、完整流程轮数、QQ账号总数和勾选项保存到 `schedule_config.json`。

命令行后台运行：

```powershell
python main.py schedule
```

也可以直接运行 `run_schedule.bat`，方便放进 Windows 任务计划程序做开机自启。

只按配置立即运行一次，适合测试：

```powershell
python main.py schedule --once
```

多台设备同时连接时，加 `--serial`：

```powershell
python main.py --serial 4226635e screenshot
```

## JSON 脚本格式

脚本可以是包含 `steps` 的对象：

```json
{
  "steps": [
    {"action": "key", "key": "HOME"},
    {"action": "tap", "x": 540, "y": 1200},
    {"action": "sleep", "seconds": 1},
    {"action": "screenshot", "path": "screen-current.png"}
  ]
}
```

已支持的 action：

- `tap`: 字段 `x`, `y`
- `tap`: 也可以用横屏/竖屏当前显示尺寸百分比字段 `xp`, `yp`，例如 `{"action":"tap","xp":0.5,"yp":0.5}`
- `tap_qq_account_index`: 字段 `index`，在 QQ 账号与安全页动态识别账号管理列表并点击第 N 个账号
- `tap_qq_account_last`: 在 QQ 账号与安全页动态识别账号管理列表；可用 `total_accounts` 指定 QQ 总账号数 1-8，并点击第 `total_accounts - 1` 个可切换账号。当前登录账号不参与切换。
- `dismiss_qq_security_prompt`: 如果当前 QQ 弹出“安全提醒”，点击“取消”
- `finish_qq_switch_to_home`: 处理 QQ 安全提醒，并按当前页面状态返回手机桌面
- `dismiss_delta_force_start_popup`: 三角洲点击开始游戏后截图检查活动弹窗，检测到右上角 `X` 才点击关闭
- `swipe`: 字段 `x1`, `y1`, `x2`, `y2`, 可选 `duration_ms`
- `swipe`: 也可以用百分比字段 `x1p`, `y1p`, `x2p`, `y2p`
- `text`: 字段 `value`
- `key`: 字段 `key`，例如 `BACK`, `HOME`, `RECENTS`, `WAKEUP`
- `launch`: 字段 `package`
- `activity`: 字段 `component`，例如 `com.xxx/.MainActivity`
- `url`: 字段 `value`
- `shell`: 字段 `command`
- `screenshot`: 可选字段 `path`
- `sleep`: 字段 `seconds`
- `repeat`: 字段 `times`, `steps`，可选 `interval`
- `log`: 字段 `message`

## 三角洲行动 QQ 登录和特勤处脚本

设备中识别到三角洲行动包名为 `com.tencent.tmgp.dfm`，QQ 包名为 `com.tencent.mobileqq`。
旧版静态三角洲示例脚本已删除；现在请在桌面监控后台或 Web 控制台里按当前勾选项直接预演或执行：

```powershell
python main.py web
```

完整多账号流程在 GUI 的“完整流程”页执行。可设置 QQ 总账号数 1-8，总数=当前登录账号+可切换账号；脚本会点击第 `总账号数 - 1` 个可切换账号。要让所有账号都跑一遍，完整流程轮数通常设置为 QQ 总账号数。三角洲点击开始游戏后会检查活动弹窗，检测到才点击右上角 `X`；若没有检测到也会在日志里提示并继续进入特勤处。三角洲智能流程会在每次操作前截图并等待画面稳定，登录页/开始游戏前的动态 CG 段只检查截图有效、未锁屏和非黑屏，不等待稳定帧；处理每个制作台后复查，全部勾选制作台完成后还会整体复查一次。若打开 QQ 后或切换账号后弹出“安全提醒”，脚本会点击“取消”，再继续切号或按当前页面状态返回桌面。

真实执行时，脚本执行器会为每一步保存校验截图到 `captures\step_checks\时间\`，并检查截图可读、手机未锁屏、等待后页面不是黑屏；点击/滑动类步骤还会检查执行后画面是否变化。校验失败会报错并停止当前脚本。

三角洲模块现在只使用 `device_profiles\xiaomi_2211133c.txt` 里的已验证坐标。建议先验证当前横屏尺寸，然后在 Web 控制台里点“三角洲”并勾选“预演模式”：

```powershell
python main.py display-size
```

首次通常需要校准这些点位：

- QQ 登录按钮：脚本里的 `xp: 0.6, yp: 0.86`
- QQ 授权按钮：脚本里的 `xp: 0.5, yp: 0.86`
- 进入游戏按钮：脚本里的 `xp: 0.86, yp: 0.88`
- 特勤处入口：脚本里的 `xp: 0.82, yp: 0.91`
- 特勤处内的一键收取/制作按钮：脚本底部几个 `xp: 0.86/0.76, yp: 0.82`

校准方法：

```powershell
python main.py
```

旧版 Tkinter 控制台里仍可点“获取截图”，保持“点击截图时只记录坐标”勾选，点击截图上的目标按钮。日志会显示 `x/y` 和 `xp/yp`，按需要更新内置坐标。

如果电脑 GUI 不能点击截图，可以直接用 ADB 监听手机触摸来校准：

```powershell
python main.py calibrate-touch
```

命令启动后，直接在手机屏幕上点一次目标按钮，终端会输出：

```text
x=1440, y=929, xp=0.6000, yp=0.8600
JSON: {"action":"tap","xp":0.6000,"yp":0.8600}
```

需要连续记录多个点：

```powershell
python main.py calibrate-touch -n 5
```

这种方式会真实点击手机，适合按游戏流程一边推进一边记录点位。

## 在电脑上录制完整流程

如果要完整录制三角洲行动流程，仍可使用旧版 Tkinter 控制台左侧的“录制流程”：

```powershell
python main.py tk-gui
```

推荐操作顺序：

1. 取消勾选“点击截图时只记录坐标”。
2. 勾选“点击后自动截图”。
3. 勾选“记录截图点击”和“自动记录等待时间”。
4. 在“输入与应用”的包名里填 `com.tencent.tmgp.dfm`。
5. 点“开始录制”。
6. 点“启动包名”，等待游戏打开。
7. 点“获取截图”。
8. 在电脑截图上按真实流程点击：QQ 登录、QQ 授权、进入游戏、关闭弹窗、特勤处、收取、制作确认等。
9. 每次点击后等自动截图刷新，再点下一步。
10. 需要额外等待时，在“等待秒数”里填秒数，点“添加等待”。
11. 流程完成后点“停止录制”，再点“保存录制脚本”。

默认会保存到：

```powershell
examples\delta_force_recorded.json
```

保存后先检查 dry-run：

```powershell
python main.py script --dry-run examples\delta_force_recorded.json
```

确认后执行：

```powershell
python main.py script examples\delta_force_recorded.json
```

## 常见问题

- `unauthorized`: 看手机屏幕，允许 USB 调试授权。
- `offline`: 重新插拔 USB，或执行 `platform-tools\adb.exe kill-server` 后再试。
- 中文输入不稳定：`adb shell input text` 对中文支持有限，后续可以改成剪贴板或输入法方案。
