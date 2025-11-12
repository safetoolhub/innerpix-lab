"""
Servicio de detección de copias exactas mediante SHA256.
Identifica archivos 100% idénticos digitalmente comparando hashes criptográficos.
"""

from pathlib import Path
from typing import List, Optional
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.file_utils import calculate_file_hash
from utils.decorators import deprecated
from services.result_types import DuplicateAnalysisResult, DuplicateDeletionResult, DuplicateGroup
from services.base_detector_service import BaseDetectorService
from services.base_service import ProgressCallback


class ExactCopiesDetector(BaseDetectorService):
    """
    Servicio de detección de copias exactas mediante hashing SHA256.
    
    Identifica fotos y vídeos 100% idénticos digitalmente (mismo SHA256),
    incluso si tienen nombres diferentes. También conocidos como duplicados exactos.
    
    Hereda de BaseDetectorService para reutilizar lógica común de eliminación.
    """

    def __init__(self):
        """Inicializa el detector de copias exactas"""
        super().__init__('ExactCopiesDetector')

    def analyze(
        self,
        directory: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicateAnalysisResult:
        """
        Analiza directorio buscando duplicados exactos (SHA256)
        
        Args:
            directory: Directorio a analizar
            progress_callback: Callback de progreso
            
        Returns:
            DuplicateAnalysisResult con grupos de duplicados exactos
        """
        self._log_section_header("INICIANDO ANÁLISIS DE DUPLICADOS EXACTOS (SHA256)")
        
        # Recopilar archivos soportados (imágenes y videos)
        image_files = []
        for ext in Config.SUPPORTED_IMAGE_EXTENSIONS:
            image_files.extend(directory.rglob(f'*{ext}'))
        
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
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(calculate_file_hash, file_path, cache=hash_cache): file_path
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
                    if not self._report_progress(
                        progress_callback,
                        processed,
                        total_files,
                        f"Procesado: {file_path.name}"
                    ):
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
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
        self._log_section_footer("ANÁLISIS DE DUPLICADOS EXACTOS COMPLETADO")
        
        return DuplicateAnalysisResult(
            success=True,
            mode='exact',
            groups=groups,
            total_files=total_files,
            total_groups=total_groups,
            total_duplicates=total_duplicates,
            space_wasted=space_wasted
        )
