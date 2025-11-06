"""
Configuración centralizada para Pixaro Lab
"""
from pathlib import Path


class Config:
    """Configuración principal de la aplicación"""

    # ========================================================================
    # INFORMACIÓN DE LA APLICACIÓN
    # ========================================================================
    APP_NAME = "Pixaro Lab"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Organiza, renombra y optimiza tu biblioteca de fotos"

    # ========================================================================
    # EXTENSIONES DE ARCHIVOS SOPORTADOS
    # ========================================================================
    SUPPORTED_IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.heic', '.heif',
        '.tiff', '.tif', '.bmp', '.webp'
    }

    SUPPORTED_VIDEO_EXTENSIONS = {
        '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv'
    }

    # ========================================================================
    # CONFIGURACIÓN DE LOGGING
    # ========================================================================
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y%m%d_%H%M%S"

    # ========================================================================
    # DIRECTORIOS POR DEFECTO
    # ========================================================================
    DEFAULT_BASE_DIR = Path.home() / "Documents" / "Pixaro_Lab"
    DEFAULT_LOG_DIR = DEFAULT_BASE_DIR / "logs"
    DEFAULT_BACKUP_DIR = DEFAULT_BASE_DIR / "backups"

    # ========================================================================
    # CONFIGURACIÓN DE PROCESAMIENTO
    # ========================================================================
    MAX_WORKERS = 4
    PROGRESS_UPDATE_INTERVAL = 10
    DEFAULT_WORKER_THREADS = 4
    MAX_WORKER_THREADS = 16
    LARGE_FILE_TIMEOUT = 120
    ENABLE_HASH_CACHE = True
    DEFAULT_HASH_SIZE = 8

    # ========================================================================
    # CONFIGURACIÓN DE DESARROLLO
    # ========================================================================
    DEVELOPMENT_MODE = True  # Si True, salta directamente a Stage 2 con la última carpeta usada

    # ========================================================================
    # CONSTANTES DE UI
    # ========================================================================
    TABLE_MAX_HEIGHT = 300  # Altura máxima para tablas en diálogos
    THUMBNAIL_SIZE = 150  # Tamaño de miniaturas en píxeles

    # ========================================================================
    # CONSTANTES DE WORKERS
    # ========================================================================
    WORKER_SHUTDOWN_TIMEOUT_MS = 10000  # Tiempo de espera para detener workers (milisegundos)
    PROGRESS_CALLBACK_INTERVAL = 50  # Actualizar progreso cada N archivos procesados

    # ========================================================================
    # CONSTANTES DE DIÁLOGOS
    # ========================================================================
    PREVIEW_MAX_ITEMS = 20  # Máximo de items para preview en diálogos

    # ========================================================================
    # CONFIGURACIÓN DE NORMALIZACIÓN
    # ========================================================================
    NORMALIZED_DATE_FORMAT = "%Y%m%d_%H%M%S"
    CONFLICT_SUFFIX_FORMAT = "_{:03d}"
    DATE_FORMAT = "%Y%m%d"
    TIME_FORMAT = "%H%M%S"

    # ========================================================================
    # CONFIGURACIÓN DE ANÁLISIS
    # ========================================================================
    # Umbral para solicitar confirmación antes de analizar directorios grandes
    LARGE_DIRECTORY_THRESHOLD = 40000  # Número de archivos

    # Configuración para detección de duplicados (futuro)
    DEFAULT_HAMMING_THRESHOLD = 5
    MAX_HAMMING_THRESHOLD = 20
    
    # ========================================================================
    # TIMING MÍNIMO DE ANÁLISIS (Stage 2)
    # ========================================================================
    # Duración mínima de visualización de cada fase del análisis en segundos
    # Esto garantiza que el usuario siempre vea el progreso, incluso si el
    # análisis real es muy rápido
    MIN_PHASE_DURATION_SECONDS = 2.0  # Default: 2 segundos por fase
    
    # Delay adicional antes de transicionar a Stage 3 (después de completar todo)
    FINAL_DELAY_BEFORE_STAGE3_SECONDS = 2.0  # Default: 2 segundos

    # ========================================================================
    # MÉTODOS DE UTILIDAD
    # ========================================================================
    @classmethod
    def is_image_file(cls, filename: str) -> bool:
        """
        Verifica si un archivo es una imagen soportada

        Args:
            filename: Nombre del archivo a verificar

        Returns:
            True si es una imagen soportada, False en caso contrario
        """
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_IMAGE_EXTENSIONS

    @classmethod
    def is_video_file(cls, filename: str) -> bool:
        """
        Verifica si un archivo es un video soportado

        Args:
            filename: Nombre del archivo a verificar

        Returns:
            True si es un video soportado, False en caso contrario
        """
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_VIDEO_EXTENSIONS

    @classmethod
    def is_media_file(cls, filename: str) -> bool:
        """
        Verifica si un archivo es multimedia soportado (imagen o video)

        Args:
            filename: Nombre del archivo a verificar

        Returns:
            True si es multimedia soportado, False en caso contrario
        """
        return cls.is_image_file(filename) or cls.is_video_file(filename)

    @classmethod
    def is_supported_file(cls, filename: str) -> bool:
        """
        Verifica si un archivo es soportado

        Args:
            filename: Nombre del archivo a verificar

        Returns:
            True si es soportado, False en caso contrario
        """
        return cls.is_media_file(filename)

    @classmethod
    def get_file_type(cls, filename: str) -> str:
        """
        Obtiene el tipo de archivo

        Args:
            filename: Nombre del archivo

        Returns:
            'PHOTO', 'VIDEO', u 'OTHER'
        """
        if cls.is_image_file(filename):
            return 'PHOTO'
        elif cls.is_video_file(filename):
            return 'VIDEO'
        else:
            return 'OTHER'

    @classmethod
    def ensure_directories_exist(cls):
        """Crea los directorios necesarios si no existen"""
        cls.DEFAULT_BASE_DIR.mkdir(parents=True, exist_ok=True)
        cls.DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
