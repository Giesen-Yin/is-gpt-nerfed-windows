# Windows 0.5.8 review verification

Verified on Windows x64, Python 3.13.13, native Codex 0.162.0-alpha.2, 2026-10-09.

- Independent requirements/standards review and re-review: four required findings and two recommendations closed; see [UPSTREAM_REVIEW.md](UPSTREAM_REVIEW.md).
- Full offline suite: **80 tests passed** (39.438 seconds), including JS scorer parity.
- New launcher cases: absent Python, stale source roots, custom homes, pre-main failure and valid JSON halt all passed in real PowerShell.
- Source and copied-release documentation navigation tests passed; bilingual modification summaries and changelog links are checked.
- Display-only translations preserve model/effort identifiers, raw records and unknown external diagnostics.
- Rebuilt GUI/backend/EXE properties/archive version: 0.5.8. Bilingual UI/resize/tray/plugin dialog and relocated no-Python bundle checks passed.
- Native registration, explicit trust, all five hooks after moving the portable app, same-version reinstall and unrelated config preservation passed in a disposable home, with no model inference.
- Windows may retain a temporary directory after the native test; any cleanup warning is recorded in the result instead of hiding an assertion failure.
- Real user hooks/configuration were not installed or changed by the review.

## Earlier verification records

# Windows 0.5.7 integration verification

Verified on Windows x64 with Python 3.13.13 and native Codex 0.162.0-alpha.2, 2026-10-09.

- 70 offline tests passed, including integration preflight, exact-definition trust filtering, registration-failure rollback and structured UI errors.
- Packaged GUI tests passed in both languages, including the new Codex plugin page, resizing, tray, settings and reports.
- Native installation was exercised only in a disposable CODEX_HOME without copied authentication.
- First-run status with no installed hooks reported the standalone manual-probe prerequisites available.
- All five hooks registered through the native CLI; explicit trust was verified through the app-server.
- The original portable directory was moved, Python was removed from PATH, and all five installed hooks still executed.
- Unicode, apostrophes, ampersands and spaces in paths and hook payloads were preserved. No hook errors or inference records were generated.
- Same-version reinstall succeeded; unrelated configuration survived.
- The test can report a cleanup warning if Windows retains an empty temporary directory after native process exit; it does not conceal installation or hook assertion failures.
- The actual user's installed hooks/config were not changed by these acceptance tests.

Run `windows/build.ps1 -IntegrationCodex <absolute-codex.exe>` to build and repeat the isolated native checks.
See `windows/test_installation.py` and `dist/integration-install-test.json` for the implementation/local result.

## Previous 0.5.6 verification

Local environment: Windows x64, Python 3.13.13, Tk 8.6, PyInstaller 6.21.0; verified 2026-10-09.

| Check | Result |
| --- | --- |
| Full offline Python suite | 63 tests passed; includes fake app-server integration and Node scorer parity |
| ModelTrace bank, provenance, MIT license | unchanged from the upstream baseline (newline-normalized comparison) |
| Session lock stress | four concurrent processes, 15 increments each, all 60 preserved |
| Nudge/automatic schedule | due reminder, cooldown, active/archived/deleted filtering and no inference in nudge mode covered |
| GUI | both languages, resized window, details/settings, tray startup, hide/restore and exit passed |
| Windows notification | actual PowerShell/WinRT command returned 0; visible delivery depends on notification policy |
| Portable EXE | relocated to a Chinese/space-containing path with Python removed from PATH; passed |
| Bundled config | true/false settings round trip in an isolated home passed |
| Read-only live snapshot | 14 current visible sessions; Codex executable found and hooks trusted |
| Version metadata | GUI/backend/manifest and both EXE file/product versions are 0.5.6 |
| Release licenses | MIT, notices, ModelTrace, CPython, Tcl/Tk, PyInstaller notices included |
| macOS code | Swift app, shell installers/build scripts and macOS updater removed |

No additional live model inference was requested for this verification. The full fake-server tests exercise
actual worker, retry, timeout, tool refusal, account, mismatch, passive scan and scheduling paths offline.
Existing installed hooks were not replaced; source/bundled code is distinct from the user's old plugin cache.

GitHub Actions is configured for Windows Python 3.11 and 3.13; hosted runs have not yet been executed because
this checkout has not been published as the user's Windows repository. Local checks do not guarantee absence
of every bug or compatibility with every future experimental app-server version.


## Publication preparation

The destination repository's existing copyright notice was combined with the preserved upstream notice in LICENSE. The full MIT permission text is unchanged. Generated archives, executables, logs, caches, environment files and user state are excluded from the source commit. Public source synchronization does not publish local test logs or a binary release.
