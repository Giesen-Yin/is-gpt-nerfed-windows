# Is GPT nerfed? — Windows

简体中文 · [English](README.md)

Windows 仓库：[Giesen-Yin/Is-GPT-Nerfed-ForWindows](https://github.com/Giesen-Yin/Is-GPT-Nerfed-ForWindows)。

本仓库是 [kiyoakii/is-gpt-nerfed](https://github.com/kiyoakii/is-gpt-nerfed) 的 Windows 专用派生版本，保留原版 Python 检测核心与 ModelTrace 归因逻辑。
**mac 系统请找原仓库：[kiyoakii/is-gpt-nerfed](https://github.com/kiyoakii/is-gpt-nerfed)。** 本仓库不再分发或维护 Swift 应用、DMG 安装器和 macOS 更新器。这是经过修改的 Windows 分支，并非完全相同的镜像，也不是上游官方 Windows 发行版。

## 相对原仓库的改动类型

| 类型 | Windows 分支改动 |
| --- | --- |
| 新增 Added | Windows EXE/Tk 界面、中英切换、托盘驻留、应用内 hooks 安装/信任/诊断、隔离 Windows 测试。 |
| 修改 Changed | Windows 进程发现/锁/通知、UTF-8 hook 启动器与源码回退、源码 Python 3.11+ 要求、便携打包与手动更新。 |
| 移除 Removed | Swift/macOS 应用、DMG 与 shell 安装器、macOS 自更新器、未使用的 Unix 终端菜单实现。 |
| 保留 Preserved | 原 MIT 声明、上游署名、ModelTrace 指纹库/来源记录/校准提示词、评分器与 JavaScript 一致性测试。 |

上游基线为提交 [`ff0d7c0c8fdc8713273b6570b1ada1838eaad84c`](https://github.com/kiyoakii/is-gpt-nerfed/commit/ff0d7c0c8fdc8713273b6570b1ada1838eaad84c)。
详见 [Windows 更新日志及保留的上游历史](CHANGELOG.md)、[开发要求](docs/DEVELOPMENT.md)、[原规范审核记录](docs/UPSTREAM_REVIEW.md)。Windows 版本号仅表示本分支版本，不表示获得原作者认可。

![Windows app — synthetic demo](docs/windows-panel.png)

## 在 Windows 上运行

要求 Windows 10/11 x64，以及已安装、已登录且支持插件 hooks 的 Codex。下载本 Windows 分支发布的 ZIP，**完整解压文件夹**，双击 `IsGPTNerfed.exe`。保留同目录的 `nerfed-backend.exe` 和 `_internal`。便携应用无需另装 Python、无需管理员权限。未签名 EXE 可能被 SmartScreen 或组织策略阻止；不要为此关闭安全防护。

从源码运行需 Python 3.11+（含 Tk）：

```powershell
.\windows\start.ps1
# 或：python windows/app.py
```

窗口从本地 Codex 数据库读取近期对话。搜索标题、模型或 ID，点击“检测”即可通过临时分叉测试选中的对话，无需在聊天中手动调用技能。点击卡片查看报告。默认隐藏已归档和已删除会话，可在设置中开启显示保留的历史记录；已删除/不可用会话不能再次检测。

## 设置与后台运行

- 设置中切换**简体中文 / English**，保存后刷新界面。用户标题、模型 ID、推理级别标识、已存证据与外部诊断保留原文。
- 拖动标题栏移动窗口、拖动边缘调整大小；长会话文字自动换行，列表可滚动。
- **关闭应用后驻留后台**默认关闭。开启后，关闭窗口会隐藏到 Windows 通知区域；点击托盘图标恢复，右键选择“打开窗口 / 设置 / 退出”。托盘创建失败会保持窗口可见。“退出”结束界面，但不取消已启动的检测。
- **自动检测**模式会启动到期检测；窗口打开或驻留后台期间，每分钟检查一次调度，hooks 也会在对话轮次结束后检查。**仅提醒**模式显示到期提醒，不主动请求模型回答。界面提醒对同一会话限每 15 分钟一次。保存“仅提醒”还会把新会话间隔设为手动，避免旧缓存 hooks 自动发起新会话检测。
- 会话间隔默认 `30m`，可选 `manual`、时间间隔或 `turns:8`。新会话检测默认 `manual`，启用后按时间间隔执行；界面心跳对新会话的自动推理同样要求“自动检测”模式。
- 可设置通知、匹配时也通知、声音。“测试通知”发送测试文案，不代表检测结果；遵循通知开关及 Windows 通知/勿扰设置。

一次常规检测请求三份短回答，消耗当前账户额度；超时和传输重试可能增加请求。匹配默认不提醒。结果是对库内模型的统计归因，**不能证明服务器实际使用了哪套权重**。无结果、失败、未收录都不代表降配；Codex 内的设置变化可能需要用户确认后才能解释。

## 在应用内安装和诊断 Codex hooks

EXE 可直接读取会话和手动检测，**不依赖预先安装 hooks**。hooks 增加每轮被动扫描、对话内提醒，以及前端退出后由 Codex 对话事件触发的调度（不是独立 Windows 定时服务）。

1. 打开 EXE，点击 **Codex 插件**；未安装或未信任时，首页也会显示入口。
2. 点击 **运行诊断** 查看 Codex 程序、指纹库、插件启用状态、5 个 hooks 的信任状态和独立运行时。
3. 点击 **安装 / 更新 hooks**。需要一次完成时，可明确勾选“安装后同时信任本插件的 5 个 hooks”；否则安装后点击 **信任已安装 hooks**。
4. 重启 Codex，再发送一条消息并运行诊断，确认实际 hook 事件已出现。
5. 若找不到 Codex，使用 **选择 codex.exe** 指定路径，再安装；应用不会代为安装 Codex 本体。

以上流程**不需要单独运行 install.ps1，也不需要系统 Python**。应用把独立运行时和本地 marketplace 保存到 `NERFED_HOME/windows-runtime/<版本-内容哈希>/`，通过 Codex CLI 注册；因此关闭、移动或删除便携前端文件夹不会让已安装 hooks 丢失程序。旧运行时保留，避免中断尚未重载的 hooks。

安装先验证 Codex/app-server，失败时展示原始诊断；发生注册失败会尝试用 Codex CLI 恢复本插件原注册，不覆盖其他 Codex 设置。仅信任与本次生成的 5 个命令完全匹配的 hooks。没有后台静默安装或自动信任。

`install.ps1` / `uninstall.ps1` 仍保留为源码维护入口。源码模式的安装需要 Python；便携 EXE 的安装不需要。GUI 更新不会自动替换用户已安装的 hooks；升级后可再次点击应用内“安装 / 更新 hooks”。

## 数据与更新

从 `CODEX_HOME`（默认 `%USERPROFILE%\.codex`）读取 Codex 状态。结果和设置写入 `NERFED_HOME`（默认 `CODEX_HOME\is-gpt-nerfed`），其中 `windows-ui.json` 保存语言与后台驻留偏好。读取认证信息仅用于账户哈希和掩码标签。应用不上传本地记录；检测本身是正常的 Codex 推理请求。关闭应用不删除数据。

自动更新已禁用，避免误装上游 macOS 资源。升级时退出应用，再手动替换 Windows 文件夹。GUI、后端、EXE 文件/产品版本和 ZIP 名称统一跟随插件清单版本。详见 [Windows 使用与构建](windows/README.md)、[开发要求](docs/DEVELOPMENT.md)。

## 协议与来源

项目代码及 Windows 修改继续使用 **MIT**，在 [LICENSE](LICENSE) 中完整保留原版权声明。[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 记录上游、ModelTrace 和打包组件来源。运行时依赖保留各自协议，本项目不对它们重新授权。保留 [ModelTrace 来源记录](plugin/assets/modeltrace/provenance.json)、指纹库和校准提示词。
