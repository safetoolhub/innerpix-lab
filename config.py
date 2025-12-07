"""
Configuración centralizada para Pixaro Lab
"""
from pathlib import Path
from typing import Optional


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
        '.tiff', '.tif', '.bmp', '.webp',
        # Uppercase variants for Linux case-sensitive rglob
        '.JPG', '.JPEG', '.PNG', '.HEIC', '.HEIF',
        '.TIFF', '.TIF', '.BMP', '.WEBP'
    }

    SUPPORTED_VIDEO_EXTENSIONS = {
        '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv',
        # Uppercase variants for Linux case-sensitive rglob
        '.MP4', '.MOV', '.AVI', '.MKV', '.WMV', '.FLV'
    }

    # Todas las extensiones soportadas (imágenes + videos)
    ALL_SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS

    # ========================================================================
    # CONFIGURACIÓN DE LOGGING
    # ========================================================================
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y%m%d_%H%M%S"
    
    # Configuración de rotación de logs
    MAX_LOG_FILE_SIZE_MB = 10  # Tamaño máximo de archivo de log en MB antes de rotar
    MAX_LOG_BACKUP_COUNT = 9999  # Número de backups a mantener (9999 = ilimitado en la práctica)

    # ========================================================================
    # DIRECTORIOS POR DEFECTO
    # ========================================================================
    DEFAULT_BASE_DIR = Path.home() / "Documents" / "Pixaro_Lab"
    DEFAULT_LOG_DIR = DEFAULT_BASE_DIR / "logs"
    DEFAULT_BACKUP_DIR = DEFAULT_BASE_DIR / "backups"

    # ========================================================================
    # CONFIGURACIÓN DE PROCESAMIENTO
    # ========================================================================
    PROGRESS_UPDATE_INTERVAL = 10
    LARGE_FILE_TIMEOUT = 120
    ENABLE_HASH_CACHE = True
    DEFAULT_HASH_SIZE = 8
    
    # Factores de cálculo para workers dinámicos
    _WORKER_FACTOR_PER_CORE = 2  # 2 workers por core (I/O bound)
    _MIN_WORKERS = 4
    _MAX_WORKERS = 16
    
    @classmethod
    def get_cpu_count(cls) -> int:
        """
        Obtiene el número de CPUs/cores del sistema.
        
        Returns:
            Número de cores, o 4 si no se puede detectar
        """
        import os
        return os.cpu_count() or 4
    
    @classmethod
    def get_optimal_worker_threads(cls) -> int:
        """
        Calcula el número óptimo de workers para procesamiento paralelo.
        
        Para operaciones I/O bound (lectura de archivos, cálculo de hashes),
        usamos 2x el número de cores. Para operaciones CPU bound (análisis
        de imágenes), usaríamos 1x cores.
        
        Fórmula: min(max(cores * 2, 4), 16)
        
        Returns:
            Número óptimo de workers (entre 4 y 16)
        """
        cores = cls.get_cpu_count()
        
        # Para operaciones I/O bound, usar 2x cores
        optimal = cores * cls._WORKER_FACTOR_PER_CORE
        
        # Aplicar límites
        return max(cls._MIN_WORKERS, min(optimal, cls._MAX_WORKERS))
    
    @classmethod
    def get_cpu_bound_workers(cls) -> int:
        """
        Calcula workers para operaciones CPU-intensive (análisis de imágenes).
        
        Para CPU bound, usar 1x cores (sin hyperthreading).
        
        Returns:
            Número de workers para operaciones CPU bound
        """
        cores = cls.get_cpu_count()
        return max(cls._MIN_WORKERS, min(cores, cls._MAX_WORKERS))
    
    @classmethod
    def get_actual_worker_threads(cls, override: int = 0, io_bound: bool = True) -> int:
        """
        Obtiene el número real de workers a usar, respetando override manual.
        
        Args:
            override: Valor de override del usuario (0 = automático)
            io_bound: True para operaciones I/O, False para CPU bound
        
        Returns:
            Número de workers a usar
        """
        # Si hay override manual (>0), usarlo
        if override > 0:
            return min(override, cls.MAX_WORKER_THREADS)
        
        # Si no, usar automático según tipo de operación
        if io_bound:
            return cls.get_optimal_worker_threads()
        else:
            return cls.get_cpu_bound_workers()
    
    # Valores por defecto para compatibilidad con código legacy
    # (se recomienda usar los métodos get_optimal_worker_threads() en su lugar)
    MAX_WORKERS = None  # Se calcula dinámicamente
    DEFAULT_WORKER_THREADS = None  # Se calcula dinámicamente
    MAX_WORKER_THREADS = 16  # Límite máximo absoluto

    # ========================================================================
    # CONFIGURACIÓN DE DESARROLLO
    # ========================================================================
    DEVELOPMENT_MODE = False  # Si True, salta directamente a Stage 2 con la última carpeta usada
    
    # Configuración de caché para desarrollo (acelerar pruebas con datasets grandes)
    DEV_USE_CACHED_ANALYSIS = True  # Si True, intenta cargar .pixaro_analysis_cache.pkl
    DEV_CACHE_FILENAME = ".pixaro_analysis_cache.pkl"


    # ========================================================================
    # TIMING MÍNIMO DE ANÁLISIS (Stage 2)
    # ========================================================================
    # Duración mínima de visualización de cada fase del análisis en segundos
    # Esto garantiza que el usuario siempre vea el progreso, incluso si el
    # análisis real es muy rápido
    MIN_PHASE_DURATION_SECONDS = 0.0  # Default: 1 segundo por fase
    
    # Delay adicional antes de transicionar a Stage 3 (después de completar todo)
    FINAL_DELAY_BEFORE_STAGE3_SECONDS =1.0  # Default: 2 segundos

    # ========================================================================
    # CONSTANTES DE UI
    # ========================================================================
    TABLE_MAX_HEIGHT = 300  # Altura máxima para tablas en diálogos
    THUMBNAIL_SIZE = 200  # Tamaño de miniaturas en píxeles (aumentado para mejor visualización)

    # ========================================================================
    # CONSTANTES DE WORKERS
    # ========================================================================
    WORKER_SHUTDOWN_TIMEOUT_MS = 10000  # Tiempo de espera para detener workers (milisegundos)
    UI_UPDATE_INTERVAL = 10  # Actualizar progreso de UI cada N archivos procesados
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
    # CONFIGURACIÓN DE DIÁLOGO DE ARCHIVOS SIMILARES
    # ========================================================================
    # Umbrales de navegación para evitar bloqueos de UI con muchos grupos
    SIMILAR_FILES_MAX_GROUPS_WARNING = 500  # Advertir si hay más de N grupos
    SIMILAR_FILES_MAX_GROUPS_NAVIGABLE = 1000  # Límite máximo de grupos navegables
    SIMILAR_FILES_LARGE_DATASET_THRESHOLD = 10000  # Umbral para considerar dataset grande
    
    # Sensibilidades iniciales según tamaño del dataset
    SIMILAR_FILES_DEFAULT_SENSITIVITY = 85  # Sensibilidad para datasets pequeños
    SIMILAR_FILES_LARGE_DATASET_SENSITIVITY = 100  # Sensibilidad para datasets grandes (muy restrictivo)
    
    # Clustering progresivo para evitar bloqueos
    SIMILAR_FILES_INITIAL_BATCH_SIZE = 200  # Archivos a procesar en batch inicial (reducido para evitar crashes)
    SIMILAR_FILES_LOAD_MORE_BATCH_SIZE = 300  # Archivos adicionales por batch
    
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
    def get_max_cache_entries(cls, file_count: Optional[int] = None) -> int:
        """
        Calcula el número máximo de entradas en caché según RAM disponible y número de archivos.
        
        Si file_count no se proporciona, usa solo RAM.
        Si se proporciona, calcula el óptimo considerando ambos factores.
        
        Estrategia:
        - La caché debe poder contener todos los archivos si hay RAM suficiente
        - Asumimos ~1KB por entrada de caché (conservador)
        - Usamos hasta el 10% de la RAM total para la caché
        - Aplicamos límites absolutos para evitar extremos
        
        Args:
            file_count: Número total de archivos (opcional)
        
        Returns:
            Número máximo de entradas para caché de metadatos
        """
        ram_gb = cls._get_system_ram_gb()
        
        if file_count is None:
            # Solo RAM: usar 1000 entradas por GB de RAM
            max_entries = int(ram_gb * 1000)
        else:
            # Dinámico: considerar tanto RAM como file count
            
            # Idealmente, cachear todos los archivos
            cache_needed = file_count
            
            # Calcular cuántas entradas podemos permitirnos según RAM
            # Asumimos 1KB por entrada, usamos 10% de RAM para caché
            available_ram_kb = ram_gb * 1024 * 1024 * 0.1  # 10% de RAM en KB
            max_entries_by_ram = int(available_ram_kb)  # 1KB por entrada
            
            # Tomar el mínimo para no exceder RAM
            max_entries = min(cache_needed, max_entries_by_ram)
            
            # Si el file_count es muy pequeño, asegurar un mínimo razonable
            max_entries = max(max_entries, int(ram_gb * 1000))
        
        # Límites: mínimo 5000, máximo 200000
        return max(5000, min(200000, max_entries))
    
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
        
        # Límites: mínimo 3000, máximo 50000
        return max(3000, min(50000, threshold))
    
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
    
    @classmethod
    def get_system_info(cls) -> dict:
        """
        Obtiene información completa del sistema para logging.
        
        Returns:
            Dict con ram_gb, ram_available_gb, cpu_count, cache_entries,
            large_threshold, auto_open_threshold, io_workers, cpu_workers
        """
        ram_gb = cls._get_system_ram_gb()
        
        try:
            import psutil
            ram_available_gb = psutil.virtual_memory().available / (1024 ** 3)
            psutil_available = True
        except ImportError:
            ram_available_gb = None
            psutil_available = False
        
        return {
            'ram_total_gb': ram_gb,
            'ram_available_gb': ram_available_gb,
            'psutil_available': psutil_available,
            'cpu_count': cls.get_cpu_count(),
            'max_cache_entries': cls.get_max_cache_entries(),
            'large_dataset_threshold': cls.get_large_dataset_threshold(),
            'auto_open_threshold': cls.get_similarity_dialog_auto_open_threshold(),
            'io_workers': cls.get_optimal_worker_threads(),
            'cpu_workers': cls.get_cpu_bound_workers(),
        }
    


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

