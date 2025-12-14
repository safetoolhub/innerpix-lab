"""
Servicio unificado de Live Photos - Detección y limpieza consolidados

Este servicio fusiona LivePhotoDetector y LivePhotoCleaner en una sola clase
para simplificar la API y eliminar duplicación de código.
Refactorizado para usar MetadataCache.
"""
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable, Dict, Tuple
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from config import Config
from utils.date_utils import get_date_from_file
from services.result_types import LivePhotosAnalysisResult, LivePhotosExecutionResult
from services.base_service import BaseService, BackupCreationError
from services.file_info_repository import FileInfoRepository
from utils.logger import log_section_header_discrete, log_section_footer_discrete, log_section_header_relevant, log_section_footer_relevant, get_logger


@dataclass
class LivePhotoGroup:
    """Representa un grupo de Live Photo detectado"""
    image_path: Path
    video_path: Path
    base_name: str
    directory: Path
    image_size: int
    video_size: int
    image_date: Optional[datetime] = None
    video_date: Optional[datetime] = None
    image_date_source: str = "unknown"
    video_date_source: str = "unknown"
    file_info_repo: Optional[FileInfoRepository] = None

    def __post_init__(self):
        """Validaciones y cálculos adicionales"""
        if not self.image_path.exists():
            raise ValueError(f"Imagen no existe: {self.image_path}")
        if not self.video_path.exists():
            raise ValueError(f"Video no existe: {self.video_path}")
        
        # VALIDACIÓN CRÍTICA: Verificar que imagen y video están en el mismo directorio
        if self.image_path.parent != self.video_path.parent:
            raise ValueError(
                f"Live Photo inválido: imagen y video deben estar en el mismo directorio. "
                f"Imagen: {self.image_path.parent}, Video: {self.video_path.parent}"
            )
        
        # Verificar que el directorio almacenado coincide
        if self.directory != self.image_path.parent:
            raise ValueError(
                f"Inconsistencia en directorio: directory={self.directory}, "
                f"pero image está en {self.image_path.parent}"
            )
        
        # Las fechas se calculan lazy (solo cuando se accede a time_difference)

    def _ensure_dates_loaded(self) -> bool:
        """
        Intenta cargar fechas desde caché o calcularlas si es necesario.
        """
        if not self.image_date:
            # Primero intentar desde caché
            if self.file_info_repo:
                cached_date, source = self.file_info_repo.get_selected_date(self.image_path)
                if cached_date:
                    self.image_date = cached_date
                    self.image_date_source = source
            
            # Si no hay caché o no estaba cacheado, calcular
            if not self.image_date:
                if self.file_info_repo:
                    # Con cache disponible: usar fallback rápido
                    self.image_date = get_date_from_file(self.image_path, metadata_cache=self.file_info_repo, skip_expensive_ops=True)
                    self.image_date_source = "mtime_fallback"
                else:
                    self.image_date = get_date_from_file(self.image_path)
                    self.image_date_source = "test_calculation"
                    if not self.image_date:
                        self.image_date = datetime.fromtimestamp(self.image_path.stat().st_mtime)
                        self.image_date_source = "mtime"
        
        if not self.video_date:
            # Primero intentar desde caché
            if self.file_info_repo:
                cached_date, source = self.file_info_repo.get_selected_date(self.video_path)
                if cached_date:
                    self.video_date = cached_date
                    self.video_date_source = source
            
            # Si no hay caché o no estaba cacheado, calcular
            if not self.video_date:
                if self.file_info_repo:
                    self.video_date = get_date_from_file(self.video_path, metadata_cache=self.file_info_repo, skip_expensive_ops=True)
                    self.video_date_source = "mtime_fallback"
                else:
                    self.video_date = get_date_from_file(self.video_path)
                    self.video_date_source = "test_calculation"
                    if not self.video_date:
                        self.video_date = datetime.fromtimestamp(self.video_path.stat().st_mtime)
                        self.video_date_source = "mtime"
        
        return self.image_date is not None and self.video_date is not None
    
    @property
    def total_size(self) -> int:
        return self.image_size + self.video_size

    def _is_filesystem_source(self, source: str) -> bool:
        if not source: return False
        s = source.lower()
        return 'mtime' in s or 'ctime' in s or 'filesystem' in s or 'fallback' in s

    def _is_exif_source(self, source: str) -> bool:
        if not source: return False
        s = source.lower()
        return 'exif' in s

    def get_comparison_dates(self) -> Tuple[datetime, datetime, str, str]:
        """Obtiene las fechas ajustadas para comparación justa."""
        if not self._ensure_dates_loaded():
            return None, None, "unavailable", "unavailable"
        
        img_date = self.image_date
        img_source = self.image_date_source
        vid_date = self.video_date
        vid_source = self.video_date_source
        
        # REGLA CRÍTICA: Si el video usa mtime, forzar mtime también en imagen
        if self._is_filesystem_source(vid_source) and self._is_exif_source(img_source):
            try:
                mtime_date = None
                if self.file_info_repo:
                    # El método correcto en cache es get_file_stats que incluye mtime
                    # Assuming file_info_repo (FileInfoRepository) has get_file_metadata returning FileMetadata with mtime
                    meta = self.file_info_repo.get_file_metadata(self.image_path)
                    if meta:
                        mtime_date = datetime.fromtimestamp(meta.fs_mtime)
                
                if not mtime_date:
                    mtime_date = datetime.fromtimestamp(self.image_path.stat().st_mtime)
                
                if mtime_date:
                    img_date = mtime_date
                    img_source = f"{img_source}→mtime_adjusted"
            except Exception:
                pass
        
        return img_date, vid_date, img_source, vid_source

    @property
    def time_difference(self) -> float:
        """Diferencia en segundos entre imagen y video."""
        img_date, vid_date, _, _ = self.get_comparison_dates()
        if img_date and vid_date:
            return abs((img_date - vid_date).total_seconds())
        return 0.0


