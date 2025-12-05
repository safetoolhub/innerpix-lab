"""
Sistema de caché compartida para metadatos de archivos.

Este módulo proporciona un sistema centralizado de caché para evitar recálculos
costosos de datos compartidos entre múltiples fases del análisis:

- Hashes SHA256: Usados por ExactCopiesDetector y HEICRemover
- Fechas EXIF: Extraídas por FileRenamer, útiles para FileOrganizer  
- Metadata básico: Tamaño, tipo, timestamps - usado por todas las fases

La caché se invalida automáticamente después de operaciones destructivas
(delete, move) para mantener consistencia.

Example:
    >>> cache = FileMetadataCache()
    >>> cache.set_hash(Path("photo.jpg"), "abc123...")
    >>> hash_value = cache.get_hash(Path("photo.jpg"))
    >>> cache.invalidate()  # Después de delete/move operations
"""

from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import time

from utils.logger import get_logger


@dataclass
class FileMetadata:
    """Metadatos cacheados de un archivo individual"""
    path: Path
    
    # Hash SHA256 para duplicados exactos
    sha256_hash: Optional[str] = None
    
    # Fechas EXIF extraídas (formato datetime)
    exif_date: Optional[datetime] = None
    exif_date_original: Optional[datetime] = None
    
    # Metadata básico del filesystem
    size: Optional[int] = None
    file_type: Optional[str] = None  # 'image', 'video', 'other'
    
    # Timestamps del filesystem
    modified_time: Optional[float] = None
    created_time: Optional[float] = None
    
    # Metadata de caché
    cached_at: float = field(default_factory=time.time)
    
    def is_valid(self, max_age_seconds: float = 3600) -> bool:
        """
        Verifica si la entrada de caché sigue siendo válida.
        
        Args:
            max_age_seconds: Edad máxima en segundos (default 1 hora)
            
        Returns:
            True si la caché es válida, False si expiró
        """
        age = time.time() - self.cached_at
        return age < max_age_seconds


