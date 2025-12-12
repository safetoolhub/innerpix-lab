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
             create_metadata_cache: bool = True,
             precalculate_hashes: bool = False) -> DirectoryScanResult:
        """
        Escanea un directorio y clasifica archivos por tipo.
        Cuando create_metadata_cache=True, también extrae y cachea fechas EXIF.
        
        Args:
            directory: Directorio a escanear
            progress_callback: Función opcional (current, total, message) -> bool.
                             Retorna False para cancelar.
            create_metadata_cache: Si crear caché de metadatos completo.
            precalculate_hashes: Si pre-calcular hashes SHA256.
        
        Returns:
            DirectoryScanResult con archivos clasificados y caché opcional
        """
        # Validación temprana
        validate_directory_exists(directory)
        
        self.logger.info(f"Escaneando directorio: {directory}")
        
        # Obtener/crear instancia singleton del repositorio
        self.logger.info(f"DEBUG: create_metadata_cache={create_metadata_cache}")
        metadata_cache = None
        if create_metadata_cache:
            try:
                from services.file_info_repository import FileInfoRepository
                metadata_cache = FileInfoRepository.get_instance()
                self.logger.info(f"✅ Repositorio de archivos obtenido exitosamente")
                self.logger.info(f"  - Tipo: {type(metadata_cache).__name__}")
                self.logger.info(f"  - Max entries: {metadata_cache._max_entries:,}")
                self.logger.info(f"  - Habilitada: {metadata_cache._enabled}")
                self.logger.info(f"  - Archivos actuales: {metadata_cache.get_file_count()}")
            except Exception as e:
                self.logger.error(f"❌ ERROR obteniendo FileInfoRepository: {type(e).__name__}: {e}")
                import traceback
                self.logger.error(f"Traceback:\n{traceback.format_exc()}")
        else:
            self.logger.warning("⚠️  Repositorio de archivos NO usado (create_metadata_cache=False)")
        
        self.logger.info(f"DEBUG ANTES DE CONTAR: metadata_cache={'presente' if metadata_cache is not None else 'None'}")
        
        # Una sola iteración: clasificar directamente sin contar primero
        images, videos, others = [], [], []
        image_extensions = {}
        video_extensions = {}
        unsupported_extensions = {}
        unsupported_files = []
        processed = 0
        
        # Primera pasada: obtener lista de archivos para saber el total
        # Excluir explícitamente el archivo de caché de desarrollo
        all_files = [
            f for f in directory.rglob("*") 
            if f.is_file() and f.name != Config.DEV_CACHE_FILENAME
        ]
        total_files = len(all_files)
        
        # Actualizar límite de caché basándose en el número de archivos
        self.logger.info(f"📊 Archivos contados: {total_files:,}")
        if metadata_cache is not None:
            self.logger.info(f"🔄 Actualizando límite de caché basado en {total_files:,} archivos...")
            metadata_cache.update_max_entries(total_files)
        else:
            self.logger.warning("⚠️  NO se puede actualizar límite de caché (metadata_cache es None)")
        
        
        # Segunda pasada: clasificar archivos y cachear metadata completo
        scan_message = "Escaneando y calculando hashes (esto puede tardar...)" if precalculate_hashes else "Escaneando archivos y extrayendo metadatos"
        
        if precalculate_hashes:
            self.logger.warning(
                "⚠️  PRE-CÁLCULO DE HASHES ACTIVADO: El escaneo será más lento pero "
                "la fase de duplicados exactos será instantánea"
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
            
            # Cachear metadata
            if metadata_cache is not None:
                try:
                    stat_info = f.stat()
                    metadata_cache.set_basic_metadata(
                        path=f,
                        size=stat_info.st_size,
                        ctime=stat_info.st_ctime,
                        mtime=stat_info.st_mtime,
                        atime=stat_info.st_atime,
                        file_type=file_type
                    )
                    
                    # Para archivos de imagen y video, extraer y cachear TODAS las fechas
                    if file_type in ('image', 'video'):
                        try:
                            from utils.date_utils import get_all_file_dates
                            all_dates = get_all_file_dates(f)
                            if all_dates and any(all_dates.values()):
                                metadata_cache.set_all_dates(f, all_dates)
                        except Exception as e:
                            pass
                    
                    if precalculate_hashes and file_type in ('image', 'video'):
                        try:
                            file_hash = calculate_file_hash(f)
                            metadata_cache.set_hash(f, file_hash)
                            self.logger.debug(f"🔐 Hash pre-calculado: {f.name} = {file_hash[:8]}...")
                        except Exception as e:
                            self.logger.warning(f"Error calculando hash de {f}: {e}")
                            
                except Exception as e:
                    self.logger.warning(f"No se pudo cachear metadata de {f}: {e}")
            
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
            metadata_cache=metadata_cache,
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
            f"[{result.image_count:,} imágenes + {result.video_count:,} videos]"
        )
        self.logger.info(
            f"*** Archivos NO SOPORTADOS: {unsupported_count:,} ({unsupported_percentage:.1f}%) "
            f"- Extensiones: {ext_summary}"
        )
        
        if metadata_cache is not None:
            cache_stats = metadata_cache.get_stats()
            # Contar cuántas entradas tienen al menos una fecha EXIF
            exif_cached = sum(
                1 for m in metadata_cache._cache.values() 
                if m.exif_date_time_original or m.exif_create_date or m.exif_date_digitized
            )
            hashes_cached = sum(1 for m in metadata_cache._cache.values() if m.sha256_hash)
            self.logger.info(
                f"💾 Caché después del escaneo: "
                f"{cache_stats['size']} entradas, "
                f"{exif_cached} con fechas EXIF, "
                f"{hashes_cached} con hashes SHA256"
            )
            
            if precalculate_hashes and hashes_cached > 0:
                self.logger.info(
                    f"✅ Pre-cálculo de hashes completado: {hashes_cached} archivos "
                    "(la fase de duplicados exactos será instantánea)"
                )
            elif not precalculate_hashes:
                self.logger.info(
                    "ℹ️  Hashes NO pre-calculados (se calcularán en la fase de duplicados exactos)"
                )
        
        return result
