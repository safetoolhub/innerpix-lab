"""
Configuración centralizada para PhotoKit Manager
"""
from pathlib import Path


class Config:
    """Configuración principal de la aplicación"""

    # ========================================================================
    # INFORMACIÓN DE LA APLICACIÓN
    # ========================================================================
    APP_NAME = "PhotoKit Manager"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Organiza, renombra y optimiza tu biblioteca de fotos"

    # ========================================================================
    # CONFIGURACIÓN DE VENTANA
    # ========================================================================
    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 600
    WINDOW_DEFAULT_WIDTH = 1200
    WINDOW_DEFAULT_HEIGHT = 800

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
    DEFAULT_BASE_DIR = Path.home() / "Documents" / "PhotoKit_Manager"
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
    # MÉTODOS DE UTILIDAD (COMPATIBILIDAD CON CÓDIGO EXISTENTE)
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
        Verifica si un archivo es soportado (alias para is_media_file)

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
        try:
            cls.DEFAULT_BASE_DIR.mkdir(parents=True, exist_ok=True)
            cls.DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            cls.DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: No se pudieron crear directorios por defecto: {e}")

    @classmethod
    def create_default_directories(cls):
        """Alias para ensure_directories_exist (compatibilidad)"""
        cls.ensure_directories_exist()



    # ========================================================================
    # CONFIGURACIÓN DE DETECCIÓN DE DUPLICADOS
    # ========================================================================
    
    # Hashing perceptual
    DEFAULT_HASH_SIZE = 8  # Tamaño del hash para imagehash (8x8 = 64 bits)
    DEFAULT_HAMMING_THRESHOLD = 10  # Umbral de distancia Hamming para similitud
    MAX_HAMMING_THRESHOLD = 20  # Máximo umbral permitido
    
    # Cache de hashes
    ENABLE_HASH_CACHE = True  # Habilitar caché de hashes calculados
    
    # Backup
    DEFAULT_BACKUP_DIR = Path.home() / "PhotoKit_Backups"
    
    # Métodos auxiliares para verificación de tipos de archivo
    @staticmethod
    def is_image_file(filename: str) -> bool:
        """Verifica si un archivo es una imagen"""
        return Path(filename).suffix.lower() in Config.SUPPORTED_IMAGE_EXTENSIONS
    
    @staticmethod
    def is_video_file(filename: str) -> bool:
        """Verifica si un archivo es un video"""
        return Path(filename).suffix.lower() in Config.SUPPORTED_VIDEO_EXTENSIONS
    
    @staticmethod
    def is_media_file(filename: str) -> bool:
        """Verifica si un archivo es multimedia (imagen o video)"""
        ext = Path(filename).suffix.lower()
        return ext in Config.SUPPORTED_IMAGE_EXTENSIONS or ext in Config.SUPPORTED_VIDEO_EXTENSIONS


# Instancia global para compatibilidad con código existente
config = Config()
