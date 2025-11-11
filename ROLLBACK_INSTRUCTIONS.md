# Emergency Rollback Instructions

If the app is crashing after the refactor, follow these steps to restore functionality:

## Option 1: Quick Fix (Recommended)

Add defensive error handling to MessageRouter signal handlers:

In `core/message_router.py`, wrap all signal handlers with try/except:

```python
def _on_order_signal(self, sender, **kwargs) -> None:
    try:
        msg = sender if isinstance(sender, dict) else kwargs
        # ... rest of handler
    except Exception as e:
        print(f"ERROR in _on_order_signal: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: call panel directly without marshaling
        if self.panel_live and hasattr(self.panel_live, "on_order_update"):
            try:
                self.panel_live.on_order_update(msg)
            except:
                pass
```

## Option 2: Revert to Previous Working State

```bash
git revert 3db0df5
git push -u origin claude/large-file-transfer-011CUxXi9bUuqWHQD57LPGRP
```

This will undo the signal routing refactor and restore the old manual wiring.

## Option 3: Disable Auto-Subscribe Temporarily

In `core/app_manager.py` line 588, change:

```python
auto_subscribe=False,  # Temporarily disable
```

Then manually wire signals in app_manager (restore old code from git history).

## Diagnosis Commands

```bash
# Check if signals are being emitted:
DEBUG_DATA=1 python main.py

# Check if MessageRouter is subscribing:
DEBUG_SIGNALS=1 python main.py

# See crash traceback:
python main.py 2>&1 | tee crash.log
```
