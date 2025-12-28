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
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from utils.logger import log_section_header_discrete, log_section_footer_discrete


def _is_valid_image_file(filename: str) -> bool:
    """Helper for backward compatibility with tests"""
    from utils.file_utils import is_image_file, is_supported_file
    return is_image_file(filename) or is_supported_file(filename)



class DuplicatesExactService(DuplicatesBaseService):
    """
    Servicio de detección de copias exactas mediante hashing SHA256.
    """

    def __init__(self):
        """Inicializa el detector de copias exactas"""
        super().__init__('DuplicatesExactService')

    def analyze(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> DuplicateAnalysisResult:
        """
        Analiza buscando duplicados exactos (SHA256) usando FileInfoRepository.
        
        Args:
            progress_callback: Callback de progreso
            **kwargs: Args adicionales
            
        Returns:
            DuplicateAnalysisResult con grupos de duplicados exactos
        """
        # Obtener FileInfoRepositoryCache
        repo = FileInfoRepositoryCache.get_instance()
        
        log_section_header_discrete(self.logger, "INICIANDO ANÁLISIS DE DUPLICADOS EXACTOS (SHA256)")
        
        all_files = repo.get_all_files()
        total_files = len(all_files)
        self.logger.info(f"Escaneando {total_files} archivos en FileInfoRepositoryCache para detección de duplicados")
        
        if total_files == 0:
            return DuplicateAnalysisResult(groups=())
            
        # Filtrar candidatos (imágenes y videos soportados)
        candidates: List[FileMetadata] = []
        supported_exts = Config.SUPPORTED_IMAGE_EXTENSIONS | Config.SUPPORTED_VIDEO_EXTENSIONS
        
        # Mapeo por tamaño para optimización preliminar (si tamaños difieren, no pueden ser iguales)
        # Aunque para exactas usamos SHA256, podemos evitar hashear si el tamaño es único?
        # Sí, si un archivo tiene un tamaño único, no puede tener duplicado.
        
        by_size = repo.get_files_by_size()
        
        # Solo necesitamos procesar archivos que comparten tamaño con al menos otro archivo
        files_to_hash = []
        for size, files in by_size.items():
            if len(files) > 1:
                # Solo considerar tipos soportados o validar si es imagen
                for meta in files:
                    ext = meta.extension
                    if ext in supported_exts:
                        files_to_hash.append(meta)
                    elif HAS_PIL and meta.fs_size < 100 * 1024 * 1024:
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
        
        # 1. Poblar cache con hashes (Explicitamente)
        # Esto delega la paralelización y el cálculo al repositorio
        failed_hashes = []
        if files_to_hash:
            # Filter files that already have a hash in the cache to avoid re-processing overhead
            files_missing_hash = []
            files_cached_hash = 0
            
            self.logger.info("Verificando caché de hashes...")
            
            for meta in files_to_hash:
                if meta.sha256:
                    files_cached_hash += 1
                else:
                    files_missing_hash.append(meta.path)
            
            if files_cached_hash > 0:
                self.logger.info(f"Hashes encontrados en caché: {files_cached_hash} (se omitirá cálculo)")
                
            if files_missing_hash:
                 self.logger.info(f"Archivos requiriendo cálculo de hash: {len(files_missing_hash)}")
                 
                 # Adaptador para reportar progreso
                 # populate_from_scan llama a callback(processed, total)
                 def repo_progress_callback(processed_count, total_count):
                     # Log inmediato inicial y luego periódico
                     if processed_count == 0 or (processed_count % 1000 == 0):
                         self.logger.info(f"Hashing progreso: {processed_count}/{total_count} archivos procesados")
                         
                     return self._report_progress(
                         progress_callback, 
                         processed_count, 
                         total_count, 
                         "Calculando firmas digitales..."
                     )
    
                 # Iniciar población solo para faltantes
                 from services.file_metadata_repository_cache import PopulationStrategy
                 repo.populate_from_scan(
                     files_missing_hash, 
                     strategy=PopulationStrategy.HASH,
                     max_workers=4,
                     progress_callback=repo_progress_callback,
                     stop_check_callback=lambda: self._should_stop_check() if hasattr(self, '_should_stop_check') else False
                 )
            else:
                 self.logger.info("Todos los archivos candidatos ya tienen hash en caché.")

        # 2. Recolectar resultados de la caché (si no estaban antes ahora sí estarán)
        processed = 0
        for meta in files_to_hash:
            hash_val = repo.get_hash(meta.path)
            if hash_val:
                if hash_val not in file_hashes:
                    file_hashes[hash_val] = []
                file_hashes[hash_val].append(meta.path)
            else:
                 # Si después de populate no hay hash, es un error de lectura o permiso
                 failed_hashes.append(meta.path)
            
            processed += 1
            # Progreso ligero durante la recolección
            if self._should_report_progress(processed, interval=Config.UI_UPDATE_INTERVAL * 2):
                if processed % 10000 == 0:
                    self.logger.info(f"Agrupando duplicados: {processed}/{len(files_to_hash)} revisados")
                    
                if not self._report_progress(progress_callback, processed, len(files_to_hash), "Agrupando duplicados..."):
                    break # Cancelado

        # Crear grupos
        groups = []
        for hash_mid, paths in file_hashes.items():
            if len(paths) > 1:
                # Calcular tamaño total del grupo
                # paths es List[Path], necesitamos size.
                # Podemos obtenerlo de meta o disk. Meta es mejor.
                # Pero paths solo tiene Path. 
                # Recuperar size del primer path (todos iguales en contenido => tamaño igual)
                first_meta = repo.get_file_metadata(paths[0])
                size = first_meta.fs_size if first_meta else paths[0].stat().st_size
                
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
