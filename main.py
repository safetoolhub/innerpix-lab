"""
Innerpix Lab - Application entry point

Multimedia file management application with tools for organizing and cleaning duplicates
"""
import sys
import os

# Configure Qt to avoid Wayland warnings
os.environ['QT_LOGGING_RULES'] = 'qt.qpa.wayland=false'

from PyQt6.QtWidgets import QApplication
from ui.screens.main_window import MainWindow
from ui.styles.design_system import DesignSystem
from config import Config
from utils.logger import configure_logging, get_logger
from utils import get_optimal_window_config
from utils.settings_manager import settings_manager
from utils.i18n import init_i18n
import logging


def main():
    """Main application entry point"""

    # Initialize internationalization before anything else
    language = settings_manager.get_language()
    init_i18n(language)

    if Config.DEVELOPMENT_MODE:
        print(f"DEVELOPMENT MODE ENABLED")
        if Config.SAVED_CACHE_DEV_MODE_PATH:
             print(f"Loading cache from: {Config.SAVED_CACHE_DEV_MODE_PATH}")

    # Read log level from persistent settings
    saved_log_level = settings_manager.get_log_level("INFO")  # INFO by default
    saved_dual_log = settings_manager.get_dual_log_enabled()  # True by default
    
    # Configure logging system with saved level
    log_file, logs_dir = configure_logging(
        logs_dir=Config.DEFAULT_LOG_DIR,
        level=saved_log_level,
        dual_log_enabled=saved_dual_log
    )
    
    # Read precalculation settings for log output
    precalc_hashes = settings_manager.get_precalculate_hashes()
    precalc_image_exif = settings_manager.get_precalculate_image_exif()
    precalc_video_exif = settings_manager.get_precalculate_video_exif()
    
    logger = get_logger()
    log_level = logging.getLevelName(logger.logger.level)
    
    # Get system info
    sys_info = Config.get_system_info()
    
    logger.info("=" * 80)
    logger.info(f"Starting {Config.APP_NAME} v{Config.get_full_version()}")
    logger.info("=" * 80)
    logger.info("")
    logger.info("SYSTEM CONFIGURATION:")
    logger.info(f"  • Total RAM: {sys_info['ram_total_gb']:.2f} GB")
    if sys_info['ram_available_gb']:
        logger.info(f"  • Available RAM: {sys_info['ram_available_gb']:.2f} GB")
    logger.info(f"  • CPU Cores: {sys_info['cpu_count']}")
    logger.info(f"  • I/O Workers (hashing): {sys_info['io_workers']}")
    logger.info(f"  • CPU Workers (images): {sys_info['cpu_workers']}")
    if not sys_info['psutil_available']:
        logger.info("  psutil not available, using default values")
    logger.info("")
    logger.info("MEMORY CONFIGURATION:")
    logger.info(f"  • Max cache entries (initial): {sys_info['max_cache_entries']:,}")
    logger.info(f"  • Large dataset threshold: {sys_info['large_dataset_threshold']:,} files")
    logger.info(f"  • Auto-open dialog threshold: {sys_info['auto_open_threshold']:,} files")
    logger.info("")
    logger.info("LOG CONFIGURATION:")
    logger.info(f"  • Log level: {log_level}")
    logger.info(f"  • Log file: {log_file}")
    logger.info(f"  • Log directory: {logs_dir}")
    if saved_dual_log and saved_log_level in ('INFO', 'DEBUG'):
        logger.info(f"  • Dual logging: enabled (additional _WARNERROR file will be created)")
    else:
        logger.info(f"  • Dual logging: {'disabled' if not saved_dual_log else 'not applicable (WARNING/ERROR level)'}")
    logger.info("")
    logger.info("LANGUAGE:")
    logger.info(f"  • UI Language: {language}")
    logger.info("")
    logger.info("INITIAL ANALYSIS CONFIGURATION:")
    logger.info(f"  • SHA256 hash calculation: {'enabled' if precalc_hashes else 'disabled (on demand)'}")
    logger.info(f"  • Image metadata (EXIF): {'enabled' if precalc_image_exif else 'disabled (on demand)'}")
    logger.info(f"  • Video metadata (EXIF): {'enabled' if precalc_video_exif else 'disabled (on demand)'}")
    logger.info("=" * 80)
    logger.info("")
    
    app = QApplication(sys.argv)

    # Configure the application
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.get_full_version())
    app.setOrganizationName("InnerpixLab")

    # Create and show main window
    window = MainWindow()
    
    # Configure window size using decoupled utility
    action, window_size, center_pos = get_optimal_window_config()
    
    if action == 'resize' and window_size and center_pos:
        # 2K+ monitor: show in FullHD centered
        window.resize(window_size.width, window_size.height)
        window.move(center_pos[0], center_pos[1])
        logger.info(f"Window configured in FullHD ({window_size}) centered on screen")
    else:
        # FullHD or lower monitor: maximize
        window.showMaximized()
        logger.info("Window maximized")
    
    window.show()
    
    logger.debug("Main window shown")

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
