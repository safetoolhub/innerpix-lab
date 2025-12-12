"""
Servicio de detección de copias exactas mediante SHA256.
Identifica archivos 100% idénticos digitalmente comparando hashes criptográficos.
Refactorizado para usar MetadataCache.
"""

from pathlib import Path
from typing import List, Optional, Dict
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from config import Config
from services.result_types import DuplicateAnalysisResult, DuplicateGroup
from services.duplicates_base_service import DuplicatesBaseService
from services.base_service import ProgressCallback
from services.file_info_repository import MetadataCache, FileMetadata
from utils.logger import log_section_header_discrete, log_section_footer_discrete


def _is_valid_image_file(filename: str) -> bool:
    """Helper for backward compatibility with tests"""
    return Config.is_image_file(filename) or Config.is_supported_file(filename)



class DuplicatesExactService(DuplicatesBaseService):
    """
    Servicio de detección de copias exactas mediante hashing SHA256.
    """

    def __init__(self):
        """Inicializa el detector de copias exactas"""
        super().__init__('DuplicatesExactService')

    def analyze(
        self,
        metadata_cache: MetadataCache,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> DuplicateAnalysisResult:
        """
        Analiza buscando duplicados exactos (SHA256) usando la caché de metadatos.
        
        Args:
            metadata_cache: Caché con metadatos de archivos
            progress_callback: Callback de progreso
            **kwargs: Args adicionales
            
        Returns:
            DuplicateAnalysisResult con grupos de duplicados exactos
        """
        log_section_header_discrete(self.logger, "INICIANDO ANÁLISIS DE DUPLICADOS EXACTOS (SHA256)")
        
        all_files = metadata_cache.get_all_files()
        total_files = len(all_files)
        self.logger.info(f"Escaneando {total_files} archivos en caché para detección de duplicados")
        
        if total_files == 0:
            return DuplicateAnalysisResult(groups=())
            
        # Filtrar candidatos (imágenes y videos soportados)
        candidates: List[FileMetadata] = []
        supported_exts = Config.SUPPORTED_IMAGE_EXTENSIONS | Config.SUPPORTED_VIDEO_EXTENSIONS
        
        # Mapeo por tamaño para optimización preliminar (si tamaños difieren, no pueden ser iguales)
        # Aunque para exactas usamos SHA256, podemos evitar hashear si el tamaño es único?
        # Sí, si un archivo tiene un tamaño único, no puede tener duplicado.
        
        by_size = metadata_cache.get_files_by_size()
        
        # Solo necesitamos procesar archivos que comparten tamaño con al menos otro archivo
        files_to_hash = []
        for size, files in by_size.items():
            if len(files) > 1:
                # Solo considerar tipos soportados o validar si es imagen
                for meta in files:
                    ext = meta.extension
                    if ext in supported_exts:
                        files_to_hash.append(meta)
                    elif HAS_PIL and meta.size < 100 * 1024 * 1024:
                        # Lógica legacy para detectar imágenes con ext extraña
                         # Esto requiere acceso a disco, cuidado
                        pass 
                        # Por ahora simplificamos: solo soportados o ya conocidos
                        # Si queremos mantener la lógica PIL exacta, tendríamos que re-implementarla aquí
                        # pero implica I/O. Asumiremos standard extensions por eficiencia en V2
                
        # Si queremos ser estrictos con la lógica anterior:
        # El código anterior escaneaba TODO.
        # Aquí optimizamos: solo hasheamos si hay colisión de tamaño.
        
        self.logger.info(f"Candidatos a duplicados (por coincidencia de tamaño): {len(files_to_hash)}")
        
        file_hashes: Dict[str, List[Path]] = {}
        processed = 0
        total_to_hash = len(files_to_hash)
        
        # Definir función para worker
        def get_hash_task(meta: FileMetadata):
            # metadata_cache.get_hash usa lock internamente para lectura/escritura de cache
            # pero el cálculo es lazy.
            return metadata_cache.get_hash(meta.path), meta.path

        # Calcular hashes en paralelo
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_path = {
                executor.submit(get_hash_task, meta): meta.path
                for meta in files_to_hash
            }
            
            for future in as_completed(future_to_path):
                try:
                    hash_val, path = future.result()
                    if hash_val:
                        if hash_val not in file_hashes:
                            file_hashes[hash_val] = []
                        file_hashes[hash_val].append(path)
                except Exception as e:
                    self.logger.error(f"Error obteniendo hash: {e}")
                
                processed += 1
                if self._should_report_progress(processed, interval=Config.UI_UPDATE_INTERVAL):
                     if not self._report_progress(progress_callback, processed, total_to_hash, "Calculando firmas digitales..."):
                         break

        # Crear grupos
        groups = []
        for hash_mid, paths in file_hashes.items():
            if len(paths) > 1:
                # Calcular tamaño total del grupo
                # paths es List[Path], necesitamos size.
                # Podemos obtenerlo de meta o disk. Meta es mejor.
                # Pero paths solo tiene Path. 
                # Recuperar size del primer path (todos iguales en contenido => tamaño igual)
                first_meta = metadata_cache.get_metadata(paths[0])
                size = first_meta.size if first_meta else paths[0].stat().st_size
                
                groups.append(DuplicateGroup(
                    hash_value=hash_mid,
                    files=paths,
                    total_size=size * len(paths),
                    similarity_score=100.0
                ))
        
        # Calcular estadísticas
        total_groups = len(groups)
        total_duplicates = sum(len(g.files) - 1 for g in groups)
        space_wasted = sum((len(g.files) - 1) * (g.total_size // len(g.files)) for g in groups)
        
        from utils.format_utils import format_size
        self.logger.info(f"*** Grupos encontrados: {total_groups}")
        self.logger.info(f"*** Espacio recuperable: {format_size(space_wasted)}")
        
        log_section_footer_discrete(self.logger, "ANÁLISIS DE DUPLICADOS EXACTOS COMPLETADO")
        
        return DuplicateAnalysisResult(
            groups=groups,
            total_duplicates=total_duplicates,
            total_groups=total_groups, # Added field
            total_files=total_files,
            space_wasted=space_wasted
        )
