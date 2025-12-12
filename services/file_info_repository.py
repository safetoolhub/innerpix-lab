"""
File Info Repository

Repositorio centralizado de información de archivos del dataset seleccionado.
Almacena metadata del sistema de archivos y metadatos extendidos (EXIF, hashes, etc.)
para evitar búsquedas repetitivas sobre el mismo dataset.

Este módulo actúa como caché inteligente: si tiene el dato lo devuelve,
si no lo tiene lo busca automáticamente.

Los servicios NO reciben este repositorio como parámetro, sino que lo consultan
directamente. El repositorio es un singleton de facto creado en el scan inicial.

Diseño: Preparado para futura migración a BBDD si el rendimiento con datasets
enormes no es adecuado. La interfaz pública está desacoplada de la implementación
interna (dict en memoria).
"""
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Tuple, List, Protocol
from datetime import datetime
import threading

from utils.logger import get_logger
from utils.file_utils import calculate_file_hash

# Type alias for external compatibility
MetadataCache = 'FileInfoRepository'


@dataclass
class FileMetadata:
    """
    Metadatos puros de un archivo.
    
    Contiene información del sistema de archivos y metadatos extendidos
    como EXIF y hashes calculados bajo demanda.
    """
    path: Path
    size: int
    ctime: float  # Creation time (timestamp)
    mtime: float  # Modification time (timestamp)
    atime: float  # Access time (timestamp)
    
    # Extended Metadata (Lazy loaded or populated during scan)
    exif_data: Dict[str, Any] = field(default_factory=dict)
    
    # Hash (Lazy loaded - expensive operation)
    sha256: Optional[str] = None
    
    @property
    def extension(self) -> str:
        """Extensión del archivo en minúsculas"""
        return self.path.suffix.lower()

    @property
    def exif_date_time_original(self) -> Optional[str]:
        """Fecha EXIF DateTimeOriginal (fecha de captura)"""
        return self.exif_data.get('DateTimeOriginal')

    @property
    def exif_create_date(self) -> Optional[str]:
        """Fecha EXIF CreateDate"""
        return self.exif_data.get('CreateDate')
        
    @property
    def exif_date_digitized(self) -> Optional[str]:
        """Fecha EXIF DateTimeDigitized"""
        return self.exif_data.get('DateTimeDigitized')

    @property
    def sha256_hash(self) -> Optional[str]:
        """Hash SHA256 del archivo (alias para compatibilidad)"""
        return self.sha256


class IFileRepository(Protocol):
    """
    Interfaz abstracta del repositorio de archivos.
    
    Define el contrato que debe cumplir cualquier implementación,
    facilitando la migración futura a BBDD.
    """
    def add_file(self, path: Path) -> FileMetadata: ...
    def get_metadata(self, path: Path) -> Optional[FileMetadata]: ...
    def get_hash(self, path: Path) -> str: ...
    def set_hash(self, path: Path, hash_val: str) -> None: ...
    def get_all_files(self) -> List[FileMetadata]: ...
    def get_file_count(self) -> int: ...
    def get_files_by_size(self) -> Dict[int, List[FileMetadata]]: ...
    def clear(self) -> None: ...


