"""
Utilidades compartidas para Pixaro Lab
"""
from .logger import get_logger, SimpleLogger, set_global_log_level
from .date_utils import (
    get_date_from_file,
    format_renamed_name,
    is_renamed_filename,
    parse_renamed_name
)
from .screen_utils import (
    ScreenResolution,
    WindowSizeConfig,
    ScreenDetector,
    screen_detector,
    get_optimal_window_config
)
from .file_utils import (
    validate_file_exists,
    validate_files_list,
    to_path,
    calculate_file_hash,
    launch_backup_creation,
    cleanup_empty_directories,
    find_next_available_name
)
from .format_utils import (
    format_size,
    format_number,
    format_file_count,
    format_percentage,
    truncate_path,
    format_file_operation_summary,
    format_count_short,
    format_size_short,
    format_count_full,
    format_size_full,
    format_time_ago
)
from .platform_utils import (
    open_file_with_default_app,
    open_folder_in_explorer,
    is_linux,
    is_macos,
    is_windows,
    get_default_file_manager
)
from .callback_utils import (
    safe_progress_callback,
    create_safe_callback
)
from .icons import (
    IconManager,
    get_icon,
    set_button_icon,
    set_label_icon,
    create_icon_label
)
from .storage import (
    StorageBackend,
    JsonStorageBackend,
    QSettingsBackend
)
from .settings_manager import SettingsManager
from .decorators import deprecated

__all__ = [
    # Logger utilities
    'get_logger',
    'SimpleLogger',
    'set_global_log_level',

    # Date utilities
    'get_date_from_file',
    'format_renamed_name',
    'is_renamed_filename',
    'parse_renamed_name',

    # Screen utilities
    'ScreenResolution',
    'WindowSizeConfig',
    'ScreenDetector',
    'screen_detector',
    'get_optimal_window_config',

    # File utilities
    'validate_file_exists',
    'validate_files_list',
    'to_path',
    'calculate_file_hash',
    'launch_backup_creation',
    'cleanup_empty_directories',
    'find_next_available_name',

    # Format utilities
    'format_size',
    'format_number',
    'format_file_count',
    'format_percentage',
    'truncate_path',
    'format_file_operation_summary',
    'format_count_short',
    'format_size_short',
    'format_count_full',
    'format_size_full',
    'format_time_ago',

    # Platform utilities
    'open_file_with_default_app',
    'open_folder_in_explorer',
    'is_linux',
    'is_macos',
    'is_windows',
    'get_default_file_manager',

    # Callback utilities
    'safe_progress_callback',
    'create_safe_callback',

    # Icon utilities
    'IconManager',
    'get_icon',
    'set_button_icon',
    'set_label_icon',
    'create_icon_label',

    # Storage utilities
    'StorageBackend',
    'JsonStorageBackend',
    'QSettingsBackend',

    # Settings manager
    'SettingsManager',

    # Decorators
    'deprecated'
]
