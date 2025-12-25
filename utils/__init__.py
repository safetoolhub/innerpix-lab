"""
Utilidades compartidas para Innerpix Lab
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
    select_best_date_from_file,
    format_renamed_name,
    is_renamed_filename,
    parse_renamed_name,
    get_all_metadata_from_file,
    extract_date_from_filename
)
from .file_utils import (
    get_exif_from_image,
    get_exif_from_video
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
)
from .platform_utils import (
    open_file_with_default_app,
    open_folder_in_explorer,
    is_linux,
    is_macos,
    is_windows,
)
from .callback_utils import (
    safe_progress_callback,
)
from .storage import (
    StorageBackend,
    JsonStorageBackend,
    QSettingsBackend
)
from .settings_manager import SettingsManager, settings_manager

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
    'get_all_metadata_from_file',
    'extract_date_from_filename',
    'select_best_date_from_file',
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
    'to_path',
    'calculate_file_hash',
    'launch_backup_creation',
    'cleanup_empty_directories',
    'find_next_available_name',
    'detect_file_source',
    'is_whatsapp_file',
    'get_exif_from_image',
    'get_exif_from_video',

    # Format utilities
    'format_size',
    'format_number',
    'format_file_count',
    'format_percentage',
    'truncate_path',

    # Platform utilities
    'open_file_with_default_app',
    'open_folder_in_explorer',
    'is_linux',
    'is_macos',
    'is_windows',

    # Callback utilities
    'safe_progress_callback',

    # Storage utilities
    'StorageBackend',
    'JsonStorageBackend',
    'QSettingsBackend',

    # Settings manager
    'SettingsManager',
    'settings_manager'
]
