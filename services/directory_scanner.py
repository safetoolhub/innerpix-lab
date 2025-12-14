"""
Directory Scanner Service.
Handles the initial scan of the directory to populate FileInfoRepository
"""
from pathlib import Path
from typing import Optional, Callable, Dict, List
import logging

from config import Config
from utils.logger import get_logger
from utils.file_utils import calculate_file_hash, validate_directory_exists, get_file_stat_info
from services.file_info_repository import FileInfoRepository, PopulationStrategy
from services.result_types import DirectoryScanResult

class DirectoryScanner:
    """
    Handles scanning of a directory to collect file metadata.
    
    El escaneo se realiza en 3 fases:
    1. Obtención de lista de archivos
    2. Clasificación y extracción de metadatos
    3. Estadísticas finales
    """
    def __init__(self):
        self.logger = get_logger('DirectoryScanner')
    
    def _get_file_list(self, directory: Path) -> List[Path]:
        """
        FASE 1: Obtiene la lista completa de archivos en el directorio.
        
        Excluye archivos de caché de desarrollo.
        
        Args:
            directory: Directorio a escanear
            
        Returns:
            Lista de Path con todos los archivos encontrados
        """
        all_files = [
            f for f in directory.rglob("*") 
            if f.is_file() and f.name != Config.DEV_CACHE_FILENAME
        ]
        return all_files

    def scan(self, 
             directory: Path,
             progress_callback: Optional[Callable[[int, int, str], bool]] = None,
             use_file_info_repository: bool = True,
             precalculate_hashes: bool = False) -> DirectoryScanResult:
        """
        Escanea un directorio y clasifica archivos por tipo.
        Cuando use_file_info_repository=True, puebla el FileInfoRepository y extrae fechas EXIF.
        
        Args:
            directory: Directorio a escanear
            progress_callback: Función opcional (current, total, message) -> bool.
                             Retorna False para cancelar.
            use_file_info_repository: Si poblar FileInfoRepository con metadatos completos.
            precalculate_hashes: Si pre-calcular hashes SHA256 (más lento pero duplicados instantáneos).
        
        Returns:
            DirectoryScanResult con archivos clasificados y referencia al repositorio
        """
        # Validación temprana
        validate_directory_exists(directory)
        
        self.logger.info(f"Escaneando directorio: {directory}")
        
        # Obtener instancia singleton del repositorio
        repo = None
        if use_file_info_repository:
            try:
                repo = FileInfoRepository.get_instance()
                self.logger.info(f"FileInfoRepository obtenido: max_entries={repo._max_entries:,}, current_files={repo.count()}")
            except Exception as e:
                self.logger.error(f"ERROR obteniendo FileInfoRepository: {type(e).__name__}: {e}")
                import traceback
                self.logger.error(f"Traceback:\n{traceback.format_exc()}")
        else:
            self.logger.info("FileInfoRepository NO usado (use_file_info_repository=False)")
        
        # ==================== FASE 1: OBTENCIÓN DE LISTA DE ARCHIVOS ====================
        if progress_callback:
            progress_callback(0, 100, "Obteniendo lista de archivos")
        
        all_files = self._get_file_list(directory)
        total_files = len(all_files)
        
        self.logger.info(f"Archivos encontrados: {total_files:,}")
        
        # Actualizar límite del repositorio basándose en el número de archivos
        if repo is not None:
            repo.update_max_entries(total_files)
            self.logger.info(f"FileInfoRepository actualizado para {total_files:,} archivos")
        
        # Preparar estructuras de datos
        images, videos, others = [], [], []
        image_extensions = {}
        video_extensions = {}
        unsupported_extensions = {}
        unsupported_files = []
        
        # ==================== FASE 2: OBTENCIÓN DE METADATOS DE ARCHIVOS ====================
        scan_message = "Obteniendo metadatos de archivos"
        
        if precalculate_hashes:
            self.logger.warning(
                "PRE-CALCULO DE HASHES ACTIVADO: El escaneo sera mas lento pero "
                "la fase de duplicados exactos sera instantanea"
            )
        
        processed = 0
        for f in all_files:
            if progress_callback and not progress_callback(processed, total_files, scan_message):
                self.logger.warning("Escaneo cancelado por usuario")
                break
            
            # Obtener extensión (normalizar a lowercase)
            ext = f.suffix.lower() if f.suffix else '(sin extensión)'
            
            # Clasificar archivo
            from utils.file_utils import is_image_file, is_video_file
            if is_image_file(f.name):
                images.append(f)
                file_type = 'image'
                image_extensions[ext] = image_extensions.get(ext, 0) + 1
            elif is_video_file(f.name):
                videos.append(f)
                file_type = 'video'
                video_extensions[ext] = video_extensions.get(ext, 0) + 1
            else:
                others.append(f)
                file_type = 'other'
                unsupported_extensions[ext] = unsupported_extensions.get(ext, 0) + 1
                unsupported_files.append(f)
            
            processed += 1
            
            # Reportar progreso
            if progress_callback and processed % Config.UI_UPDATE_INTERVAL == 0:
                progress_callback(processed, total_files, scan_message)
        
        # Reportar progreso final de fase 2
        if progress_callback and total_files > 0:
            progress_callback(total_files, total_files, scan_message)
        
        # ==================== FASE 3: FINALIZANDO ANÁLISIS ====================
        if progress_callback:
            progress_callback(total_files, total_files, "Finalizando análisis")
        
        result = DirectoryScanResult(
            total_files=total_files,
            images=images,
            videos=videos,
            others=others,
            image_extensions=image_extensions,
            video_extensions=video_extensions,
            unsupported_extensions=unsupported_extensions,
            unsupported_files=unsupported_files
        )
        
        # Estadísticas de archivos soportados vs no soportados
        supported_count = result.image_count + result.video_count
        unsupported_count = result.other_count
        supported_percentage = (supported_count / total_files * 100) if total_files > 0 else 0
        unsupported_percentage = (unsupported_count / total_files * 100) if total_files > 0 else 0
        
        # Obtener extensiones de archivos no soportados
        unsupported_extensions = {}
        for f in others:
            ext = f.suffix.lower() if f.suffix else '(sin extensión)'
            unsupported_extensions[ext] = unsupported_extensions.get(ext, 0) + 1
        
        # Formatear extensiones para el log
        ext_summary = ', '.join(f"{ext} ({count})" for ext, count in sorted(unsupported_extensions.items()))
        if not ext_summary:
            ext_summary = "ninguna"
        
        self.logger.info(f"*** Escaneo completado: {total_files:,} archivos totales")
        self.logger.info(
            f"*** Archivos SOPORTADOS: {supported_count:,} ({supported_percentage:.1f}%) "
            f"[{result.image_count:,} imagenes + {result.video_count:,} videos]"
        )
        self.logger.info(
            f"*** Archivos NO SOPORTADOS: {unsupported_count:,} ({unsupported_percentage:.1f}%) "
            f"- Extensiones: {ext_summary}"
        )
        
        # Poblar FileInfoRepository si está habilitado
        if repo is not None:
            # Determinar estrategia de población
            if precalculate_hashes:
                strategy = PopulationStrategy.HASH
                self.logger.info("Poblando FileInfoRepository con hashes (pre-calculo activado)")
            else:
                strategy = PopulationStrategy.BASIC
                self.logger.info("Poblando FileInfoRepository con metadatos básicos")

            # Obtener archivos soportados para poblar el repositorio
            supported_files = images + videos

            try:
                repo.populate_from_scan(
                    files=supported_files,
                    strategy=strategy,
                    progress_callback=lambda current, total: progress_callback(current, total, "Poblando repositorio") if progress_callback else None
                )
                self.logger.info(f"FileInfoRepository poblado exitosamente con {len(supported_files)} archivos")
            except Exception as e:
                self.logger.error(f"Error poblando FileInfoRepository: {e}")
                import traceback
                self.logger.error(f"Traceback:\n{traceback.format_exc()}")

            # Mostrar estadísticas del repositorio poblado
            stats = repo.get_stats()
            self.logger.info(
                f"FileInfoRepository despues del escaneo: "
                f"{stats.total_files} entradas, "
                f"{stats.files_with_hash} con hashes SHA256"
            )

            if precalculate_hashes and stats.files_with_hash > 0:
                self.logger.info(
                    f"Pre-calculo de hashes completado: {stats.files_with_hash} archivos "
                    "(la fase de duplicados exactos sera instantanea)"
                )
            elif not precalculate_hashes:
                self.logger.info(
                    "Hashes NO pre-calculados (se calcularan en la fase de duplicados exactos)"
                )
        
        return result
