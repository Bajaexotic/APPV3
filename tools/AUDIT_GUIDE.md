# APPSIERRA Audit Tool Usage Guide

## Overview

The `run_code_audit.py` orchestrator runs diagnostic and validation tools using either **scope patterns** or **curated presets**.

---

## Quick Start

### List Available Presets

```bash
python tools/run_code_audit.py --list-presets
```

### Run a Preset

```bash
# UI & Mode validation (5 tools)
python tools/run_code_audit.py --preset ui

# Quick health check (2 tools)
python tools/run_code_audit.py --preset quick

# Full system audit (all validation/diagnostic tools)
python tools/run_code_audit.py --preset full
```

### Run by Scope Pattern

```bash
# All validation tools
python tools/run_code_audit.py --scope validation.*

# All DTC tools
python tools/run_code_audit.py --scope dtc.*

# Specific tool
python tools/run_code_audit.py --scope validation.config_integrity
```

### Exclude Specific Tools

```bash
# Run all validation except dependencies
python tools/run_code_audit.py --scope validation.* --exclude dependencies

# Run full audit but skip performance tools
python tools/run_code_audit.py --preset full --exclude performance.*

# Multiple exclusions
python tools/run_code_audit.py --preset full --exclude validation.dependencies --exclude performance.startup_profiler
```

---

## Available Presets

### `ui` - UI & Mode Validation

**Purpose:** Validate UI data flow and SIM/LIVE mode segregation

**Runs:**

- `validation.config_integrity` - Environment/mode consistency
- `validation.theme_audit` - Theme validation across modes
- `dtc.probe` - DTC connectivity health check
- `diagnostics.signal_trace` - PyQt signal flow validation
- `diagnostics.state_diff` - State consistency check

**Use Case:** Before trading sessions, verify UI receives data correctly

```bash
python tools/run_code_audit.py --preset ui
```

---

### `quick` - Fast Health Check

**Purpose:** Minimal validation for rapid feedback

**Runs:**

- `validation.config_integrity`
- `dtc.probe`

**Use Case:** Quick sanity check during development

```bash
python tools/run_code_audit.py --preset quick
```

---

### `full` - Complete System Audit

**Purpose:** Comprehensive validation (CI/pre-deployment)

**Runs:**

- All validation tools (`validation.*`)
- All DTC tools (`dtc.*`)
- All diagnostic tools (`diagnostics.*`)
- All performance tools (`performance.*`)
- All maintenance tools (`maintenance.*`)

**Use Case:** CI pipeline, pre-release validation

```bash
python tools/run_code_audit.py --preset full
```

---

### `validation` - All Validation Tools

**Purpose:** Config, theme, schema validation

**Runs:**

- `validation.config_integrity`
- `validation.theme_audit`
- `validation.schema_validator`
- `validation.dependencies` (poetry_audit)
- `validation.theme_validation`

```bash
python tools/run_code_audit.py --preset validation
```

---

### `dtc` - All DTC Tools

**Purpose:** DTC protocol validation and diagnostics

**Runs:**

- `dtc.probe`
- `dtc.discovery`
- `dtc.handshake_validation`
- `dtc.test_framework`

```bash
python tools/run_code_audit.py --preset dtc
```

---

### `performance` - Performance Benchmarks

**Purpose:** Measure startup times, render performance, DB latency

**Runs:**

- `performance.startup_profiler`
- `performance.render_timer`

```bash
python tools/run_code_audit.py --preset performance
```

---

### `maintenance` - Code Quality & Reports

**Purpose:** Code cleanup, changelogs, metrics

**Runs:**

- `maintenance.code_cleanup`
- `maintenance.theme_refactor`
- `maintenance.sync_theme_schema`
- `reporting.metrics_exporter`
- `reporting.changelog_builder`

```bash
python tools/run_code_audit.py --preset maintenance
```

---

## Scope Patterns

All tools have a `__scope__` attribute following this hierarchy:

```
category.tool_name
```

### Categories

