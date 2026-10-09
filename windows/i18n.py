"""Presentation-only translations. Model IDs, external diagnostics and stored evidence stay unchanged."""
STRINGS = {
 'settings': ('设置', 'Settings'), 'refresh': ('刷新', 'Refresh'), 'quit': ('退出', 'Quit'),
 'open': ('打开窗口', 'Open window'), 'search': ('搜索', 'Search'),
 'recent': ('近期会话 · 近 48 小时', 'Recent sessions · last 48 hours'),
 'loading': ('正在读取最近会话…', 'Loading recent sessions…'), 'empty': ('没有符合条件的近期会话', 'No matching recent sessions'),
 'fresh': ('新会话', 'Fresh session'), 'fresh_probe': ('检测新会话', 'Probe fresh session'),
 'probe': ('检测', 'Probe'), 'retry': ('重试', 'Retry'), 'running': ('检测中', 'Probing'),
 'no_probe': ('尚未检测', 'Not probed yet'), 'collecting': ('正在收集回答', 'Collecting answers'),
 'unverified': ('未验证', 'Unverified'), 'other_account': ('来自其他账户的结果', 'Result from another account'),
 'match': ('匹配', 'Match'), 'suspicious': ('可疑', 'Suspicious'), 'unlisted': ('模型未收录', 'Unlisted model'),
 'invalid': ('检测失败', 'Invalid'), 'downgrade': ('降配', 'Downgrade'), 'upgrade': ('升配', 'Upgrade'), 'rerouted': ('重路由', 'Rerouted'),
 'no_sample': ('没有可用样本', 'No usable sample'), 'no_anomaly': ('未发现异常记录', 'No anomalies recorded'),
 'down_count': ('{n} 个会话降配', '{n} downgraded sessions'), 'warn_count': ('{n} 个会话可疑', '{n} suspicious sessions'),
 'summary': ('{warn} 个可疑 · {up} 个升配 · {running} 个检测中', '{warn} suspicious · {up} upgraded · {running} probing'),
 'last_hook': ('最近回调', 'Last hook'), 'none': ('无', 'None'), 'default': ('默认', 'Default'), 'unknown_model': ('未知模型', 'Unknown model'),
 'turns': ('{n} 轮', '{n} turns'), 'archived': ('已归档', 'Archived'),
 'unavailable': ('已删除或不在当前数据库中 · 仅查看历史记录', 'Deleted or unavailable · history only'),
 'halted': ('已暂停：需在原会话中明确恢复', 'Halted: explicitly resume in the original session'),
 'last_failed': ('上次尝试失败 · 点击查看详情', 'Last attempt failed · click for details'),
 'help': ('点击会话查看详情。每次检测通常请求 3 份短回答，使用当前 Codex 账户额度。', 'Click a session for details. Each probe normally requests 3 short answers using your Codex quota.'),
 'started': ('检测已启动。关闭窗口不会终止已启动的检测。', 'Probe started. Closing the window will not stop an active probe.'),
 'finished': ('检测进程已结束，请查看会话结果。', 'Probe process finished; see the session result.'),
 'saved': ('设置已保存', 'Settings saved'), 'save_failed': ('设置保存失败', 'Could not save settings'),
 'read_failed': ('读取失败（保留上次结果）', 'Read failed (showing previous results)'), 'failed': ('操作失败', 'Operation failed'),
 'copy': ('复制报告', 'Copy report'), 'no_report': ('尚无报告，请先检测。', 'No report yet. Run a probe first.'),
 'language': ('界面语言', 'Interface language'), 'frequency': ('会话检测间隔', 'Session probe interval'),
 'fresh_frequency': ('新会话自动检测间隔', 'Fresh-session probe interval'), 'mode': ('到期时的行为', 'When a probe is due'),
 'auto': ('自动检测', 'Probe automatically'), 'nudge': ('仅提醒，不自动检测', 'Remind only; no automatic probe'),
 'manual': ('仅手动', 'Manual only'), 'every8': ('每 8 轮', 'Every 8 turns'),
 '15m': ('每 15 分钟', 'Every 15 minutes'), '30m': ('每 30 分钟', 'Every 30 minutes'), '1h': ('每小时', 'Hourly'),
 'notify': ('显示检测通知', 'Show notifications'), 'notify_on_ok': ('匹配时也通知', 'Notify on a match too'),
 'sound': ('异常时提示音', 'Play a sound on mismatch'), 'hide_titles': ('隐藏会话标题与账户', 'Hide session titles and account'),
 'show_inactive_threads': ('显示已归档或已删除会话', 'Show archived or deleted sessions'),
 'background': ('关闭应用后驻留后台', 'Keep running in background when closed'),
 'save': ('保存', 'Save'), 'test_notification': ('测试通知', 'Test notification'),
 'test_notice': ('这是一条测试提醒，不代表检测结果。', 'This is a test notification, not a probe verdict.'),
 'notice_sent': ('已请求 Windows 显示测试通知；勿扰模式可能隐藏通知。', 'Test notification requested. Do Not Disturb may suppress it.'),
 'tray_error': ('托盘不可用，窗口将保持打开', 'Tray unavailable; keeping the window open'),
 'demo': ('演示数据', 'Demo data'), 'due': ('已到检测时间', 'Probe due'),
 'reminder': ('会话已到检测时间，点击“检测”开始。', 'A session is due. Click Probe to start.'),
 'report': ('检测报告', 'Probe report'), 'evidence': ('检测证据', 'Evidence'),
 'history': ('检测历史', 'Probe history'), 'error': ('错误详情（原始内容）', 'Error details (original text)'),
 'schedule_hint': ('仅提醒模式会关闭新会话自动检测，不消耗模型额度。后台驻留时继续调度。', 'Remind-only also sets fresh-session probing to manual. Enabled schedules continue in the tray.'),
 'integration': ('Codex 插件', 'Codex plugin'),
 'integration_hint': ('未安装或未信任 hooks；仍可手动检测。点击配置插件。', 'Hooks are missing or untrusted; manual probes still work. Click to set up.'),
 'integration_intro': ('在应用内安装或更新这 5 个 hooks：SessionStart、UserPromptSubmit、PreToolUse、Stop、SessionEnd。安装后请重启 Codex；手动检测不要求安装插件。', 'Install/update the five hooks here: SessionStart, UserPromptSubmit, PreToolUse, Stop, SessionEnd. Restart Codex afterwards. Manual probes do not require the plugin.'),
 'install_hooks': ('安装 / 更新 hooks', 'Install / update hooks'),
 'trust_hooks': ('信任已安装 hooks', 'Trust installed hooks'),
 'trust_with_install': ('安装后同时信任本插件的 5 个 hooks', 'Also trust this plugin’s five hooks after installation'),
 'diagnose': ('运行诊断', 'Run diagnostics'),
 'choose_codex': ('选择 codex.exe', 'Choose codex.exe'),
 'integration_busy': ('正在处理，请稍候；不要关闭安装进程…', 'Working; please wait for the installation to finish…'),
 'integration_done': ('操作完成。安装或信任后，请重启 Codex。', 'Operation complete. Restart Codex after installation or trust.'),
 'integration_ready': ('插件已安装并信任', 'Plugin installed and trusted'),
 'integration_pending': ('插件尚未就绪，请查看诊断', 'Plugin not ready; see diagnostics'),
 'integration_runtime': ('Hooks 运行时', 'Hooks runtime'),
 'integration_manual': ('手动检测可用', 'Manual probing available'),
 'integration_installed': ('插件已启用', 'Plugin enabled'),
 'integration_restart': ('需要重启 Codex 加载新版 hooks', 'Restart Codex to load the new hooks'),
 'integration_storage': ('安装会在本地检测目录保存独立运行时，关闭或移动前端后仍可运行；无需安装 Python。不会安装 Codex 本体。', 'Installation saves a standalone runtime in the local detection directory. It keeps working after the GUI is closed or moved; Python is not required. This does not install Codex itself.'),
 'integration_error': ('操作失败；下方保留完整诊断。', 'Operation failed; diagnostics are shown below.'),
 'integration_copy': ('复制诊断', 'Copy diagnostics'),
 'yes': ('是', 'Yes'), 'no': ('否', 'No'),

 'integration_storage_source': ('源码模式会保存插件副本并使用当前 Python；便携 EXE 模式会部署独立运行时，不依赖系统 Python。', 'Source mode saves a plugin copy and uses the current Python. Portable EXE mode deploys a standalone runtime without system Python.'),

}

