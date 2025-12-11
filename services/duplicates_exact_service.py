"""
Servicio de detección de copias exactas mediante SHA256.
Identifica archivos 100% idénticos digitalmente comparando hashes criptográficos.
"""

from pathlib import Path
from typing import List, Optional
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from config import Config
from utils.file_utils import calculate_file_hash
from services.result_types import DuplicateAnalysisResult, DuplicateDeletionResult, DuplicateGroup
from services.duplicates_base_service import DuplicatesBaseService
from services.base_service import BaseService, ProgressCallback
from services.metadata_cache import FileMetadataCache
from utils.logger import log_section_header_discrete, log_section_footer_discrete


def _is_valid_image_file(file_path: Path) -> bool:
    """
    Verifica si un archivo es una imagen válida usando PIL.
    
    Args:
        file_path: Ruta al archivo a verificar
        
    Returns:
        True si es una imagen válida, False en caso contrario
    """
    if not HAS_PIL:
        return False
    
    try:
        with Image.open(file_path) as img:
            img.verify()  # Verifica que sea una imagen válida
        return True
    except Exception:
        return False


class DuplicatesExactService(DuplicatesBaseService):
    """
    Servicio de detección de copias exactas mediante hashing SHA256.
    
    Identifica fotos y vídeos 100% idénticos digitalmente (mismo SHA256),
    incluso si tienen nombres diferentes. También conocidos como duplicados exactos.
    
    Hereda de BaseDetectorService para reutilizar lógica común de eliminación.
    """

    def __init__(self):
        """Inicializa el detector de copias exactas"""
        super().__init__('DuplicatesExactService')

    def analyze(
        self,
        directory: Path,
        progress_callback: Optional[ProgressCallback] = None,
        metadata_cache: Optional[FileMetadataCache] = None
    ) -> DuplicateAnalysisResult:
        """
        Analiza directorio buscando duplicados exactos (SHA256)
        
        Args:
            directory: Directorio a analizar
            progress_callback: Callback de progreso
            metadata_cache: Caché opcional de metadatos para reutilizar hashes SHA256
            
        Returns:
            DuplicateAnalysisResult con grupos de duplicados exactos
        """
        log_section_header_discrete(self.logger, "INICIANDO ANÁLISIS DE DUPLICADOS EXACTOS (SHA256)")
        
        # Log del estado de la caché recibida
        if metadata_cache is not None:
            cache_stats = metadata_cache.get_stats()
            self.logger.info(
                f"📦 Caché de metadatos recibida: "
                f"habilitada={cache_stats['enabled']}, "
                f"tamaño={cache_stats['size']} entradas, "
                f"hits={cache_stats['hits']}, "
                f"misses={cache_stats['misses']}, "
                f"hit_rate={cache_stats['hit_rate']:.1f}%"
            )
        else:
            self.logger.warning("⚠️  ¡SIN CACHÉ! metadata_cache es None - se calcularán todos los hashes desde cero")
        
        # Recopilar archivos soportados (imágenes y videos)
        image_files = []
        for ext in Config.SUPPORTED_IMAGE_EXTENSIONS:
            image_files.extend(directory.rglob(f'*{ext}'))
        
        # También buscar archivos que puedan ser imágenes válidas aunque tengan extensiones no estándar
        if HAS_PIL:
            self.logger.debug("Buscando archivos que puedan ser imágenes válidas con extensiones no estándar")
            potential_images = []
            
            for file_path in directory.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() in Config.SUPPORTED_IMAGE_EXTENSIONS:
                    continue
                # Solo verificar archivos que no sean muy grandes (para evitar archivos binarios grandes)
                if file_path.stat().st_size < 100 * 1024 * 1024:  # Menos de 100MB
                    if _is_valid_image_file(file_path):
                        potential_images.append(file_path)
                        self.logger.debug(f"Imagen válida encontrada con extensión no estándar: {file_path.name}")
            
            image_files.extend(potential_images)
            if potential_images:
                self.logger.info(f"Archivos de imagen adicionales encontrados: {len(potential_images)}")
        
        video_files = []
        for ext in Config.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(directory.rglob(f'*{ext}'))
        
        files = image_files + video_files
        total_files = len(files)
        self.logger.info(f"Archivos a procesar: {total_files} ({len(image_files)} imágenes, {len(video_files)} videos)")
        
        if total_files == 0:
            return DuplicateAnalysisResult(
                success=True,
                mode='exact',
                groups=[],
                total_files=0,
                total_groups=0,
                total_duplicates=0,
                space_wasted=0
            )
        
        # Calcular hashes en paralelo con caché compartido
        # El caché permite reutilizar hashes si se analiza el mismo directorio múltiples veces
        hash_cache = {}
        file_hashes = {}
        processed = 0
        
        # Función auxiliar para calcular hash con caché de metadatos
        def get_file_hash(file_path):
            """Obtiene hash desde metadata_cache o calcula si no existe"""
            # Intentar obtener de caché de metadatos primero
            if metadata_cache:
                cached_hash = metadata_cache.get_hash(file_path)
                if cached_hash:
                    self.logger.debug(f"✅ Hash obtenido de CACHÉ: {file_path.name} = {cached_hash[:8]}...")
                    return cached_hash
                else:
                    self.logger.debug(f"🔍 Calculando hash (no en caché): {file_path.name}")
            else:
                self.logger.debug(f"⚠️  Calculando hash (SIN caché disponible): {file_path.name}")
            
            # Calcular hash (usa hash_cache interno de la sesión)
            file_hash = calculate_file_hash(file_path, cache=hash_cache)
            
            # Cachear en metadata_cache para futuros usos
            if file_hash and metadata_cache:
                metadata_cache.set_hash(file_path, file_hash)
                self.logger.debug(f"💾 Hash calculado y guardado en caché: {file_path.name} = {file_hash[:8]}...")
            
            return file_hash
        
        # Calcular hash en paralelo usando método centralizado
        with self._parallel_processor(io_bound=True) as executor:
            future_to_file = {
                executor.submit(get_file_hash, file_path): file_path
                for file_path in files
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        if file_hash not in file_hashes:
                            file_hashes[file_hash] = []
                        file_hashes[file_hash].append(file_path)
                    
                    processed += 1
                    if processed % Config.UI_UPDATE_INTERVAL == 0 and not self._report_progress(
                        progress_callback,
                        processed,
                        total_files,
                        f"Procesado: {file_path.name}"
                    ):
                        break  # Salir del loop, el with hace shutdown limpio
                except Exception as e:
                    self.logger.error(f"Error calculando hash de {file_path}: {e}")
        
        # Crear grupos de duplicados (solo hashes con 2+ archivos)
        groups = []
        for hash_value, file_list in file_hashes.items():
            if len(file_list) > 1:
                group = DuplicateGroup(
                    hash_value=hash_value,
                    files=file_list,
                    total_size=sum(f.stat().st_size for f in file_list),
                    similarity_score=100.0  # Duplicados exactos siempre 100%
                )
                groups.append(group)
        
        # Calcular estadísticas
        total_groups = len(groups)
        total_duplicates = sum(len(g.files) - 1 for g in groups)  # Total de duplicados
        space_wasted = sum(
            (len(g.files) - 1) * g.files[0].stat().st_size
            for g in groups
        )
        
        # Logging de resumen con formato estandarizado
        from utils.format_utils import format_size
        self.logger.info(f"*** Archivos analizados: {total_files}")
        self.logger.info(f"*** Grupos de duplicados: {total_groups}")
        self.logger.info(f"*** Duplicados encontrados: {total_duplicates}")
        self.logger.info(f"*** Espacio potencialmente recuperable: {format_size(space_wasted)}")
        
        # Log de estadísticas de caché al final
        if metadata_cache is not None:
            cache_stats = metadata_cache.get_stats()
            self.logger.info(
                f"📊 Estadísticas de caché al finalizar: "
                f"hits={cache_stats['hits']}, "
                f"misses={cache_stats['misses']}, "
                f"hit_rate={cache_stats['hit_rate']:.1f}%, "
                f"tamaño final={cache_stats['size']} entradas"
            )
        
        log_section_footer_discrete(self.logger, "ANÁLISIS DE DUPLICADOS EXACTOS COMPLETADO")
        
        return DuplicateAnalysisResult(
            success=True,
            mode='exact',
            groups=groups,
            total_files=total_files,
            total_groups=total_groups,
            total_duplicates=total_duplicates,
            space_wasted=space_wasted
        )