| Category        | Tools                                                                           |
| --------------- | ------------------------------------------------------------------------------- |
| `validation.*`  | config_integrity, theme_audit, schema_validator, dependencies, theme_validation |
| `dtc.*`         | probe, discovery, handshake_validation, test_framework                          |
| `diagnostics.*` | signal_trace, state_diff                                                        |
| `performance.*` | startup_profiler, render_timer                                                  |
| `maintenance.*` | code_cleanup, theme_refactor, sync_theme_schema                                 |
| `reporting.*`   | metrics_exporter, changelog_builder                                             |

### Pattern Examples

```bash
# All validation tools
python tools/run_code_audit.py --scope validation.*

# Specific tool
python tools/run_code_audit.py --scope dtc.probe

# All diagnostic tools
python tools/run_code_audit.py --scope diagnostics.*
```

---

## Advanced Usage

### Combine Preset with Exclusions

```bash
# Full audit but skip slow performance tests
python tools/run_code_audit.py --preset full --exclude performance.*

# UI validation but skip signal trace (if running headless)
python tools/run_code_audit.py --preset ui --exclude diagnostics.signal_trace
```

### Multiple Exclusions

```bash
python tools/run_code_audit.py --preset full \
    --exclude performance.* \
    --exclude validation.dependencies \
    --exclude reporting.*
```

---

## Integration Examples

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
python tools/run_code_audit.py --preset validation
```

### CI Pipeline

```yaml
# .github/workflows/audit.yml
- name: Run Full Audit
  run: python tools/run_code_audit.py --preset full
```

### Pre-Trading Session Script

```bash
#!/bin/bash
# scripts/pre_trading_check.sh
echo "Running UI validation..."
python tools/run_code_audit.py --preset ui

if [ $? -eq 0 ]; then
    echo "✅ All checks passed - safe to start trading"
else
    echo "❌ Validation failed - DO NOT trade"
    exit 1
fi
```

---

## Output Format

```
================================================================================
Running Audit Preset: ui
================================================================================

Running 5 tool(s):
  - diagnostics.signal_trace
  - diagnostics.state_diff
  - dtc.probe
  - validation.config_integrity
  - validation.theme_audit

================================================================================
[RUN] diagnostics.signal_trace
================================================================================
Signal trace written to logs/signal_trace.csv
[PASS] diagnostics.signal_trace

================================================================================
[RUN] diagnostics.state_diff
================================================================================
State diff written to reports/state_diff.json
[PASS] diagnostics.state_diff

... (continues for each tool)

================================================================================
AUDIT SUMMARY
================================================================================
Total: 5
Passed: 5
Failed: 0

✅ All tools passed!
```

---

## Troubleshooting

### Tool Not Found

```
No tools matched scope: validation.foo
```

**Solution:** Run `--list-presets` to see available tools, or check tool has `__scope__` attribute

### Tool Failed

```
[FAIL] dtc.probe returned 1
```

**Solution:** Run the tool individually with verbose output:

```bash
python tools/dtc_probe.py --mode health
```

### Import Errors

```
[ERR] validation.theme_audit: No module named 'config.theme'
```

**Solution:** Ensure you're running from repository root:

```bash
cd C:\Users\cgrah\Desktop\APPSIERRA
python tools/run_code_audit.py --preset ui
```

---

## Adding New Tools

To make a tool discoverable:

1. Add `__scope__` attribute to your tool:

```python
# tools/my_new_tool.py
__scope__ = "validation.my_new_tool"

def main(argv):
    # Tool implementation
    return 0  # 0 = success, non-zero = failure
```

2. Tool will automatically appear in scope matching:

```bash
python tools/run_code_audit.py --scope validation.*
```

3. (Optional) Add to a preset in `run_code_audit.py`:

```python
AUDIT_PRESETS = {
    "my_preset": [
        "validation.my_new_tool",
        # ...
    ]
}
```

---

## Best Practices

1. **Use presets for common workflows** - Don't memorize scope patterns
2. **Run `quick` during development** - Fast feedback loop
3. **Run `ui` before trading** - Verify data flow and mode routing
4. **Run `full` in CI** - Comprehensive validation
5. **Exclude slow tools locally** - Use `--exclude performance.*` for speed
6. **Check exit codes in scripts** - Non-zero = failure

---

## See Also

- Individual tool documentation in `tools/` directory
- Test suite in `tests/` directory
- Original audit report in repository root
