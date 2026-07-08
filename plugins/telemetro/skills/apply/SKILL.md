---
name: apply
description: >-
  Apply selected "Proposed changes" from the latest harness diagnosis report —
  settings/permissions edits, CLAUDE.md additions, hook or skill-description
  fixes. Use for "apply the proposed changes", "apply 1 and 3", "진단 결과
  반영해줘", "제안된 수정 적용해줘", "2번 제안 적용".
---

# Telemetro — apply proposed changes

Turn the diagnosis report's §6 proposals into actual config changes. Only ever
apply what the report proposed — nothing broader, nothing invented.

## Steps

1. Locate the latest diagnosis report:

   ```bash
   REPORTS="$(python3 -c "import sys;sys.path.insert(0,'${CLAUDE_PLUGIN_ROOT}/scripts');import common;print(common.reports_dir())")"
   ls -t "$REPORTS" | head -1
   ```

   No reports → tell the user to run `/telemetro:diagnose` first and stop.

2. Read the report's **§6 Proposed changes**. If the user named items ("apply 1
   and 3"), select those; otherwise show the numbered list and ask which to
   apply (all / subset). Skip items already marked applied.

3. Apply each selected item **by kind**, exactly as proposed:

   - **Settings / permissions** — before the first edit, back up the target
     file (`cp settings.json settings.json.telemetro-bak`). Merge only the
     proposed key/value into the scope the proposal names (project
     `.claude/settings.json` vs user `~/.claude/settings.json`); never widen a
     rule beyond the proposed text.
   - **CLAUDE.md additions** — append the proposed line(s) under the most
     fitting existing section (create a `## Conventions` section only if none
     fits). Quote the proposal verbatim unless grammar requires touch-ups.
   - **Hooks** — write the hook script into the project's `.claude/hooks/`
     (`chmod +x`) and add the settings `hooks` entry. Show the user the full
     script before saving — it's new executable code.
   - **Skill/agent description fixes** — if the file lives under a plugin
     cache (`~/.claude/plugins/…`), warn that edits there are overwritten on
     plugin update and the real fix belongs upstream; apply only if the user
     still wants it. Project/user-scope files: edit directly.

   Anything ambiguous or not literally in §6 → skip it and say why.

4. **Annotate the report**: append `→ ✅ applied <YYYY-MM-DD>` to each applied
   item (and `→ ⏭ skipped: <reason>` for explicit skips) so the next
   diagnosis's Trend section can check whether the change had the intended
   effect.

5. Summarize: what was applied where, backup locations, which changes need a
   **new session** to take effect (env vars, hooks), and suggest re-running
   `/telemetro:diagnose` after a few days of use to verify the effect.

## Notes

- This skill mutates the user's configuration — keep every change minimal and
  traceable to a §6 item. When in doubt, ask instead of applying.
- Never delete or rewrite existing rules unless the proposal explicitly says
  to; additions only by default.