class CleanupMode(Enum):
    KEEP_IMAGE = "keep_image"
    KEEP_VIDEO = "keep_video"
    KEEP_LARGER = "keep_larger"
    KEEP_SMALLER = "keep_smaller"
    CUSTOM = "custom"


class LivePhotoService(BaseService):
    """
    Servicio unificado de Live Photos: detección y limpieza.
    """

    def __init__(self):
        super().__init__("LivePhotoService")

        # Extensiones para Live Photos
        self.photo_extensions = {ext.upper() for ext in {'.heic', '.jpg', '.jpeg'}}
        self.video_extensions = {'.MOV'}
        
        self.logger.info(f"Extensiones de foto configuradas: {self.photo_extensions}")
        self.logger.info(f"Extensiones de video configuradas: {self.video_extensions}")

        self.time_tolerance = 5.0

    def analyze(
        self, 
        cleanup_mode: CleanupMode = CleanupMode.KEEP_IMAGE,
        progress_callback: Optional[Callable[[int, int, str], bool]] = None,
        **kwargs
    ) -> LivePhotosAnalysisResult:
        """
        Analiza Live Photos usando FileInfoRepository.
        
        Args:
            cleanup_mode: Modo de limpieza a aplicar
            progress_callback: Callback de progreso
            **kwargs: Args adicionales
        """
        # Obtener FileInfoRepository
        repo = FileInfoRepository.get_instance()
        
        # Extraer directory de kwargs si existe, aunque usaremos repo.
        # Si orchestator pasa directory, lo usaremos para loggear.
        directory = kwargs.get('directory', Path('.')) 
        
        log_section_header_discrete(self.logger, "ANÁLISIS DE LIVE PHOTOS")
        self.logger.info(f"Usando FileInfoRepository con {repo.get_file_count()} archivos")
        self.logger.info(f"Modo de limpieza: {cleanup_mode.value}")

        # Paso 1: Detectar Live Photos
        live_photos = self._detect_in_directory(progress_callback)
        
        if live_photos is None: # Cancelado
            return self._create_empty_result(cleanup_mode)

        if not live_photos:
            self.logger.info("No se encontraron Live Photos")
            return self._create_empty_result(cleanup_mode)

        # Paso 2: Generar plan de limpieza según el modo
        cleanup_plan = self._generate_cleanup_plan(live_photos, cleanup_mode)

        # Paso 3: Calcular estadísticas
        total_space = sum(lp.total_size for lp in live_photos)
        space_to_free = sum(item['size'] for item in cleanup_plan['files_to_delete'])

        result = LivePhotosAnalysisResult(
            items_count=len(live_photos),
            groups=live_photos,
            bytes_total=total_space,
            space_to_free=space_to_free,
            total_space=total_space,
            data={
                'files_to_delete': cleanup_plan['files_to_delete'],
                'files_to_keep': cleanup_plan['files_to_keep'],
                'cleanup_mode': cleanup_mode.value
            }
        )

        # Logging detallado
        from utils.format_utils import format_size
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Live Photos - Archivos para eliminar:")
            for file_info in cleanup_plan['files_to_delete']:
                self.logger.debug(f"  → A eliminar: {file_info['path']} ({file_info['type']}, {format_size(file_info['size'])})")
            
            self.logger.debug("Live Photos: Archivos a conservar:")
            for file_info in cleanup_plan['files_to_keep']:
                self.logger.debug(f"  ✓ A conservar: {file_info['path']} ({file_info['type']}, {format_size(file_info['size'])})")
        
        log_section_footer_discrete(self.logger, f"Análisis completado: {len(cleanup_plan['files_to_delete'])} archivos a eliminar")

        return result

    def execute(
        self,
        analysis_result: LivePhotosAnalysisResult,
        dry_run: bool = False,
        **kwargs
    ) -> LivePhotosExecutionResult:
        """
        Ejecuta la limpieza de Live Photos.
        
        Args:
            analysis_result: Resultado del análisis
            dry_run: Si solo simular
            **kwargs: create_backup, progress_callback
        """
        create_backup = kwargs.get('create_backup', True)
        progress_callback = kwargs.get('progress_callback')
        
        files_to_delete = analysis_result.data.get('files_to_delete', [])

        if not files_to_delete:
            return LivePhotosExecutionResult(
                success=True,
                files_deleted=0,
                space_freed=0,
                dry_run=dry_run,
                message='No hay archivos para eliminar'
            )

        # Extraer rutas para el backup
        files_for_backup = [item['path'] for item in files_to_delete]
        
        return self._execute_operation(
            files=files_for_backup,
            operation_name='livephoto_cleanup',
            execute_fn=lambda dry: self._do_live_photo_cleanup(
                files_to_delete, 
                analysis_result, 
                dry, 
                progress_callback
            ),
            create_backup=create_backup,
            dry_run=dry_run,
            progress_callback=progress_callback
        )
    
    def _do_live_photo_cleanup(
        self,
        files_to_delete: List[dict],
        analysis: LivePhotosAnalysisResult,
        dry_run: bool,
        progress_callback: Optional[Callable[[int, int, str], bool]]
    ) -> LivePhotosExecutionResult:
        """Lógica real de eliminación de Live Photos."""
        mode_label = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(self.logger, "INICIANDO LIMPIEZA DE LIVE PHOTOS", mode=mode_label)
        self.logger.info(f"*** Archivos a procesar: {len(files_to_delete)}")

        results = LivePhotosExecutionResult(success=True, dry_run=dry_run)
        files_deleted_list = []

        try:
            total = len(files_to_delete)
            
            for idx, file_info in enumerate(files_to_delete):
                if not self._report_progress(progress_callback, idx+1, total, f"{'[Simulación] ' if dry_run else ''}Procesando {Path(file_info['path']).name}"):
                    self.logger.info("Limpieza cancelada por el usuario")
                    break

                file_path = file_info['path']
                file_size = file_info['size']

                try:
                    if not file_path.exists():
                        self.logger.warning(f"Archivo no encontrado: {file_path}")
                        continue

                    # Capturar fecha
                    from utils.format_utils import format_size
                    from utils.date_utils import get_date_from_file
                    
                    try:
                         # Uso get_date_from_file por ahora, podría usar cache si tuviera acceso fácil aquí
                        file_date = get_date_from_file(file_path, verbose=False)
                        file_date_str = file_date.strftime('%Y-%m-%d %H:%M:%S') if file_date else 'unknown'
                    except Exception:
                        file_date_str = 'unknown'

                    if dry_run:
                        results.simulated_files_deleted += 1
                        results.simulated_space_freed += file_size
                        files_deleted_list.append(str(file_path))
                        
                        log_msg = f"FILE_DELETED_SIMULATION: {file_path} | Size: {format_size(file_size)} | Type: {file_info['type']} | Date: {file_date_str}"
                        self.logger.info(log_msg)
                        
                        if file_info['type'] == 'video' and file_size > Config.LIVE_PHOTO_MAX_VIDEO_SIZE:
                             self.logger.warning(f"⚠️ SOSPECHA: Video grande eliminado: {file_path} ({format_size(file_size)})")
                    else:
                        file_path.unlink()
                        results.files_deleted += 1
                        results.space_freed += file_size
                        files_deleted_list.append(str(file_path))
                        
                        log_msg = f"FILE_DELETED: {file_path} | Size: {format_size(file_size)} | Type: {file_info['type']} | Date: {file_date_str}"
                        self.logger.info(log_msg)
                        
                        if file_info['type'] == 'video' and file_size > Config.LIVE_PHOTO_MAX_VIDEO_SIZE:
                             self.logger.warning(f"⚠️ SOSPECHA: Video grande eliminado: {file_path} ({format_size(file_size)})")

                except Exception as e:
                    error_msg = f"Error eliminando {file_path.name}: {str(e)}"
                    results.add_error(error_msg)
                    self.logger.error(error_msg)

            results.success = len(results.errors) == 0
            
            # Compatibilidad generic
            if not dry_run:
                 results.files_affected = [Path(f) for f in files_deleted_list]
            else:
                 results.files_affected = []
                 
            results.deleted_files = files_deleted_list

            # Resumen
            from utils.format_utils import format_size
            count = results.simulated_files_deleted if dry_run else results.files_deleted
            space = results.simulated_space_freed if dry_run else results.space_freed
            freed = format_size(space)
            
            summary = self._format_operation_summary("Limpieza Live Photos", count, space, dry_run)
            log_section_footer_relevant(self.logger, summary)
            
            results.message = summary
            if results.backup_path:
                results.message += f"\n\nBackup: {results.backup_path}"
                
            if results.errors:
                 results.message += f"\nAdvertencia: {len(results.errors)} errores"

        except Exception as e:
            error_msg = f"Error durante limpieza: {str(e)}"
            results.add_error(error_msg)
            results.message = error_msg
            self.logger.error(error_msg)

        return results

    def _create_empty_result(self, cleanup_mode: CleanupMode) -> LivePhotosAnalysisResult:
        return LivePhotosAnalysisResult(
            items_count=0, 
            groups=[],
            space_to_free=0, 
            total_space=0, 
            data={
                'files_to_delete': [], 
                'files_to_keep': [],
                'cleanup_mode': cleanup_mode.value
            }
        )

    def _detect_in_directory(
        self, 
        progress_callback: Optional[Callable] = None
    ) -> Optional[List[LivePhotoGroup]]:
        """
        Detecta Live Photos usando FileInfoRepository.
        """
        # Obtener FileInfoRepository
        repo = FileInfoRepository.get_instance()
        
        # Recopilar archivos desde repo
        all_files = repo.get_all_files()
        
        photos = []
        videos = []
        
        processed = 0
        total_in_cache = len(all_files)
        
        photo_exts = self.photo_extensions
        video_exts = self.video_extensions

        self.logger.info(f"Escaneando {total_in_cache} archivos en FileInfoRepository...")
        
        for meta in all_files:
            file_path = meta.path
            
            # Check for cancellation
            if processed % 1000 == 0 and progress_callback:
                if not progress_callback(processed, total_in_cache, "Filtrando archivos"):
                    return None
            
            # Use meta.extension (assuming it is lower case in FileInfoRepository but we have UPPER in sets)
            # Actually FileInfoRepository typically stores lower case extension (e.g. .jpg)
            # self.photo_extensions has UPPER.
            # Convert meta.extension to upper for check.
            ext_upper = meta.extension.upper()
            
            if ext_upper in photo_exts:
                photos.append(file_path)
            elif ext_upper in video_exts:
                videos.append(file_path)
            
            processed += 1
            
        self.logger.info(f"Encontrados: {len(photos)} fotos, {len(videos)} videos")

        if not photos or not videos:
            return []

        # Detectar grupos
        self.logger.info("Iniciando matching de Live Photos...")
        groups = self._detect_live_photos(photos, videos, progress_callback)

        if groups is None:
            return None

        # Eliminar duplicados
        unique_groups = self._remove_duplicate_groups(groups)
        self.logger.info(f"Detectados {len(unique_groups)} grupos de Live Photos")

        return unique_groups

    def _normalize_name(self, name: str) -> str:
        """Normaliza el nombre eliminando sufijos comunes"""
        name = name.lower()
        suffixes = ['_photo', '_video', ' photo', ' video', '-photo', '-video']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name

    def _detect_live_photos(
        self, 
        photos: List[Path], 
        videos: List[Path], 
        progress_callback: Optional[Callable] = None
    ) -> Optional[List[LivePhotoGroup]]:
        """Detecta parejas de fotos/videos."""
        
        # Obtener FileInfoRepository
        repo = FileInfoRepository.get_instance()
        
        groups = []
        total_photos = len(photos)
        
        video_map = defaultdict(list)
        for video in videos:
            normalized_name = self._normalize_name(video.stem)
            video_map[normalized_name].append(video)

        for idx, photo in enumerate(photos, 1):
            if idx % 100 == 0:
                if progress_callback and not progress_callback(idx, total_photos, "Matching Live Photos"):
                    return None
            
            normalized_name = self._normalize_name(photo.stem)
            
            if normalized_name in video_map:
                original_name = photo.stem
                for video in video_map[normalized_name]:
                    if photo.parent == video.parent:
                        try:
                            image_size = None
                            video_size = None
                            
                            meta_img = repo.get_file_metadata(photo)
                            meta_vid = repo.get_file_metadata(video)
                            if meta_img: image_size = meta_img.fs_size
                            if meta_vid: video_size = meta_vid.fs_size
                            
                            if image_size is None: image_size = photo.stat().st_size
                            if video_size is None: video_size = video.stat().st_size
                            
                            group = LivePhotoGroup(
                                image_path=photo,
                                video_path=video,
                                base_name=original_name,
                                directory=photo.parent,
                                image_size=image_size,
                                video_size=video_size,
                                file_info_repo=repo
                            )
                            
                            time_diff = group.time_difference
                            if time_diff <= self.time_tolerance:
                                groups.append(group)
                            
                        except Exception as e:
                            self.logger.debug(f"Error matching {original_name}: {e}")
                            
        return groups

    def _remove_duplicate_groups(self, groups: List[LivePhotoGroup]) -> List[LivePhotoGroup]:
        """Elimina grupos duplicados basados en imagen y video."""
        unique = {}
        for group in groups:
            key = (str(group.image_path), str(group.video_path))
            if key not in unique:
                unique[key] = group
        return list(unique.values())

    def _generate_cleanup_plan(
        self, 
        groups: List[LivePhotoGroup], 
        mode: CleanupMode
    ) -> dict:
        """Genera plan de limpieza."""
        files_to_delete = []
        files_to_keep = []

        for group in groups:
            delete_video = False
            delete_image = False
            
            if mode == CleanupMode.KEEP_IMAGE:
                delete_video = True
            elif mode == CleanupMode.KEEP_VIDEO:
                delete_image = True
            elif mode == CleanupMode.KEEP_LARGER:
                if group.image_size >= group.video_size:
                    delete_video = True
                else:
                    delete_image = True
            elif mode == CleanupMode.KEEP_SMALLER:
                if group.image_size <= group.video_size:
                    delete_video = True
                else:
                    delete_image = True
            
            if delete_image:
                files_to_delete.append({
                    'path': group.image_path,
                    'type': 'image',
                    'size': group.image_size,
                    'paired_file': group.video_path
                })
                files_to_keep.append({
                    'path': group.video_path,
                    'type': 'video',
                    'size': group.video_size
                })
            elif delete_video:
                files_to_delete.append({
                    'path': group.video_path,
                    'type': 'video',
                    'size': group.video_size,
                    'paired_file': group.image_path
                })
                files_to_keep.append({
                    'path': group.image_path,
                    'type': 'image',
                    'size': group.image_size
                })

        return {
            'files_to_delete': files_to_delete,
            'files_to_keep': files_to_keep
        }
