"""ui.tabs package intentionally removed.

All tabs code has been removed for the current development phase. This
module acts as a small placeholder that raises on use to make the removal
explicit and easier to diagnose at runtime.

If you plan to reintroduce tabs, replace this file with the real
implementation (or add a compatibility shim exposing the expected names).
"""

from __future__ import annotations


def _tabs_removed_placeholder(*args, **kwargs):
    """Placeholder called when code attempts to use the old tabs package.

    Raising a RuntimeError makes the failure obvious and points developers
    to the fact that the tabs module was intentionally removed in this
    development phase.
    """
    raise RuntimeError(
        "ui.tabs package removed — tabs are disabled for this phase. "
        "Reintroduce the tabs module or update callers to avoid importing it."
    )


__all__ = ["_tabs_removed_placeholder"]
