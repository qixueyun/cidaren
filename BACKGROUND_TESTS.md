# 后台操作实测记录（2026-11-01）

环境：本机已有微信、Edge、Windows .NET Framework；未安装额外软件，未使用手机。只对菜单及其遮罩执行可恢复测试，没有提交答案。

| 方法 | 实测 | 结论 |
|---|---|---|
| PrintWindow窗口截图 | 微信被遮挡时可读取题目 | 可用，但最小化暂停 |
| PostMessage，宿主及D3D子窗口 | 返回发送成功，菜单不响应 | 未通过 |
| SendMessageTimeout同步输入，宿主 | 前台不变，菜单未关闭 | 未通过 |
| SendMessageTimeout同步输入，D3D子窗口 | 前台不变，菜单未关闭 | 未通过 |
| 临时发送激活/焦点状态消息后同步输入 | 前台与鼠标不变，菜单未关闭；已撤销状态消息 | 未通过 |
| MSAA accDoDefaultAction | 返回成功，前台和鼠标不变；菜单界面未变化 | 未通过，不能以接口返回成功作为动作成功 |
| UI Automation InvokePattern | 实际打开、关闭菜单，截图验证；不移动鼠标，但改变前台焦点 | 动作可用，不满足后台并行要求 |
| 已有浏览器独立网页 | 发现真实H5练习地址，但独立访问跳到微信授权；浏览器安全策略阻止观察该授权页面 | 已停止此路径，不使用其他接口绕过 |
| 当前进程已有本地调试接口 | 未观察到调试启动参数或本地监听端口 | 没有可直接复用的现成接口 |

测试菜单已通过InvokePattern关闭，恢复原题页面。后台答题继续禁用，不自动回退到抢占鼠标或前台的方式。

复现工具：`inspect_uia.cs`、`uia_invoke.cs`、`inspect_msaa.cs`、`msaa_invoke.cs`、`probe_message_modes.py`。探针仅针对当时观察到的窗口、尺寸和菜单，不能盲目换坐标运行。

相关截图：

- `runs/20261101-000246/background-probe.png`：UIA打开菜单。
- `runs/20261101-000736/background-probe.png`：MSAA调用后，菜单仍在。
- `runs/20261101-001042/message-activation-sync.png`：临时状态消息加同步点击后，菜单仍在。
- `runs/20261101-001125/background-probe.png`：UIA关闭菜单后恢复原题。

Windows接口参考：

- https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controlpatternsoverview
- https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.invokepattern.invoke
- https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-printwindow

以上是当前版本和机器上的实验结果，不代表所有微信版本都无法后台控制。

## 已选择的运行方案

用户后续选择使用UI Automation直接调用。已接入 `uia_window.py` 和 `--uia` 模式；`start.ps1`、`start-uia.ps1` 均以此模式启动。窗口截图后只在目标微信窗口内寻找覆盖相应位置的最小可调用控件，并调用InvokePattern，不模拟鼠标点击。

实测已完成：菜单打开和关闭；一道句意题首次答错、排除错误选项、第二次答对、记录反馈并点击继续。该模式会激活微信，仍不满足无干扰后台运行条件。
