
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Verifying UI imports and worker availability...")

try:
    print("Importing ui.workers...")
    from ui.workers import (
        AnalysisWorker,
        LivePhotoAnalysisWorker,
        HeicAnalysisWorker,
        ExactDuplicatesAnalysisWorker,
        ZeroByteAnalysisWorker,
        RenamingAnalysisWorker,
        OrganizationAnalysisWorker
    )
    print("✅ ui.workers imports successful")
except ImportError as e:
    print(f"❌ Failed to import from ui.workers: {e}")
    sys.exit(1)

try:
    print("Importing ui.stages.stage_2_window...")
    from ui.stages.stage_2_window import Stage2Window
    print("✅ Stage 2 Window import successful")
except ImportError as e:
    print(f"❌ Failed to import stage_2_window: {e}")
    sys.exit(1)

try:
    print("Importing ui.stages.stage_3_window...")
    from ui.stages.stage_3_window import Stage3Window
    print("✅ Stage 3 Window import successful")
except ImportError as e:
    print(f"❌ Failed to import stage_3_window: {e}")
    sys.exit(1)

print("\nVerifying Stage 3 Analysis Trigger Logic...")
# Just mocking to ensure method exists
if hasattr(Stage3Window, '_run_analysis_and_open_dialog'):
    print("✅ Stage3Window has _run_analysis_and_open_dialog")
else:
    print("❌ Stage3Window MISSING _run_analysis_and_open_dialog")
    sys.exit(1)

print("\nAll UI components verified successfully!")
