---
name: alias-symbol
description: >-
  Set or clear a custom display label (alias) for a symbol shown in the status
  line — handy for Korean names Yahoo doesn't provide. Use for "label 005930.KS
  as 삼성전자", "rename Apple to 애플", "show 005930.KS as 삼성전자", "remove the
  alias for TSLA" (also Korean: "005930.KS를 삼성전자로 표시해줘", "별칭 지워줘").
---

# Seekerizer — alias (custom label)

By default the status line shows the company name (e.g. `Samsung Electronics`
for `005930.KS`). An alias overrides that label. Display priority is
**alias → company name → symbol**. Aliases are stored in `aliases.json`.

## Commands

```bash
# Set a custom label (everything after the symbol is the label)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" alias 005930.KS 삼성전자

# Clear the custom label (revert to the auto company name)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/manage.py" unalias 005930.KS
```

## Workflow

1. Resolve the Yahoo symbol and the label the user wants.
2. Run `manage.py alias <SYMBOL> <LABEL>` (or `unalias <SYMBOL>` to clear).
3. The new label appears in the status line within ~60s. A symbol does not need
   to be in the watchlist to have an alias.
