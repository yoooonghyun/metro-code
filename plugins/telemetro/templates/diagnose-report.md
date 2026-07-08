# Harness Diagnosis — {date}

> Window: last {hours}h · Source: {grafana_url} · Project: {project_path}
> Data volume: {events_scanned} events, {metric_count} claude_code metrics
> {data_confidence_note: e.g. "thin window — treat findings as tentative"}

## 1. Verdict

{One paragraph: is the harness behaving as intended overall? Name the single
most important finding. If the data is too thin to judge, say so here.}

## 2. Working as intended ✅

{Guardrails and configuration that demonstrably did their job. One bullet per
finding, each ending with its evidence in parentheses.}

- {e.g. "PreToolUse hook blocks force-pushes — fired N times (reject (hook): N)"}

## 3. Divergences ⚠️

{Where behavior differed from intent. Every bullet must cite a digest line.
Order by impact.}

### 3.1 Rules & permissions
- {user_reject/user_abort patterns → the missing rule/hook that would encode
  the intent}
- {repeated user_temporary approvals → allowlist candidates}

### 3.2 Skills
- {should-have-fired-but-didn't: wrapped work seen as raw commands while the
  skill never invoked (cite "raw bash commands" line)}
- {fired-but-deviated: mandated step's tool missing around invocations,
  failure clusters}
- {If no matching situation occurred: "no evidence either way — not judged"}

### 3.3 Subagents
- {missed delegation / activity contradicting the description}

### 3.4 Memory
- {memory-type MCP wired but never consulted; CLAUDE.md staleness vs recurring
  user_reject (broken self-improvement loop)}

## 4. Health & cost 📉

- {api_error clusters, token/cost outliers by model, unusually heavy tools}

## 5. Trend vs. previous diagnosis

{If a previous report exists in the reports dir: which divergences were fixed,
which persist, what's new. If none: "first diagnosis — no baseline yet."}

## 6. Proposed changes 🛠

{Numbered, copy-pasteable, one change per item. Each maps back to a finding
above by section number. NOT auto-applied.}

1. {e.g. `permissions.allow += "WebFetch(domain:api.github.com)"` — fixes 3.1}
2. {e.g. CLAUDE.md addition: "…" — fixes 3.1}
3. {e.g. sharpen `skills/foo` description with trigger phrases "…" — fixes 3.2}