def tr(language, key, **values):
    return STRINGS[key][1 if language == 'en' else 0].format(**values)


# Exact presentation templates only. Never run this on real session titles or arbitrary errors.
def backend_text(text, language):
    import re
    text = str(text or '')
    if language != 'zh':
        return text
    exact = {
        'waiting for the current turn to finish': '等待当前轮次完成',
        'Hidden model ran a turn': '隐藏模型执行了一轮对话',
        'trusted': '已信任', 'untrusted': '未信任', 'missing': '未安装', 'unknown': '未知',
        'no account': '未登录账户', 'account hidden': '账户已隐藏',
    }
    if text in exact:
        return exact[text]
    age = re.fullmatch(r'(\d+)(s|m|h|d) ago', text)
    if age:
        return age[1] + {'s':'秒','m':'分钟','h':'小时','d':'天'}[age[2]] + '前'
    templates = [
        (r'Upgraded: (\S+) → (\S+) · via settings', '已升配：{} → {} · 通过设置'),
        (r'Upgraded: (\S+) → (\S+)', '已升配：{} → {}'),
        (r'Silent model change: (\S+) → (\S+)', '模型已悄悄切换：{} → {}'),
        (r'Silent effort change: (\S+) → (\S+)', '推理级别已悄悄切换：{} → {}'),
        (r'Settings: model (\S+) → (\S+) · was that you\?', '模型设置：{} → {} · 是你更改的吗？'),
        (r'Settings: effort (\S+) → (\S+) · was that you\?', '推理级别设置：{} → {} · 是你更改的吗？'),
        (r'Codex switched model (\S+) → (\S+) at the usage limit \((\d+)%\)', '达到用量限制（{2}%）时 Codex 将模型从 {0} 切换为 {1}'),
        (r'Codex switched effort (\S+) → (\S+) at the usage limit \((\d+)%\)', '达到用量限制（{2}%）时 Codex 将推理级别从 {0} 切换为 {1}'),
        (r'Hidden model ran: (\S+)', '隐藏模型执行：{}'),
        (r'Context window (\S+) → (\S+)', '上下文窗口：{} → {}'),
        (r'Tier (\S+) → (\S+)', '服务等级：{} → {}'),
    ]
    for pattern, translated in templates:
        match = re.fullmatch(pattern, text)
        if match:
            return translated.format(*match.groups())
    return text
