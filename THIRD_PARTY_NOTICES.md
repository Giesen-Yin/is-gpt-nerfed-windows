# Third-party notices

## is-gpt-nerfed (upstream)

- Source: https://github.com/kiyoakii/is-gpt-nerfed
- Source baseline: ff0d7c0c8fdc8713273b6570b1ada1838eaad84c (0.5.3 changelog revision).
- License: MIT; copyright (c) 2026 is-gpt-nerfed contributors. Full text: LICENSE.
- Windows changes include the Tk interface, tray/language preferences, process/locking adaptations,
  executable discovery, Windows packaging, installation and tests. macOS components were removed.
- The project is a modified fork. It does not claim upstream endorsement.
- The destination repository's existing Windows-fork copyright notice is also retained in LICENSE; the upstream notice and full MIT permission text remain present.

## ModelTrace

- Source: https://github.com/xqy2006/ModelTrace
- MIT. Full text: plugin/assets/modeltrace/LICENSE-ModelTrace.txt.
- Exact bank source, commit, SHA-256 and models: plugin/assets/modeltrace/provenance.json.
- The calibrated bank, probe prompt wording, scorer parity fixture and attribution methodology retain attribution.
- The JavaScript parity reference is retained in tests/fixtures/fingerprint-core.mjs.

## simple-term-menu (upstream dependency attribution)

- Source: https://github.com/IngoMeyer441/simple-term-menu
- MIT. Full text: plugin/skills/is-gpt-nerfed/scripts/vendor/LICENSE-simple-term-menu.txt.
- The Windows CLI uses a numbered selector; the Unix implementation was removed and its original license is retained for provenance.

## Other credits

- https://github.com/hanlinwenyuan/hlwy-ai-checker — credited by upstream for the random-number probing idea.

## Packaged runtime

The portable EXE contains CPython, Tcl/Tk and standard-library binary dependencies collected by PyInstaller.
These keep their original licenses; MIT applies to this project's code, not a relicensing of dependencies.
CPython's installed license and the Tcl/Tk license files are included under `_internal/licenses` when building.
PyInstaller is a build tool under GPL with its bootloader exception; the exception permits distribution of the
bundled program under its own license. Its license is included with the portable runtime notices.
No account tokens, user configuration or personal detection records belong in release archives.