class FileMetadataCache:
    """
    Caché compartida de metadatos de archivos para optimizar análisis.
    
    Esta caché evita recalcular datos costosos que son compartidos entre
    múltiples fases del análisis:
    
    - ExactCopiesDetector y HEICRemover comparten hashes SHA256
    - FileRenamer y FileOrganizer comparten fechas EXIF
    - Todos los servicios usan metadata básico (tamaño, tipo)
    
    La caché se invalida automáticamente después de operaciones que
    modifican archivos (delete, move, rename).
    
    Thread-safety: Esta implementación NO es thread-safe. Si se necesita
    uso concurrente, agregar locks.
    """
    
    def __init__(self, max_age_seconds: float = 3600):
        """
        Args:
            max_age_seconds: Tiempo de vida máximo de entradas (default 1 hora)
        """
        from config import Config
        import threading
        
        self.logger = get_logger('FileMetadataCache')
        self._cache: Dict[Path, FileMetadata] = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._max_age_seconds = max_age_seconds
        self._max_entries = Config.get_max_cache_entries()  # Dinámico según RAM
        self._enabled = True
        
        # Estadísticas de uso
        self._hits = 0
        self._misses = 0
        
        self.logger.debug(
            f"Caché de metadatos inicializada "
            f"(max_age={max_age_seconds}s, max_entries={self._max_entries}, "
            f"dinámico según RAM del sistema)"
        )
    
    def get_or_create(self, file_path: Path) -> FileMetadata:
        """
        Obtiene o crea entrada de caché para un archivo.
        Thread-safe.
        
        Args:
            file_path: Path del archivo
            
        Returns:
            FileMetadata (existente o nueva entrada vacía)
        """
        if not self._enabled:
            return FileMetadata(path=file_path)
        
        # Normalizar path
        file_path = file_path.resolve()
        
        with self._lock:
            # Verificar si existe y es válida
            if file_path in self._cache:
                metadata = self._cache[file_path]
                if metadata.is_valid(self._max_age_seconds):
                    self._hits += 1
                    return metadata
                else:
                    # Entrada expirada, remover
                    del self._cache[file_path]
            
            # Crear nueva entrada
            self._misses += 1
            metadata = FileMetadata(path=file_path)
            self._cache[file_path] = metadata
            self.logger.debug(f"✓ Nueva entrada de caché creada para {file_path.name} (total: {len(self._cache)} entradas)")
            
            # Limitar tamaño de caché para prevenir OOM
            if len(self._cache) > self._max_entries:
                self._evict_oldest_entries()
            
            return metadata
    
    def get_hash(self, file_path: Path) -> Optional[str]:
        """
        Obtiene hash SHA256 cacheado.
        
        Args:
            file_path: Path del archivo
            
        Returns:
            Hash SHA256 o None si no está cacheado
        """
        if not self._enabled:
            self.logger.debug("⚠️  get_hash() llamado pero caché está deshabilitada")
            return None
        
        file_path = file_path.resolve()
        with self._lock:
            if file_path in self._cache:
                metadata = self._cache[file_path]
                if metadata.is_valid(self._max_age_seconds):
                    self._hits += 1
                    if metadata.sha256_hash:
                        self.logger.debug(f"✓ CACHE HIT (hash): {file_path.name} (hits: {self._hits}, misses: {self._misses})")
                        return metadata.sha256_hash
                    else:
                        self.logger.debug(f"⚠️  CACHE HIT pero sin hash: {file_path.name}")
                        return None
                else:
                    # Entrada expirada, remover
                    del self._cache[file_path]
                    self._misses += 1
                    self.logger.debug(f"⚠️  CACHE EXPIRED: {file_path.name} (misses: {self._misses})")
            else:
                self._misses += 1
                self.logger.debug(f"❌ CACHE MISS (hash): {file_path.name} (hits: {self._hits}, misses: {self._misses})")
        return None
    
    def set_hash(self, file_path: Path, sha256_hash: str) -> None:
        """
        Cachea hash SHA256 de un archivo.
        
        Args:
            file_path: Path del archivo
            sha256_hash: Hash SHA256 calculado
        """
        if not self._enabled:
            self.logger.debug("⚠️  set_hash() llamado pero caché está deshabilitada")
            return
        
        metadata = self.get_or_create(file_path)
        metadata.sha256_hash = sha256_hash
        metadata.cached_at = time.time()
        self.logger.debug(f"✓ Hash cacheado para {file_path.name} (hash: {sha256_hash[:8]}...)")
    
    def get_exif_date(self, file_path: Path) -> Optional[datetime]:
        """
        Obtiene fecha EXIF cacheada.
        
        Args:
            file_path: Path del archivo
            
        Returns:
            Fecha EXIF o None si no está cacheada
        """
        if not self._enabled:
            return None
        
        file_path = file_path.resolve()
        with self._lock:
            if file_path in self._cache:
                metadata = self._cache[file_path]
                if metadata.is_valid(self._max_age_seconds):
                    self._hits += 1
                    return metadata.exif_date or metadata.exif_date_original
                else:
                    # Entrada expirada, remover
                    del self._cache[file_path]
                    self._misses += 1
            else:
                self._misses += 1
        return None
    
    def set_exif_dates(
        self, 
        file_path: Path, 
        exif_date: Optional[datetime] = None,
        exif_date_original: Optional[datetime] = None
    ) -> None:
        """
        Cachea fechas EXIF de un archivo.
        
        Args:
            file_path: Path del archivo
            exif_date: Fecha EXIF general
            exif_date_original: Fecha original de captura
        """
        if not self._enabled:
            return
        
        metadata = self.get_or_create(file_path)
        if exif_date:
            metadata.exif_date = exif_date
        if exif_date_original:
            metadata.exif_date_original = exif_date_original
        metadata.cached_at = time.time()
    
    def get_size(self, file_path: Path) -> Optional[int]:
        """
        Obtiene tamaño cacheado del archivo.
        
        Args:
            file_path: Path del archivo
            
        Returns:
            Tamaño en bytes o None si no está cacheado
        """
        if not self._enabled:
            return None
        
        file_path = file_path.resolve()
        with self._lock:
            if file_path in self._cache:
                metadata = self._cache[file_path]
                if metadata.is_valid(self._max_age_seconds):
                    self._hits += 1
                    return metadata.size
                else:
                    # Entrada expirada, remover
                    del self._cache[file_path]
                    self._misses += 1
            else:
                self._misses += 1
        return None
    
    def set_basic_metadata(
        self,
        file_path: Path,
        size: Optional[int] = None,
        file_type: Optional[str] = None,
        modified_time: Optional[float] = None,
        created_time: Optional[float] = None
    ) -> None:
        """
        Cachea metadata básico del filesystem.
        
        Args:
            file_path: Path del archivo
            size: Tamaño en bytes
            file_type: Tipo ('image', 'video', 'other')
            modified_time: Timestamp de modificación
            created_time: Timestamp de creación
        """
        if not self._enabled:
            return
        
        metadata = self.get_or_create(file_path)
        if size is not None:
            metadata.size = size
        if file_type is not None:
            metadata.file_type = file_type
        if modified_time is not None:
            metadata.modified_time = modified_time
        if created_time is not None:
            metadata.created_time = created_time
        metadata.cached_at = time.time()
    
    def invalidate(self, file_path: Optional[Path] = None) -> None:
        """
        Invalida caché completa o de un archivo específico.
        
        Debe llamarse después de operaciones destructivas:
        - Eliminación de archivos
        - Movimiento de archivos
        - Renombrado de archivos
        
        Args:
            file_path: Path específico a invalidar, o None para invalidar todo
        """
        with self._lock:
            if file_path:
                file_path = file_path.resolve()
                if file_path in self._cache:
                    del self._cache[file_path]
                    self.logger.debug(f"Caché invalidada para: {file_path}")
            else:
                count = len(self._cache)
                self._cache.clear()
                self._hits = 0
                self._misses = 0
                self.logger.info(f"Caché completa invalidada ({count} entradas)")
    
    def clear_cache(self) -> None:
        """
        Limpia la caché completamente.
        Alias para invalidate() sin argumentos.
        """
        self.invalidate()
    
    def _evict_oldest_entries(self, keep_ratio: float = 0.8) -> None:
        """
        Elimina las entradas más antiguas cuando se excede el límite.
        
        Args:
            keep_ratio: Ratio de entradas a mantener (default 0.8 = mantener 80%)
        """
        if not self._cache:
            return
        
        # Note: This method should be called within a lock
        target_size = int(self._max_entries * keep_ratio)
        if len(self._cache) <= target_size:
            return
        
        # Ordenar por cached_at y mantener las más recientes
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda item: item[1].cached_at,
            reverse=True
        )
        
        # Mantener solo las más recientes
        self._cache = dict(sorted_entries[:target_size])
        evicted = len(sorted_entries) - target_size
        
        self.logger.debug(
            f"Caché demasiado grande. Eliminadas {evicted} entradas antiguas "
            f"(quedan {len(self._cache)})"
        )
    
    
    def update_max_entries(self, file_count: int) -> None:
        """
        Actualiza el límite máximo de entradas basándose en el número de archivos.
        
        Este método debe llamarse después de contar los archivos en el directorio
        para optimizar el tamaño de la caché.
        
        Args:
            file_count: Número total de archivos en el directorio
        """
        from config import Config
        
        old_limit = self._max_entries
        new_limit = Config.get_max_cache_entries(file_count)
        
        # Always log the update attempt for debugging
        self.logger.info(
            f"Actualizando límite de caché: archivos={file_count:,}, "
            f"límite_actual={old_limit:,}, límite_calculado={new_limit:,}"
        )
        
        with self._lock:
            self._max_entries = new_limit
        
        if old_limit != new_limit:
            self.logger.info(
                f"✓ Límite de caché actualizado: {old_limit:,} → {new_limit:,}"
            )
        else:
            self.logger.debug(
                f"Límite de caché sin cambios: {old_limit:,}"
            )
    
    def disable(self) -> None:
        """Deshabilita la caché (útil para debugging o tests)"""
        self._enabled = False
        with self._lock:
            self._cache.clear()
        self.logger.debug("Caché deshabilitada")
    
    def enable(self) -> None:
        """Habilita la caché"""
        self._enabled = True
        self.logger.debug("Caché habilitada")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso de la caché.
        
        Returns:
            Dict con hits, misses, size, hit_rate
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                'enabled': self._enabled,
                'size': len(self._cache),
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'max_age_seconds': self._max_age_seconds
            }
    
    def log_stats(self) -> None:
        """Log de estadísticas de uso"""
        stats = self.get_stats()
        self.logger.info(
            f"📊 Estadísticas de caché: "
            f"{stats['hits']} hits, {stats['misses']} misses, "
            f"{stats['hit_rate']:.1f}% hit rate, "
            f"{stats['size']} entradas, "
            f"habilitada: {stats['enabled']}"
        )
    
    def __len__(self) -> int:
        """Retorna número de entradas en caché"""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, file_path: Path) -> bool:
        """Verifica si un archivo está en caché"""
        file_path = file_path.resolve()
        with self._lock:
            return file_path in self._cache

    def __getstate__(self):
        """
        Personaliza el estado para pickling.
        Excluye el lock que no es serializable.
        """
        state = self.__dict__.copy()
        # Eliminar lock del estado
        if '_lock' in state:
            del state['_lock']
        return state

    def __setstate__(self, state):
        """
        Restaura el estado desde pickle.
        Recrea el lock.
        """
        self.__dict__.update(state)
        # Recrear el lock
        import threading
        self._lock = threading.RLock()

