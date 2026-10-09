# Windows portable app

The Windows version follows `plugin/.codex-plugin/plugin.json` (currently 0.5.3-windows).
See [English README](../README.md) / [中文说明](../README.zh-CN.md) for operation, reminders and tray settings.
For macOS use https://github.com/kiyoakii/is-gpt-nerfed.

Source launch: double-click `start.cmd`, run `windows/start.ps1`, or `python windows/app.py`.
Portable launch: extract the complete ZIP and open `IsGPTNerfed.exe`; do not separate it from the backend and `_internal`.

Build on Windows with Python 3.11+ and `pip install -r windows/requirements-build.txt`, then run `windows/build.ps1`.
Outputs: `dist/releases/<version>/IsGPTNerfed/`, `dist/IsGPTNerfed-Windows-v<version>.zip`, and `.zip.sha256`.
The build checks manifest/backend version agreement and runs isolated bundle tests before packaging.
It does not install hooks, change PATH, register startup entries, or request elevation.

For a synthetic preview use `windows/start.ps1 -Demo` or `python windows/app.py --demo`.
Demo mode uses temporary state; inference and saving settings are disabled. Full source/binary smoke tests
also exercise tray hide/restore and require a Windows desktop session.

Use the application's **Codex plugin** page for installation/update, explicit trust, diagnostics and Codex executable selection.
The EXE deploys a separate per-user runtime, so installed hooks do not depend on system Python or the portable folder's location.
No installation/trust occurs until the user clicks the relevant action. Restart Codex to load newly installed hook definitions.
Legacy PowerShell installers remain available for source maintenance only.

For the native registration acceptance test, supply an explicit Codex executable:

```powershell
python windows/test_installation.py --bundle dist/releases/0.5.3-windows/IsGPTNerfed --codex C:/path/to/codex.exe
```

It registers/trusts only in a disposable CODEX_HOME, copies no auth, starts no inference, verifies all five hooks after moving
the original bundle with no Python on PATH, and checks reinstall/config preservation. Never substitute your real CODEX_HOME for this test.

Source hooks support python.exe or the py launcher and recover from stale plugin roots. Both launch paths fail open if the interpreter/script is missing or cannot start. See [change history](../CHANGELOG.md).

Window/taskbar/tray/EXE icons use `assets/chip.ico`, generated from the original `docs/face-ok.png` by `windows/build_icon.ps1`. The icon-refresh ZIP is published as a separate asset so the original release checksum remains valid.
