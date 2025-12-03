"""
Utilidades compartidas para Pixaro Lab
"""
from .logger import (
    get_logger,
    SimpleLogger,
    set_global_log_level,
    configure_logging,
    change_logs_directory,
    get_log_file,
    get_logs_directory,
    log_section_header_discrete,
    log_section_footer_discrete,
    log_section_header_relevant,
    log_section_footer_relevant,
)
from .date_utils import (
    get_date_from_file,
    get_all_file_dates,
    select_chosen_date,
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
    find_next_available_name,
    detect_file_source,
    is_whatsapp_file,
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
    icon_manager
)
from .storage import (
    StorageBackend,
    JsonStorageBackend,
    QSettingsBackend
)
from .settings_manager import SettingsManager, settings_manager
from .decorators import deprecated

__all__ = [
    # Logger utilities
    'get_logger',
    'SimpleLogger',
    'set_global_log_level',
    'configure_logging',
    'change_logs_directory',
    'get_log_file',
    'get_logs_directory',
    'log_section_header_discrete',
    'log_section_footer_discrete',
    'log_section_header_relevant',
    'log_section_footer_relevant',

    # Date utilities
    'get_date_from_file',
    'get_all_file_dates',
    'select_chosen_date',
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
    'detect_file_source',
    'is_whatsapp_file',

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
    'icon_manager',

    # Storage utilities
    'StorageBackend',
    'JsonStorageBackend',
    'QSettingsBackend',

    # Settings manager
    'SettingsManager',
    'settings_manager',

    # Decorators
    'deprecated'
]
