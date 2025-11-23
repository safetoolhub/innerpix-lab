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

    # Todas las extensiones soportadas (imágenes + videos)
    ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS

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
    # MAX_WORKERS: Detectar automáticamente cores disponibles (mínimo 4, máximo 16)
    import os
    _detected_cores = os.cpu_count() or 4
    MAX_WORKERS = min(max(_detected_cores, 4), 16)
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
    # TIMING MÍNIMO DE ANÁLISIS (Stage 2)
    # ========================================================================
    # Duración mínima de visualización de cada fase del análisis en segundos
    # Esto garantiza que el usuario siempre vea el progreso, incluso si el
    # análisis real es muy rápido
    MIN_PHASE_DURATION_SECONDS = 0.0  # Default: 1 segundo por fase
    
    # Delay adicional antes de transicionar a Stage 3 (después de completar todo)
    FINAL_DELAY_BEFORE_STAGE3_SECONDS =0.0  # Default: 2 segundos

    # ========================================================================
    # CONSTANTES DE UI
    # ========================================================================
    TABLE_MAX_HEIGHT = 300  # Altura máxima para tablas en diálogos
    THUMBNAIL_SIZE = 200  # Tamaño de miniaturas en píxeles (aumentado para mejor visualización)

    # ========================================================================
    # CONSTANTES DE WORKERS
    # ========================================================================
    WORKER_SHUTDOWN_TIMEOUT_MS = 10000  # Tiempo de espera para detener workers (milisegundos)
    UI_UPDATE_INTERVAL = 1  # Actualizar progreso de UI cada N archivos procesados
    LOG_PROGRESS_INTERVAL = 1000  # Escribir log de progreso cada N archivos (modo INFO)

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
    
    # Configuración para detección de duplicados HEIC/JPG
    MAX_TIME_DIFFERENCE_SECONDS = 60  # Tolerancia máxima de tiempo entre archivos duplicados (segundos)
    
    # Configuración de extracción de metadatos de video
    # Por defecto False porque es muy lento y la app se enfoca en imágenes
    USE_VIDEO_METADATA = False
    
    # ========================================================================
    # CONFIGURACIÓN DE MEMORIA Y CACHÉ (DINÁMICA SEGÚN RAM)
    # ========================================================================
    @staticmethod
    def _get_system_ram_gb() -> float:
        """
        Obtiene la RAM total del sistema en GB.
        
        Returns:
            RAM en GB, o 8.0 si no se puede detectar
        """
        try:
            import psutil
            return psutil.virtual_memory().total / (1024 ** 3)
        except ImportError:
            # psutil no disponible, asumir 8GB por defecto
            return 8.0
    
    @classmethod
    def get_max_cache_entries(cls) -> int:
        """
        Calcula el número máximo de entradas en caché según RAM disponible.
        
        Fórmula: 1000 entradas por GB de RAM (mínimo 5000, máximo 20000)
        
        Returns:
            Número máximo de entradas para caché de metadatos
        """
        ram_gb = cls._get_system_ram_gb()
        
        # 1000 entradas por GB de RAM
        max_entries = int(ram_gb * 1000)
        
        # Límites: mínimo 5000, máximo 20000
        return max(5000, min(20000, max_entries))
    
    @classmethod
    def get_large_dataset_threshold(cls) -> int:
        """
        Calcula el umbral para considerar un dataset como "grande" según RAM.
        
        Datasets grandes activan optimizaciones de memoria:
        - Liberación de caché entre fases
        - No apertura automática de diálogos
        - Garbage collection más agresivo
        
        Fórmula: 500 archivos por GB de RAM (mínimo 3000, máximo 10000)
        
        Returns:
            Número de archivos para considerar dataset grande
        """
        ram_gb = cls._get_system_ram_gb()
        
        # 500 archivos por GB de RAM
        threshold = int(ram_gb * 500)
        
        # Límites: mínimo 3000, máximo 10000
        return max(3000, min(10000, threshold))
    
    @classmethod
    def get_similarity_dialog_auto_open_threshold(cls) -> int:
        """
        Umbral de archivos para abrir automáticamente el diálogo de similares.
        
        Datasets mayores no abren automáticamente para evitar OOM en UI.
        Configurado como el 60% del threshold de dataset grande.
        
        Returns:
            Número máximo de archivos para apertura automática
        """
        return int(cls.get_large_dataset_threshold() * 0.6)
    


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

