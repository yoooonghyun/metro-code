---
name: diagnose
description: >-
  Diagnose whether the Claude Code harness behaves as intended by comparing
  collected telemetry (what actually happened) against the current project's
  configuration (what should happen). Use for "diagnose my setup", "is my
  harness working as intended?", "하네스 진단", "설정이 의도대로 동작하는지
  분석해줘", "사용 패턴 분석".
---

# Telemetro — diagnose (intent vs. behavior)

Compare **what the telemetry says actually happened** with **what the harness
configuration says should happen**, and report divergences with concrete fixes.
The scripts only fetch data — you (Claude) do the analysis.

## Steps

1. Pull the usage digest from the monitoring stack (default: last 7 days):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/query.py" summary --hours 168
   ```

   If the stack is unreachable, point the user to `/telemetro:init` and stop. If
   the digest is empty, telemetry hasn't flowed yet — remind them it needs
   `init` + a restart, and that richer tool/skill data needs the
   `OTEL_LOG_TOOL_DETAILS=1` env (installed by current telemetro; older installs
   should re-run `otel.py install`).

2. Enumerate the **intent** side of the comparison:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inventory.py"
   ```

   (declared skills, subagents, MCP servers — memory-type ones flagged — and
   CLAUDE.md tiers with staleness). Then read the contents behind it:
   - project `CLAUDE.md` (and `~/.claude/CLAUDE.md` if present) — the stated
     rules and conventions
   - `.claude/settings.json` + `~/.claude/settings.json` — `permissions`
     (allow/deny/ask) and `hooks`

3. Write the diagnosis, grounded strictly in the digest numbers. Structure:

   **✅ Working as intended** — guardrails that actually fired:
   - `tool_decision` rejects with source `config`/`hook` = deny rules and hooks
     doing their job. Name which rule/hook likely fired.

   **⚠️ Divergence: behavior vs. intent**
   - `user_reject`/`user_abort` decisions = Claude repeatedly attempted actions
     the user had to refuse by hand → propose the missing CLAUDE.md rule, deny
     permission, or PreToolUse hook that would encode that intent.
   - Frequent `accept` with source `user_temporary`/`user_permanent` on the same
     tool = the user keeps approving the same thing → propose an allowlist entry
     (quote the exact `permissions.allow` rule to add).

   **🧩 Skills** — inventory vs. "skills invoked" in the digest:
   - Declared but never invoked (especially ones CLAUDE.md mandates, like a
     test-runner) → dead weight or a trigger problem; suggest a sharper
     `description` (trigger phrases) or removal.
   - High failure counts on a skill's underlying tools → the skill fires but
     doesn't work; inspect its SKILL.md steps.

   **🤖 Subagents** — inventory vs. "subagents spawned":
   - Defined agents that never run → their `description` doesn't match real
     tasks; propose rewording or dropping them.
   - A general-purpose agent doing work a specialized declared agent was built
     for → the specialized one isn't being selected; sharpen its description.

   **🧠 Memory** — if a memory-type MCP server is configured (flagged in the
   inventory):
   - Zero usage in "MCP servers used" = it's wired but never consulted →
     propose a CLAUDE.md line telling Claude when to read/write it, or remove
     the server.
   - Also check CLAUDE.md staleness: a memory file untouched for >30 days while
     `user_reject` keeps recurring means corrections aren't being written back —
     the self-improvement loop is broken; propose adding the recurring
     corrections to CLAUDE.md now.

   **📉 Health & cost**
   - `api_error` clusters, token/cost outliers by model, unusually heavy tools —
     anything that suggests harness friction (retries, oversized context).

   **🛠 Proposed changes** — a short, copy-pasteable list: settings edits,
   CLAUDE.md additions, hook suggestions. Don't apply them; this skill reports.

4. Offer to apply any of the proposed changes if the user wants.

## Notes

- Ground every claim in a digest line; if the data window is too thin to judge,
  say so rather than extrapolating.
- All data is local (the user's own Grafana stack); nothing leaves the machine.
