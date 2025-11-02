"""Package for reusable UI components

Exports a small set of component constructors/classes used by the UI.
"""
from .top_bar import TopBar
# NOTE: `SummaryPanel` used to be a separate component. TopBar now
# provides the summary UI and a compatibility wrapper is exported
# below so external imports (from ui.components import SummaryPanel)
# keep working while we remove the legacy implementation.
from .action_buttons import ActionButtons

__all__ = [
    "TopBar",
    "ActionButtons",
]