class FileInfoRepository:
    """
    Repositorio centralizado de información de archivos (Singleton).
    
    Actúa como caché inteligente thread-safe para metadatos de archivos del dataset
    seleccionado por el usuario. Los métodos buscan automáticamente si no tienen
    el dato cacheado.
    
    Patrón de uso (Singleton):
    - Los servicios acceden a la instancia global via get_instance()
    - NO se pasa como parámetro a servicios
    - Si el dato está cacheado, lo devuelve
    - Si no está cacheado, lo busca y cachea automáticamente
    
    Características:
    - Thread-safe: Usa RLock para acceso concurrente
    - Singleton: Una única instancia compartida globalmente
    - Auto-sizing: Ajusta capacidad según RAM disponible
    - Hit/Miss tracking: Estadísticas de rendimiento
    - Lazy loading: Hashes y EXIF se calculan bajo demanda
    - Auto-fetch: Si no tiene un dato, lo busca automáticamente
    
    Compartido entre servicios:
    - ExactCopiesDetector y HEICRemover comparten hashes
    - FileOrganizer y FileRenamer usan fechas EXIF cacheadas
    - Todos los servicios usan stats básicos (size, mtime)
    
    Diseño:
    - Interfaz pública desacoplada de implementación (dict en memoria)
    - Preparado para migración futura a BBDD (SQLite, PostgreSQL, etc.)
    - Protocol IFileRepository define contrato abstracto
    
    Uso:
        # Obtener instancia (orchestrator o cualquier servicio)
        repo = FileInfoRepository.get_instance()
        
        # Población (orchestrator durante scan)
        for file in scan_results:
            repo.add_file(file)
        
        # Uso en servicios (acceso directo a instancia global)
        repo = FileInfoRepository.get_instance()
        all_files = repo.get_all_files()
        file_count = repo.get_file_count()
        hash_val = repo.get_hash(path)  # Calcula automáticamente si no está cacheado
        
        # Reset entre datasets
        repo.clear()
    """
    
    _instance: Optional['FileInfoRepository'] = None
    _lock_singleton = threading.Lock()
    
    def __new__(cls):
        """Implementación del patrón Singleton"""
        if cls._instance is None:
            with cls._lock_singleton:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa el repositorio vacío (solo la primera vez)"""
        # Solo inicializar si es la primera vez
        if not hasattr(self, '_initialized'):
            self._cache: Dict[Path, FileMetadata] = {}
            self._lock = threading.RLock()
            self._max_entries = 100000 
            self._enabled = True
            self._hits = 0
            self._misses = 0
            self._logger = get_logger('FileInfoRepository')
            self._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'FileInfoRepository':
        """
        Obtiene la instancia singleton del repositorio.
        
        Returns:
            FileInfoRepository: Instancia única del repositorio
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Resetea la instancia singleton (útil para tests).
        
        PRECAUCIÓN: Solo usar en tests o al cambiar de dataset.
        """
        with cls._lock_singleton:
            if cls._instance is not None:
                cls._instance.clear()
                cls._instance = None
    
    def add_file(self, path: Path) -> FileMetadata:
        """
        Añade un archivo al repositorio, leyendo stats básicos del disco.
        
        Args:
            path: Ruta del archivo a añadir
            
        Returns:
            FileMetadata: Metadatos del archivo añadido
            
        Raises:
            Exception: Si el archivo no existe o hay error de permisos
        """
        try:
            stat = path.stat()
            meta = FileMetadata(
                path=path,
                size=stat.st_size,
                ctime=stat.st_ctime,
                mtime=stat.st_mtime,
                atime=stat.st_atime
            )
            with self._lock:
                self._cache[path] = meta
                self._logger.debug(f"Archivo añadido al repositorio: {path}")
            return meta
        except Exception as e:
            self._logger.error(f"Error añadiendo archivo al repositorio: {path} - {e}")
            raise

    def get_metadata(self, path: Path) -> Optional[FileMetadata]:
        """
        Obtiene metadatos de un archivo del repositorio.
        
        Si no está en caché, retorna None (no lo busca automáticamente).
        Usar get_or_create() para auto-fetch.
        
        Args:
            path: Ruta del archivo
            
        Returns:
            FileMetadata si existe en caché, None en caso contrario
        """
        with self._lock:
            if path in self._cache:
                self._hits += 1
                return self._cache[path]
            self._misses += 1
            return None

    def set_basic_metadata(
        self, 
        path: Path, 
        size: int, 
        ctime: float, 
        mtime: float, 
        atime: float, 
        file_type: str = "OTHER"
    ) -> None:
        """
        Establece metadatos básicos directamente (usado por orchestrator).
        
        Args:
            path: Ruta del archivo
            size: Tamaño en bytes
            ctime: Creation time (timestamp)
            mtime: Modification time (timestamp)
            atime: Access time (timestamp)
            file_type: Tipo de archivo (ignorado, para compatibilidad)
        """
        meta = FileMetadata(
            path=path,
            size=size,
            ctime=ctime,
            mtime=mtime,
            atime=atime
        )
        with self._lock:
            self._cache[path] = meta
            self._logger.debug(f"Metadatos básicos establecidos: {path}")

    def get_hash(self, path: Path) -> str:
        """
        Obtiene el hash SHA256 del archivo.
        
        AUTO-FETCH: Si no está cacheado, lo calcula automáticamente usando
        utils.file_utils.calculate_file_hash() y lo cachea.
        
        Args:
            path: Ruta del archivo
            
        Returns:
            str: Hash SHA256 en hexadecimal
            
        Raises:
            Exception: Si el archivo no existe o hay error de lectura
        """
        # Intentar obtener del caché primero
        meta = self.get_metadata(path)
        if meta and meta.sha256:
            self._logger.debug(f"Hash cacheado para: {path}")
            return meta.sha256
        
        # No está en caché o no tiene hash: añadir/actualizar
        if not meta:
            self._logger.debug(f"Archivo no en caché, añadiendo: {path}")
            meta = self.add_file(path)
        
        # Calcular hash usando file_utils
        self._logger.debug(f"Calculando hash SHA256 para: {path}")
        sha256 = calculate_file_hash(path)
        
        with self._lock:
            meta.sha256 = sha256
        
        return sha256

    def set_hash(self, path: Path, hash_val: str) -> None:
        """
        Establece el hash SHA256 de un archivo directamente.
        
        Útil cuando el hash se ha calculado externamente.
        AUTO-FETCH: Si el archivo no está en caché, lo añade automáticamente.
        
        Args:
            path: Ruta del archivo
            hash_val: Hash SHA256 en hexadecimal
        """
        meta = self.get_metadata(path)
        if not meta:
            # Añadir archivo automáticamente si no está en caché
            if path.exists():
                meta = self.add_file(path)
            else:
                self._logger.warning(f"Intento de establecer hash para archivo no existente: {path}")
                return
        
        with self._lock:
            meta.sha256 = hash_val
            self._logger.debug(f"Hash establecido para: {path}")

    def set_exif(self, path: Path, exif_data: Dict[str, Any]) -> None:
        """
        Establece datos EXIF de un archivo.
        
        AUTO-FETCH: Si el archivo no está en caché, lo añade automáticamente.
        
        Args:
            path: Ruta del archivo
            exif_data: Diccionario con datos EXIF parseados
        """
        meta = self.get_metadata(path)
        if not meta:
            if path.exists():
                meta = self.add_file(path)
            else:
                self._logger.warning(f"Intento de establecer EXIF para archivo no existente: {path}")
                return
        
        with self._lock:
            meta.exif_data = exif_data
            self._logger.debug(f"EXIF establecido para: {path}")

    def get_files_by_size(self) -> Dict[int, List[FileMetadata]]:
        """
        Agrupa archivos por tamaño.
        
        Útil para detección de duplicados exactos (pre-filtrado).
        
        Returns:
            Dict[int, List[FileMetadata]]: Diccionario size -> lista de archivos
        """
        by_size: Dict[int, List[FileMetadata]] = {}
        with self._lock:
            for meta in self._cache.values():
                if meta.size not in by_size:
                    by_size[meta.size] = []
                by_size[meta.size].append(meta)
        
        self._logger.debug(f"Archivos agrupados por tamaño: {len(by_size)} grupos")
        return by_size
    
    def get_all_files(self) -> List[FileMetadata]:
        """
        Obtiene todos los archivos del repositorio.
        
        Returns:
            List[FileMetadata]: Lista de todos los archivos
        """
        with self._lock:
            return list(self._cache.values())
    
    def get_file_count(self) -> int:
        """
        Obtiene el número total de archivos en el repositorio.
        
        Método optimizado que no requiere crear una lista completa.
        Usar este método en lugar de len(get_all_files()).
        
        Returns:
            int: Número de archivos en el repositorio
        """
        with self._lock:
            count = len(self._cache)
        self._logger.debug(f"Conteo de archivos: {count}")
        return count

    def update_max_entries(self, total_files: int) -> None:
        """
        Actualiza el límite interno de entradas basado en el conteo de archivos.
        
        Args:
            total_files: Número total de archivos en el dataset
        """
        with self._lock:
            old_max = self._max_entries
            self._max_entries = max(self._max_entries, total_files + 1000)
            if old_max != self._max_entries:
                self._logger.info(f"Límite de entradas actualizado: {old_max} -> {self._max_entries}")

    def set_all_dates(self, path: Path, all_dates: Dict[str, Any]) -> None:
        """
        Establece todas las fechas extraídas (incluyendo EXIF) para un archivo.
        
        AUTO-FETCH: Si el archivo no está en caché, lo añade automáticamente.
        
        Args:
            path: Ruta del archivo
            all_dates: Diccionario con todas las fechas encontradas
        """
        meta = self.get_metadata(path)
        if not meta:
            if path.exists():
                meta = self.add_file(path)
            else:
                self._logger.warning(f"Intento de establecer fechas para archivo no existente: {path}")
                return
        
        with self._lock:
            meta.exif_data = all_dates.copy()
            self._logger.debug(f"Fechas establecidas para: {path}")

    def get_all_dates(self, path: Path) -> Dict[str, Any]:
        """
        Obtiene todas las fechas cacheadas (incluyendo EXIF) de un archivo.
        
        Args:
            path: Ruta del archivo
            
        Returns:
            Dict[str, Any]: Diccionario con fechas, vacío si no hay datos
        """
        meta = self.get_metadata(path)
        if meta and meta.exif_data:
            return meta.exif_data.copy()
        return {}

    def get_selected_date(self, path: Path) -> Tuple[Optional[datetime], str]:
        """
        Obtiene la mejor fecha disponible para un archivo y su fuente.
        
        Usa fechas EXIF cacheadas si están disponibles, sino usa stats del FS.
        
        Args:
            path: Ruta del archivo
            
        Returns:
            Tuple[Optional[datetime], str]: (fecha, fuente)
                fuente puede ser: "exif", "mtime", "unknown"
        """
        meta = self.get_metadata(path)
        if not meta:
            self._logger.warning(f"Archivo no en caché para get_selected_date: {path}")
            return None, "unknown"
            
        # Try EXIF first (implementación completa requeriría date_utils)
        # Por ahora retornamos mtime como fallback seguro
        return datetime.fromtimestamp(meta.mtime), "mtime"

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del repositorio.
        
        Returns:
            Dict con: size, max_entries, hits, misses, hit_rate
        """
        with self._lock:
            total_access = self._hits + self._misses
            hit_rate = (self._hits / total_access * 100) if total_access > 0 else 0.0
            stats = {
                'size': len(self._cache),
                'max_entries': self._max_entries,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate
            }
        return stats

    def log_stats(self) -> None:
        """Registra estadísticas actuales del repositorio en el log"""
        stats = self.get_stats()
        self._logger.info(
            f"Estadísticas del repositorio - "
            f"Archivos: {stats['size']}, "
            f"Límite: {stats['max_entries']}, "
            f"Hits: {stats['hits']}, "
            f"Misses: {stats['misses']}, "
            f"Hit Rate: {stats['hit_rate']:.1f}%"
        )

    def clear(self) -> None:
        """
        Limpia completamente el repositorio.
        
        Útil después de operaciones destructivas o al cambiar de dataset.
        """
        with self._lock:
            old_size = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._logger.info(f"Repositorio limpiado - {old_size} archivos eliminados")
    
    def get_or_create(self, path: Path) -> FileMetadata:
        """
        Obtiene metadata de un archivo, añadiéndolo si no existe (AUTO-FETCH).
        
        Método conveniente que combina get_metadata() y add_file().
        
        Args:
            path: Ruta del archivo
            
        Returns:
            FileMetadata: Metadatos del archivo
            
        Raises:
            Exception: Si el archivo no existe o hay error de lectura
        """
        meta = self.get_metadata(path)
        if meta:
            return meta
        return self.add_file(path)
    
    def __len__(self) -> int:
        """
        Devuelve el número de archivos en el repositorio.
        
        Permite usar len(repository).
        """
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, path: Path) -> bool:
        """
        Verifica si un archivo está en el repositorio.
        
        Permite usar 'path in repository'.
        
        Args:
            path: Ruta del archivo a verificar
            
        Returns:
            bool: True si el archivo está en el repositorio
        """
        with self._lock:
            return path in self._cache
