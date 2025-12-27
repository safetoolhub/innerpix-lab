import sys
import os
from pathlib import Path

# Add project root to pythonpath
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from config import Config
    from utils.platform_utils import get_system_info
    
    print("✅ Config module imported successfully")
    
    print("\n--- System Utils ---")
    sys_info = get_system_info()
    print(f"System Info: {sys_info}")
    
    print("\n--- Config Values ---")
    print(f"APP_NAME: {Config.APP_NAME}")
    print(f"DEFAULT_LOG_DIR: {Config.DEFAULT_LOG_DIR}")
    print(f"CPU Count (via Config): {Config.get_cpu_count()}")
    print(f"Optimal Workers (via Config): {Config.get_optimal_worker_threads()}")
    print(f"Max Time Difference (seconds): {Config.MAX_TIME_DIFFERENCE_SECONDS}")
    print(f"Max Hamming Threshold: {Config.MAX_HAMMING_THRESHOLD}")
    
    # Check for removed attributes (should raise AttributeError or be None if I kept them as None)
    # I kept MAX_WORKERS as None for compat
    print(f"MAX_WORKERS (Deprecated): {Config.MAX_WORKERS}")
    
    # Verify method delegation
    full_info = Config.get_system_info()
    print(f"Full System Info (Config delegated): {full_info}")
    
    assert 'max_cache_entries' in full_info, "Config.get_system_info should return extended info"
    
    print("\n✅ Verification Successful!")
    
except ImportError as e:
    print(f"❌ ImportError: {e}")
    sys.exit(1)
except AttributeError as e:
    print(f"❌ AttributeError: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"❌ AssertionError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected Error: {e}")
    sys.exit(1)
