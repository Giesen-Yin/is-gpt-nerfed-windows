# Windows development requirements

This fork adapts the upstream development guide at commit
`ff0d7c0c8fdc8713273b6570b1ada1838eaad84c`. The original MIT notice is kept intact.
For macOS development, use https://github.com/kiyoakii/is-gpt-nerfed.

## Layout and scope

- `plugin/`: CLI (`scripts/nerfed`), stdio app-server client, ModelTrace scorer/bank/provenance, skills, manifest.
- `.agents/plugins/marketplace.json`: local plugin marketplace; keep source relative to this checkout.
- `windows/`: Tk UI, translations, Win32 tray, portable build specification and bundle validation.
- `install.ps1`, `uninstall.ps1`, `bin/nerfed.cmd`: Windows entry points.
- `tests/`: offline probe integration, scanner, scheduling, visibility, concurrency, UI and JS scorer parity.
- `LICENSE`, `THIRD_PARTY_NOTICES.md`: preserve upstream and third-party attribution in source and binaries.

This repository targets Windows 10/11 x64. The standard-library backend remains testable without a GUI;
no Swift code, DMG installer, macOS self-updater or macOS build toolchain belongs in this fork.
Use Python 3.11+ with Tk. Runtime GUI dependencies are Python standard library only.

## Preserved upstream contracts

1. Do not change ModelTrace's calibrated zh/en prompts or the bank as part of a platform port.
   Bank updates must update provenance and retain the MIT license; keep the Python/JS parity tests.
2. Localize at the presentation layer only. JSON keys, verdict codes, model IDs, reasoning efforts and
   saved evidence stay unchanged; do not translate real user titles or invent translations for external diagnostics.
3. Fork probes use a private app-server with `ephemeral: true`; refuse tool/approval requests. Do not
   substitute random-number generators or another model for actual probe answers.
4. Match is silent by default. A mismatch requires the existing probability, margin and sample-count gates.
   Invalid/unlisted samples are not downgrades. Preserve account tagging and older result history.
5. Hooks must fail open on unexpected errors. Log failures locally. The optional user-enabled halt remains explicit.
   Do not register/trust hooks in the user’s real home, edit global Codex config or call real inference in automated tests. Native installation acceptance tests must use a disposable CODEX_HOME without copied authentication.
6. Keep English and Chinese READMEs aligned. Document Windows limitations and distinguish this fork from upstream.
7. Versions come from the plugin manifest. Backend/client/skill, UI, EXE properties and ZIP must agree.
   Release tags use `vX.Y.Z`; binaries are unsigned unless a real signing certificate is supplied.

## Windows correctness

- Never use `os.kill(pid, 0)` on Windows; use a query-only process handle.
- Cross-process session locks must lock/unlock the same fixed byte. Test concurrent writers.
- Use argument arrays without `shell=True`, explicit UTF-8 JSON-RPC and hidden child consoles.
- Treat paths as paths: support spaces/non-ASCII text; do not launch Unix npm shims as executables.
- GUI work stays on the Tk thread. Queue worker/tray events; keep the window visible if tray setup fails.
- Background mode must offer an explicit Quit; nudge mode must not start inference.
- Deleted/archived records must not re-enter the default list through the historical ledger.
- Leave user ledger data intact on ordinary exit/uninstall; purge only when explicitly requested.
- Do not point the Windows updater at the upstream macOS release assets. Updates are manual here.

## Validation

```powershell
$env:PYTHONUTF8 = '1'
python -m unittest discover -s tests -v
python plugin/skills/is-gpt-nerfed/scripts/nerfed selftest
python windows/app.py --smoke-test
python -m pip install -r windows/requirements-build.txt
.\windows\build.ps1
```

`tests/windows_test_support.py` runs the fake Python server through the test interpreter on Windows,
including background-worker tests. This is test-only adaptation, never a production permission bypass.
Install Node.js to run parity tests; without Node, unittest reports the parity case skipped.
Smoke tests use an isolated home, synthetic data, both languages, a resized window, report/settings,
tray creation, hide/restore and clean exit. They require an interactive Windows desktop.
`windows/test_bundle.py --bundle <folder>` validates relocated binaries without Python on PATH,
using isolated config and no model requests. Add `--live` only for an explicitly wanted local account
read/app-server check; it still does not request inference. Build scripts run the isolated mode.

Commit source/tests/docs, not build directories, bytecode, logs, auth.json or local account data.
Keep real inference and notifications out of CI. A passing suite records tested behavior; it does not
establish that every Codex app-server version or all Windows security policies are compatible.


## In-app integration (0.5.7)

`windows_integration.py` stages a version/content-addressed private runtime and generated local marketplace, then uses
`codex plugin marketplace add` / `codex plugin add`. It uses `hooks/list` for definitions and `config/batchWrite` for explicit
trust, matching the upstream client. The official [app-server API overview](https://learn.chatgpt.com/docs/app-server#api-overview)
marks plugin/install as under development, so installation stays on the native CLI path.

Hook launch commands are fixed ASCII PowerShell EncodedCommand wrappers. Inside, literal paths are quoted, UTF-8 bytes
are forwarded through redirected streams, and the bundled backend owns hook semantics. Do not add a Python-on-PATH dependency.
Missing interpreters/scripts and unexpected launcher or backend startup failures exit 0. Intentional user-enabled halts remain expressed through the original stdout JSON denial, not a process error code. Trust only exact generated definitions.
Keep old runtime directories for in-flight hooks. Never rewrite an entire user config to roll back unrelated configuration.


## Source/release documentation checks

Keep the Added / Changed / Removed / Preserved summaries in both READMEs aligned and link CHANGELOG.md.
Release packaging copies bilingual READMEs, the changelog, documentation and required attribution files with relative paths intact.
`tests/test_repository_docs.py` checks links in both the checkout and a copied release-doc tree.
The upstream review and Windows-specific adaptations are recorded in [UPSTREAM_REVIEW.md](UPSTREAM_REVIEW.md).
