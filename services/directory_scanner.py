"""
Directory Scanner Service.
Handles the initial scan of the directory to populate metadata cache.
"""
from pathlib import Path
from typing import Optional, Callable, Dict, List
import logging

from config import Config
from utils.logger import get_logger
from utils.file_utils import calculate_file_hash, validate_directory_exists
from services.file_info_repository import FileInfoRepository
from services.result_types import DirectoryScanResult

class DirectoryScanner:
    """
    Handles scanning of a directory to collect file metadata.
    """
    def __init__(self):
        self.logger = get_logger('DirectoryScanner')

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
                self.logger.info(f"FileInfoRepository obtenido: max_entries={repo._max_entries:,}, enabled={repo._enabled}, current_files={repo.get_file_count()}")
            except Exception as e:
                self.logger.error(f"ERROR obteniendo FileInfoRepository: {type(e).__name__}: {e}")
                import traceback
                self.logger.error(f"Traceback:\n{traceback.format_exc()}")
        else:
            self.logger.info("FileInfoRepository NO usado (use_file_info_repository=False)")
        
        # Preparar estructuras de datos
        images, videos, others = [], [], []
        image_extensions = {}
        video_extensions = {}
        unsupported_extensions = {}
        unsupported_files = []
        processed = 0
        
        # Primera pasada: obtener lista de archivos (excluir archivo de caché de desarrollo)
        all_files = [
            f for f in directory.rglob("*") 
            if f.is_file() and f.name != Config.DEV_CACHE_FILENAME
        ]
        total_files = len(all_files)
        
        self.logger.info(f"Archivos encontrados: {total_files:,}")
        
        # Actualizar límite del repositorio basándose en el número de archivos
        if repo is not None:
            repo.update_max_entries(total_files)
            self.logger.info(f"FileInfoRepository actualizado para {total_files:,} archivos")
        
        
        # Segunda pasada: clasificar archivos y poblar repositorio con metadatos completos
        scan_message = "Escaneando y calculando hashes (esto puede tardar...)" if precalculate_hashes else "Escaneando archivos y extrayendo metadatos"
        
        if precalculate_hashes:
            self.logger.warning(
                "PRE-CALCULO DE HASHES ACTIVADO: El escaneo sera mas lento pero "
                "la fase de duplicados exactos sera instantanea"
            )
        
        for f in all_files:
            if progress_callback and not progress_callback(processed, total_files, scan_message):
                self.logger.warning("Escaneo cancelado por usuario")
                break
            
            # Obtener extensión (normalizar a lowercase)
            ext = f.suffix.lower() if f.suffix else '(sin extensión)'
            
            # Clasificar archivo
            if Config.is_image_file(f.name):
                images.append(f)
                file_type = 'image'
                image_extensions[ext] = image_extensions.get(ext, 0) + 1
            elif Config.is_video_file(f.name):
                videos.append(f)
                file_type = 'video'
                video_extensions[ext] = video_extensions.get(ext, 0) + 1
            else:
                others.append(f)
                file_type = 'other'
                unsupported_extensions[ext] = unsupported_extensions.get(ext, 0) + 1
                unsupported_files.append(f)
            
            # Poblar repositorio con metadatos
            if repo is not None:
                try:
                    stat_info = f.stat()
                    repo.set_basic_metadata(
                        path=f,
                        size=stat_info.st_size,
                        ctime=stat_info.st_ctime,
                        mtime=stat_info.st_mtime,
                        atime=stat_info.st_atime,
                        file_type=file_type
                    )
                    
                    # Para archivos de imagen y video, extraer y cachear TODAS las fechas EXIF
                    exif_dates = None
                    if file_type in ('image', 'video'):
                        try:
                            from utils.date_utils import get_all_file_dates
                            all_dates = get_all_file_dates(f)
                            if all_dates and any(all_dates.values()):
                                repo.set_all_dates(f, all_dates)
                                exif_dates = [k for k, v in all_dates.items() if v]
                        except Exception as e:
                            pass
                    
                    # Pre-calcular hash si está habilitado
                    file_hash = None
                    if precalculate_hashes and file_type in ('image', 'video'):
                        try:
                            file_hash = calculate_file_hash(f)
                            repo.set_hash(f, file_hash)
                        except Exception as e:
                            self.logger.warning(f"Error calculando hash de {f}: {e}")
                    
                    # Log detallado en modo DEBUG usando get_file_info_in_one_line()
                    if self.logger.isEnabledFor(logging.DEBUG):
                        file_info = repo.get_metadata(f)
                        if file_info:
                            self.logger.debug(file_info.get_file_info_in_one_line(verbose=True))
                            
                except Exception as e:
                    self.logger.warning(f"No se pudo poblar repositorio para {f}: {e}")
            
            processed += 1
            
            # Reportar progreso
            if progress_callback and processed % Config.UI_UPDATE_INTERVAL == 0:
                progress_callback(processed, total_files, scan_message)
        
        # Reportar progreso final (100%)
        if progress_callback and total_files > 0:
            progress_callback(total_files, total_files, scan_message)
        
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
        
        if repo is not None:
            stats = repo.get_stats()
            # Contar cuántas entradas tienen al menos una fecha EXIF o hash
            exif_cached = sum(
                1 for m in repo._cache.values() 
                if m.exif_date_time_original or m.exif_create_date or m.exif_date_digitized
            )
            hashes_cached = sum(1 for m in repo._cache.values() if m.sha256)
            self.logger.info(
                f"FileInfoRepository despues del escaneo: "
                f"{stats['size']} entradas, "
                f"{exif_cached} con fechas EXIF, "
                f"{hashes_cached} con hashes SHA256"
            )
            
            if precalculate_hashes and hashes_cached > 0:
                self.logger.info(
                    f"Pre-calculo de hashes completado: {hashes_cached} archivos "
                    "(la fase de duplicados exactos sera instantanea)"
                )
            elif not precalculate_hashes:
                self.logger.info(
                    "Hashes NO pre-calculados (se calcularan en la fase de duplicados exactos)"
                )
        
        return result
