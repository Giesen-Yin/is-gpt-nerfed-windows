# Upstream requirements review — Windows fork

## Scope and authority

Reviewed on 2026-10-09 by an independent `gpt-6.1-sol` reviewer (high reasoning), using the
requirements/standards review workflow. Baseline: upstream commit
`ff0d7c0c8fdc8713273b6570b1ada1838eaad84c` (original 0.5.3 development notes, README and MIT license).
Scope: all tracked changes relative to HEAD plus the new Windows source, tests and documentation.
This is our assessment against the original guide, not approval or certification by the upstream author.

## Findings and remediation in 0.5.8

| Priority / axis | Finding | Remediation |
| --- | --- | --- |
| P1 Standards | Source hooks could fail when Python was absent; bundled launchers propagated pre-main failure exit codes. | Shared PowerShell launcher exits 0 on absent runtime/script or failed startup; original JSON halt decisions are preserved. |
| P2 Standards | A stale nonempty PLUGIN_ROOT skipped the valid stable fallback. | Source launcher tries existing scripts in PLUGIN_ROOT, CLAUDE_PLUGIN_ROOT, NERFED_HOME/plugin and CODEX_HOME/is-gpt-nerfed/plugin in order. |
| P2 Requirements | READMEs lacked a grouped modification summary and changelog navigation. | Both now describe Added / Changed / Removed / Preserved, link the changelog, and identify the upstream baseline. |
| P2 Standards | Source installation advertised Python 3.9 while tomllib requires 3.11. | Both PowerShell installers check Python 3.11+ before invoking the backend; messages and doctor agree. |
| P3 Requirements | Portable README relative links had no target. | Package bilingual root READMEs, changelog and documentation with their relative paths; test copied documentation links. |
| P3 Standards | Known backend evidence/progress text remained English in the Chinese UI. | Exact known templates are translated at display time, with raw stored values and unknown external diagnostics unchanged. |

## Preserved contracts

- README.md and README.zh-CN.md direct macOS users to https://github.com/kiyoakii/is-gpt-nerfed.
- Original MIT notice, ModelTrace bank/provenance/license and calibrated prompts remain unchanged.
- Python/JavaScript scorer parity, confidence gates, ephemeral forks and refusal of model tool requests remain tested.
- Windows source, GUI/backend version, EXE properties and archive names share the plugin version.
- Installed user hooks/configuration were not modified by the review. Installation tests use disposable homes and no inference.

## Deliberate platform adaptations

Swift-specific resource bundles, Liquid Glass, macOS signing/notarization, Swift tests and build tools are removed
as requested for a Windows-only fork. Their exact font/resource conventions are not imposed mechanically on Tk.
The Windows UI provides its own bilingual labels, layout/resize/tray checks and native notification tests.

See [development requirements](DEVELOPMENT.md), [verification](VERIFICATION.md), and [changelog](../CHANGELOG.md).
Passing tests and a clean review do not establish the absence of all bugs or compatibility with every future Codex release.


## Re-review outcome

The same independent reviewer rechecked the corrected source on 2026-10-09 and closed all four required
findings and both recommendations. The reviewer independently reran the six PowerShell launcher tests and
three documentation tests; the primary agent's full offline suite passed all 80 tests. No new standards
finding was raised. The primary agent then rebuilt 0.5.8 and repeated isolated native installation and
portable runtime tests successfully. The upstream author has not been asked to approve this fork.
