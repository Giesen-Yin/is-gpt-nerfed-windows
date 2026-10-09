---
name: is-gpt-nerfed
description: Check whether the current Codex session is silently being served by a different (usually cheaper) model than the one selected. Runs ModelTrace fingerprint probes in ephemeral forks of this thread, or answers the probe directly inside a /side conversation, and relays the Codex pet's verdict card. Use when the user invokes $is-gpt-nerfed, asks whether Codex downgraded, rerouted or dumbed down this session, or when a is-gpt-nerfed message says a probe is due or a verdict must be relayed. Not for benchmarking models or evaluating other tools.
metadata:
  version: 0.5.8
---

# is-gpt-nerfed — session integrity probe

`<skill-base-dir>/scripts/nerfed` is the only tool you need; `<skill-base-dir>` is the directory containing this SKILL.md, so resolve the absolute path first. Everything it records lives under `~/.codex/is-gpt-nerfed/` so the user can audit it; nothing leaves the machine.

## Run a probe in a normal session

1. Run `<nerfed> probe now`. It reads `CODEX_THREAD_ID` itself; pass `--thread <id>` only if the user named another thread.
2. It prints one of two things. Relay it verbatim, then continue with whatever the user asked.
   - A **pet card** with the verdict: the session was forked `ephemeral: true` (like `/side`), each fork answered a number challenge, and the answers were attributed with the ModelTrace fingerprint bank. Nothing landed in this thread's context.
   - A **"Queued"** notice: this shell runs inside Codex's network-less sandbox, so the probe starts right after the turn ends. The user gets a notification; the verdict is handed to you at the start of the next turn. Do not poll or wait.
3. Never generate the probe numbers yourself in a normal session, and never substitute another model, an API call or a subagent when `probe now` fails; report the printed error instead.

## Inside a `/side` conversation

`probe now` notices that a side conversation is ephemeral and prints a **CHALLENGE** instead: choose the requested integers yourself, write them literally into the printed `probe submit-numbers` command (no code, RNG, files, earlier samples or other models), run it, and repeat until the pet card appears. The numbers stay in this ephemeral side thread.

## Relaying verdicts and halts

- When hook context from is-gpt-nerfed says "tell the user verbatim", say it first, verbatim, then continue.
- If tools are being denied because `halt_on_mismatch` is on, stop working, summarise the verdict, and wait. Only run `<nerfed> resume --thread <id>` after the user explicitly asks to continue.
- Useful for the user: `<nerfed> report`, `<nerfed> explain <probe-id>`, `<nerfed> explain --method`, `<nerfed> config set frequency turns:8|30m|manual`, `<nerfed> config set halt_on_mismatch true`.

## Rules

- One probe at a time; do not rerun to get a nicer verdict.
- Do not edit files under `~/.codex/is-gpt-nerfed/`.
- Do not grade or interpret the numbers yourself; the script's verdict is the only verdict; do not argue with it.
