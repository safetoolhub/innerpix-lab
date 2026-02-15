"""
Servicio unificado de Live Photos - Detección y limpieza consolidados

Este servicio detecta Live Photos de iPhone (pares imagen + video MOV) y permite
eliminar los videos asociados para liberar espacio.

Refactorizado para usar FileInfoRepositoryCache y seguir el patrón de HeicService.
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Set

from collections import defaultdict

from config import Config
from utils.date_utils import select_best_date_from_common_date_to_2_files
from services.result_types import (
    LivePhotosAnalysisResult, 
    LivePhotosExecutionResult,
    LivePhotoGroup,
    LivePhotoImageInfo
)
from services.base_service import BaseService, ProgressCallback
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from services.file_metadata import FileMetadata
from utils.logger import (
    log_section_header_discrete, 
    log_section_footer_discrete, 
    log_section_header_relevant, 
    log_section_footer_relevant
)
from utils.format_utils import format_size, format_duration


class LivePhotoService(BaseService):
    """
    Servicio unificado de Live Photos: detección y limpieza.
    
    Detecta Live Photos (imagen + video MOV con el mismo nombre base y fecha similar)
    y permite eliminar los videos para liberar espacio.
    
    Salvaguarda: Solo elimina videos con duración <= LIVE_PHOTO_MAX_VIDEO_DURATION_SECONDS
    (por defecto 3.2s) ya que los Live Photos de iPhone siempre duran ~3 segundos.
    
    Hereda de BaseService para logging estandarizado y gestión de backups.
    """

    def __init__(self):
        super().__init__("LivePhotoService")

        # Extensiones para Live Photos (lowercase para comparación)
        self.photo_extensions = {'.heic', '.jpg', '.jpeg'}
        self.video_extensions = {'.mov'}
        
        self.logger.info(f"Extensiones de foto configuradas: {self.photo_extensions}")
        self.logger.info(f"Extensiones de video configuradas: {self.video_extensions}")
        self.logger.info(
            f"Duración máxima para eliminación: {Config.LIVE_PHOTO_MAX_VIDEO_DURATION_SECONDS}s"
        )

        # Estadísticas
        self.stats = {
            'photos_found': 0,
            'videos_found': 0,
            'groups_found': 0,
            'total_video_size': 0,
            'total_image_size': 0,
            'rejected_by_time_diff': 0,
            'protected_by_duration': 0  # Videos no eliminados por duración > 3.2s
        }

    def analyze(
        self, 
        progress_callback: Optional[ProgressCallback] = None,
        validate_dates: bool = True,
        **kwargs
    ) -> LivePhotosAnalysisResult:
        """
        Analiza Live Photos usando FileInfoRepositoryCache.
        
        Args:
            progress_callback: Callback de progreso (current, total, message) -> bool
            validate_dates: Si validar que las fechas coincidan (recomendado)
            **kwargs: Args adicionales
            
        Returns:
            LivePhotosAnalysisResult con grupos detectados y rechazados
        """
        repo = FileInfoRepositoryCache.get_instance()
        
        log_section_header_discrete(self.logger, "ANÁLISIS DE LIVE PHOTOS")
        self.logger.info(f"Usando FileInfoRepositoryCache con {repo.get_file_count()} archivos")
        self.logger.info(f"Validación de fechas: {'ACTIVADA' if validate_dates else 'DESACTIVADA'}")
        
        if validate_dates:
            self.logger.info(f"Tolerancia máxima: {Config.LIVE_PHOTO_MAX_TIME_DIFFERENCE_SECONDS}s")
        
        self._reset_stats()
        
        # Obtener todos los archivos del repositorio
        all_files = repo.get_all_files()
        total_files = len(all_files)
        
        # Estructura optimizada: dict[directory, dict[base_name_normalizado, list[FileMetadata]]]
        photos_by_dir: Dict[Path, Dict[str, List[FileMetadata]]] = defaultdict(lambda: defaultdict(list))
        videos_by_dir: Dict[Path, Dict[str, FileMetadata]] = defaultdict(dict)
        
        # Clasificar archivos y asegurar que los videos tengan duración calculada
        videos_without_duration = []
        for i, meta in enumerate(all_files):
            if i % 1000 == 0 and not self._report_progress(
                progress_callback, i, total_files, "Clasificando archivos..."
            ):
                return self._create_empty_result()
            
            extension = meta.extension.lower()
            base_name = self._normalize_name(meta.path.stem)
            parent_dir = meta.path.parent
            
            if extension in self.photo_extensions:
                photos_by_dir[parent_dir][base_name].append(meta)
                self.stats['total_image_size'] += meta.fs_size
                self.stats['photos_found'] += 1
            elif extension in self.video_extensions:
                videos_by_dir[parent_dir][base_name] = meta
                self.stats['total_video_size'] += meta.fs_size
                self.stats['videos_found'] += 1
                
                # Verificar si tiene duración calculada
                if meta.exif_VideoDurationSeconds is None:
                    videos_without_duration.append(meta)
        
        self.logger.info(f"Encontrados: {self.stats['photos_found']} fotos, {self.stats['videos_found']} videos MOV")
        
        # Calcular duración de videos que no la tienen (on-demand)
        if videos_without_duration:
            self._ensure_video_durations(videos_without_duration, progress_callback)
        
        # Emparejar archivos
        groups: List[LivePhotoGroup] = []
        rejected_groups: List[LivePhotoGroup] = []
        
        # Calcular total de posibles grupos para el log de progreso (INFO cada 10%)
        total_possible_groups = 0
        for directory, video_dict in videos_by_dir.items():
            if directory in photos_by_dir:
                total_possible_groups += len(
                    set(video_dict.keys()) & set(photos_by_dir[directory].keys())
                )
        
        processed_groups = 0
        progress_checkpoint = max(1, total_possible_groups // 10)
        
        processed_dirs = 0
        total_dirs = len(videos_by_dir)
        
        for directory, video_dict in videos_by_dir.items():
            processed_dirs += 1
            if processed_dirs % 10 == 0:
                self._report_progress(
                    progress_callback, processed_dirs, total_dirs, "Emparejando Live Photos..."
                )
            
            if directory not in photos_by_dir:
                continue
            
            photo_dict = photos_by_dir[directory]
            
            # Nombres base comunes
            common_bases = sorted(list(set(video_dict.keys()) & set(photo_dict.keys())))
            
            for base_name in common_bases:
                processed_groups += 1
                video_meta = video_dict[base_name]
                photo_metas = photo_dict[base_name]
                
                self.logger.debug(f"Analizando grupo: {base_name} en {directory} ({len(photo_metas)} imágenes)")
                
                try:
                    # Crear grupo con todas las imágenes que coinciden
                    group = self._create_live_photo_group(
                        video_meta=video_meta,
                        photo_metas=photo_metas,
                        base_name=base_name,
                        directory=directory,
                        validate_dates=validate_dates
                    )
                    
                    if group is not None:
                        # El filtrado individual ya se hizo en _create_live_photo_group
                        # Si el grupo no tiene imágenes válidas, va a rejected_groups
                        if group.image_count == 0:
                            # El log detallado ya se hizo en _create_live_photo_group
                            self.stats['rejected_by_time_diff'] += 1
                            rejected_groups.append(group)
                        else:
                            # Grupo válido con al menos una imagen
                            diff_str = f"{group.date_difference:.2f}s" if group.date_difference is not None else "N/A"
                            self.logger.debug(
                                f"Grupo admitido {base_name}: "
                                f"source={group.date_source}, diff={diff_str}, "
                                f"imágenes={group.image_count}"
                            )
                            groups.append(group)
                            
                except Exception as e:
                    self.logger.warning(f"Error procesando grupo {base_name}: {e}")
                    import traceback
                    self.logger.debug(traceback.format_exc())
                
                # Log INFO cada 10% de los grupos totales
                if total_possible_groups > 0 and processed_groups % progress_checkpoint == 0:
                    percent = (processed_groups / total_possible_groups) * 100
                    self.logger.info(
                        f"** Progreso análisis Live Photos: {percent:.0f}% "
                        f"({processed_groups}/{total_possible_groups} grupos)"
                    )
        
        self.stats['groups_found'] = len(groups)
        
        # Calcular estadísticas
        total_space = sum(g.total_size for g in groups)
        
        log_section_footer_discrete(
            self.logger, 
            f"Análisis completado: {len(groups)} grupos aceptados, {len(rejected_groups)} rechazados"
        )
        
        return LivePhotosAnalysisResult(
            groups=groups,
            rejected_groups=rejected_groups,
            items_count=len(groups),
            bytes_total=total_space,
            total_space=total_space
        )

    def execute(
        self,
        analysis_result: LivePhotosAnalysisResult,
        dry_run: bool = False,
        create_backup: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> LivePhotosExecutionResult:
        """
        Ejecuta la limpieza de Live Photos (elimina videos).
        
        Args:
            analysis_result: Resultado del análisis
            dry_run: Si solo simular
            create_backup: Si crear backup antes de eliminar
            progress_callback: Callback de progreso
            **kwargs: Args adicionales
            
        Returns:
            LivePhotosExecutionResult con resultados de la ejecución
        """
        groups = analysis_result.groups
        
        if not groups:
            return LivePhotosExecutionResult(
                success=True,
                items_processed=0,
                bytes_processed=0,
                message='No hay Live Photos para limpiar',
                dry_run=dry_run,
                videos_deleted=0
            )
        
        # Extraer videos a eliminar (únicos, ya que múltiples imágenes pueden compartir un video)
        videos_to_delete: Dict[Path, int] = {}
        for group in groups:
            if group.video_path not in videos_to_delete:
                videos_to_delete[group.video_path] = group.video_size
        
        files_to_delete = list(videos_to_delete.keys())
        
        return self._execute_operation(
            files=files_to_delete,
            operation_name='livephoto_cleanup',
            execute_fn=lambda dry: self._do_live_photo_cleanup(
                videos_to_delete,
                dry,
                progress_callback
            ),
            create_backup=create_backup,
            dry_run=dry_run,
            progress_callback=progress_callback
        )

    def _create_live_photo_group(
        self,
        video_meta: FileMetadata,
        photo_metas: List[FileMetadata],
        base_name: str,
        directory: Path,
        validate_dates: bool
    ) -> Optional[LivePhotoGroup]:
        """
        Crea un LivePhotoGroup a partir de un video y sus imágenes asociadas.
        
        Args:
            video_meta: Metadatos del video
            photo_metas: Lista de metadatos de las imágenes candidatas
            base_name: Nombre base normalizado
            directory: Directorio común
            validate_dates: Si validar fechas
            
        Returns:
            LivePhotoGroup o None si no se puede crear
        """
        images: List[LivePhotoImageInfo] = []
        rejected_images: Dict[str, str] = {}  # {nombre: motivo}
        max_time_diff: float = 0.0
        date_source: Optional[str] = None
        video_date: Optional[datetime] = None
        
        for photo_meta in photo_metas:
            if validate_dates:
                # Usar select_best_date_from_common_date_to_2_files para comparar fechas
                best_date_result = select_best_date_from_common_date_to_2_files(video_meta, photo_meta, verbose=True)
                
                if not best_date_result:
                    # No hay fecha común válida - rechazar esta imagen
                    reason = "sin fecha común"
                    self.logger.debug(
                        f"Imagen rechazada ({reason}) para {base_name}: {photo_meta.path.name}"
                    )
                    rejected_images[photo_meta.path.name] = reason
                    continue
                
                vid_date, img_date, source = best_date_result
                time_diff = abs((vid_date - img_date).total_seconds())
                
                # FILTRAR: Si esta imagen específica excede el threshold, descartarla
                if time_diff > Config.LIVE_PHOTO_MAX_TIME_DIFFERENCE_SECONDS:
                    reason = f"diff={format_duration(time_diff)} > {format_duration(Config.LIVE_PHOTO_MAX_TIME_DIFFERENCE_SECONDS)}"
                    self.logger.debug(
                        f"Imagen rechazada ({reason}) "
                        f"para {base_name}: {photo_meta.path.name}"
                    )
                    rejected_images[photo_meta.path.name] = reason
                    continue
                
                # Actualizar video_date y source si es la primera vez
                if video_date is None:
                    video_date = vid_date
                    date_source = source
                
                # Actualizar max time diff (solo con imágenes aceptadas)
                if time_diff > max_time_diff:
                    max_time_diff = time_diff
                
                img_info = LivePhotoImageInfo(
                    path=photo_meta.path,
                    size=photo_meta.fs_size,
                    date=img_date,
                    date_source=source
                )
            else:
                # Sin validación de fechas, crear imagen sin datos de fecha
                img_info = LivePhotoImageInfo(
                    path=photo_meta.path,
                    size=photo_meta.fs_size,
                    date=None,
                    date_source=None
                )
                max_time_diff = 0.0
            
            images.append(img_info)
        
        # Log de imágenes rechazadas si hubo
        if rejected_images:
            accepted_names = [img.path.name for img in images]
            rejected_with_reasons = [f"{name} ({reason})" for name, reason in rejected_images.items()]
            self.logger.info(
                f"Grupo '{base_name}' en {directory}: "
                f"{len(images)} aceptadas [{', '.join(accepted_names)}], "
                f"{len(rejected_images)} rechazadas [{', '.join(rejected_with_reasons)}]"
            )
        
        # Si no hay imágenes válidas, crear un grupo vacío para rejected_groups
        # Usamos la primera imagen rechazada para calcular date_difference
        if not images and validate_dates and rejected_images:
            # Intentar obtener la máxima diferencia de tiempo de las rechazadas
            # para reportar en rejected_groups
            for photo_meta in photo_metas:
                best_date_result = select_best_date_from_common_date_to_2_files(video_meta, photo_meta, verbose=False)
                if best_date_result:
                    vid_date, img_date, source = best_date_result
                    time_diff = abs((vid_date - img_date).total_seconds())
                    if time_diff > max_time_diff:
                        max_time_diff = time_diff
                        video_date = vid_date
                        date_source = source
        
        if not images:
            # Retornar None solo si no hay imágenes Y no estamos validando fechas
            # (caso de error genuino)
            if not validate_dates:
                return None
            # Si estamos validando y todas fueron rechazadas, crear grupo vacío
            # para rejected_groups
        
        # Crear el grupo (puede tener 0 imágenes si todas fueron rechazadas)
        return LivePhotoGroup(
            video_path=video_meta.path,
            video_size=video_meta.fs_size,
            images=images,
            base_name=base_name,
            directory=directory,
            video_date=video_date,
            video_date_source=date_source,
            date_source=date_source,
            date_difference=max_time_diff
        )

    def _do_live_photo_cleanup(
        self,
        videos_to_delete: Dict[Path, int],
        dry_run: bool,
        progress_callback: Optional[ProgressCallback]
    ) -> LivePhotosExecutionResult:
        """
        Lógica real de eliminación de videos de Live Photos.
        
        Salvaguarda: Videos con duración > LIVE_PHOTO_MAX_VIDEO_DURATION_SECONDS
        no se eliminan (los Live Photos reales duran ~3 segundos).
        """
        mode_label = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(self.logger, "LIMPIEZA DE LIVE PHOTOS", mode=mode_label)
        self.logger.info(f"Videos a evaluar: {len(videos_to_delete)}")
        self.logger.info(
            f"Salvaguarda de duración activa: máximo {Config.LIVE_PHOTO_MAX_VIDEO_DURATION_SECONDS}s"
        )

        result = LivePhotosExecutionResult(success=True, dry_run=dry_run)
        files_affected = []
        items_processed = 0
        bytes_processed = 0
        videos_deleted = 0
        videos_protected = 0
        remaining_short_videos: List[Path] = []  # Videos cortos que quedan sin eliminar

        repo = FileInfoRepositoryCache.get_instance()
        max_duration = Config.LIVE_PHOTO_MAX_VIDEO_DURATION_SECONDS

        try:
            total = len(videos_to_delete)
            
            for idx, (video_path, video_size) in enumerate(videos_to_delete.items()):
                if not self._report_progress(
                    progress_callback, 
                    idx + 1, 
                    total, 
                    f"{'[Simulación] ' if dry_run else ''}Evaluando {video_path.name}"
                ):
                    self.logger.info("Limpieza cancelada por el usuario")
                    break

                try:
                    if not video_path.exists():
                        self.logger.warning(f"Video no encontrado: {video_path}")
                        continue

                    # Obtener duración del video desde el repositorio
                    video_meta = repo.get_file_metadata(video_path)
                    video_duration = None
                    
                    if video_meta:
                        duration_value = video_meta.exif_VideoDurationSeconds
                        # Verificar que sea un número real (no None, no Mock)
                        if isinstance(duration_value, (int, float)):
                            video_duration = float(duration_value)
                    
                    if video_duration is None:
                        # Si no está en caché, extraer duración directamente
                        try:
                            from utils.file_utils import get_exif_from_video
                            video_exif = get_exif_from_video(video_path)
                            if video_exif and 'duration_seconds' in video_exif:
                                video_duration = video_exif['duration_seconds']
                        except Exception as e:
                            self.logger.debug(f"No se pudo obtener duración de {video_path.name}: {e}")

                    # SALVAGUARDA DE DURACIÓN: No eliminar videos > 3.2s
                    if video_duration is not None and video_duration > max_duration:
                        videos_protected += 1
                        self.logger.warning(
                            f"⛔ VIDEO PROTEGIDO: {video_path} no se eliminará "
                            f"(duración: {video_duration:.2f}s > {max_duration}s). "
                            f"Probablemente NO es un Live Photo real."
                        )
                        continue

                    # Usar método centralizado de BaseService
                    if self._delete_file_with_logging(video_path, video_size, 'MOV', dry_run):
                        items_processed += 1
                        bytes_processed += video_size
                        videos_deleted += 1
                        files_affected.append(video_path)
                        
                        # Warning si el video es grande (aunque se elimine)
                        if video_size > Config.LIVE_PHOTO_MAX_VIDEO_SIZE:
                            self.logger.warning(
                                f"⚠️ SOSPECHA: Video grande {'en' if dry_run else 'eliminado en'} "
                                f"Live Photo: {video_path} ({format_size(video_size)})"
                            )

                except Exception as e:
                    error_msg = f"Error procesando {video_path.name}: {str(e)}"
                    result.add_error(error_msg)
                    self.logger.error(error_msg)

            # Actualizar estadísticas
            self.stats['protected_by_duration'] = videos_protected

            result.success = len(result.errors) == 0
            
            # Poblar estadísticas en el objeto de resultado
            result.items_processed = items_processed
            result.bytes_processed = bytes_processed
            result.files_affected = files_affected
            result.videos_deleted = videos_deleted

            # LOG FINAL: Listar videos cortos restantes en el directorio
            self._log_remaining_short_videos(repo, max_duration)

            # Resumen
            summary = self._format_operation_summary(
                "Limpieza Live Photos", 
                items_processed, 
                bytes_processed, 
                dry_run
            )
            
            if videos_protected > 0:
                summary += f" | {videos_protected} videos protegidos por duración"
            
            log_section_footer_relevant(self.logger, summary)
            
            # Mostramos estadísticas de la caché al final
            repo.log_cache_statistics(level=logging.INFO)

            result.message = summary
            if result.backup_path:
                result.message += f"\n\nBackup: {result.backup_path}"
                
            if result.errors:
                result.message += f"\nAdvertencia: {len(result.errors)} errores"
            
            if videos_protected > 0:
                result.message += f"\n⛔ {videos_protected} videos protegidos (duración > {max_duration}s)"

        except Exception as e:
            error_msg = f"Error durante limpieza: {str(e)}"
            result.add_error(error_msg)
            result.message = error_msg
            self.logger.error(error_msg)

        return result

    def _log_remaining_short_videos(self, repo: FileInfoRepositoryCache, max_duration: float) -> None:
        """
        Registra en log INFO todos los videos MOV cortos que permanecen en el dataset.
        
        Esto permite analizar si hay Live Photos no detectados que deberían haberse procesado.
        
        Args:
            repo: Repositorio de metadatos
            max_duration: Duración máxima en segundos para considerar un video "corto"
        """
        all_files = repo.get_all_files()
        short_videos: List[tuple] = []  # (path, duration)
        
        for meta in all_files:
            ext = meta.extension
            # Verificar que extension sea un string real (no Mock)
            if not isinstance(ext, str):
                continue
                
            if ext.lower() in self.video_extensions:
                duration = meta.exif_VideoDurationSeconds
                # Verificar que sea un número real
                if isinstance(duration, (int, float)) and duration <= max_duration:
                    short_videos.append((meta.path, float(duration)))
        
        if short_videos:
            self.logger.info(
                f"📋 ANÁLISIS FINAL: {len(short_videos)} videos MOV cortos "
                f"(≤{max_duration}s) permanecen en el dataset:"
            )
            for path, duration in sorted(short_videos, key=lambda x: x[0]):
                self.logger.info(f"   - {path} ({duration:.2f}s)")
            self.logger.info(
                "   ℹ️ Revisa estos videos: podrían ser Live Photos no detectados "
                "(nombre base no coincide con imagen o fechas muy diferentes)"
            )
        else:
            self.logger.info(
                f"✅ No quedan videos MOV cortos (≤{max_duration}s) en el dataset"
            )

    def _ensure_video_durations(
        self, 
        videos: List[FileMetadata], 
        progress_callback: Optional[ProgressCallback]
    ) -> None:
        """
        Asegura que todos los videos tengan duración calculada.
        
        Si un video no tiene exif_VideoDurationSeconds en caché, intenta extraerlo
        con get_exif_from_video() y actualiza el FileMetadata correspondiente.
        
        Args:
            videos: Lista de FileMetadata de videos sin duración
            progress_callback: Callback de progreso
        """
        if not videos:
            return
        
        self.logger.info(
            f"📹 Calculando duración de {len(videos)} videos sin metadatos..."
        )
        
        # Verificar si hay herramientas disponibles
        import shutil
        has_ffprobe = shutil.which('ffprobe') is not None
        has_exiftool = shutil.which('exiftool') is not None
        
        if not has_ffprobe and not has_exiftool:
            self.logger.warning(
                "⚠️ No se encontró ffprobe ni exiftool. "
                "No se puede calcular la duración de los videos. "
                "Instale ffmpeg o exiftool para habilitar esta funcionalidad."
            )
            return
        
        try:
            from utils.file_utils import get_exif_from_video
        except ImportError:
            self.logger.error("No se pudo importar get_exif_from_video")
            return
        
        calculated = 0
        failed = 0
        
        for i, meta in enumerate(videos):
            if i % 10 == 0:
                self._report_progress(
                    progress_callback, 
                    i, 
                    len(videos), 
                    f"Extrayendo duración de videos ({i}/{len(videos)})..."
                )
            
            try:
                video_exif = get_exif_from_video(meta.path)
                
                if video_exif and 'duration_seconds' in video_exif:
                    # Actualizar el FileMetadata directamente
                    meta.exif_VideoDurationSeconds = video_exif['duration_seconds']
                    calculated += 1
                    self.logger.debug(
                        f"Duración calculada para {meta.path.name}: "
                        f"{meta.exif_VideoDurationSeconds:.2f}s"
                    )
                else:
                    failed += 1
                    self.logger.debug(
                        f"No se pudo obtener duración de {meta.path.name}"
                    )
                    
            except Exception as e:
                failed += 1
                self.logger.debug(
                    f"Error calculando duración de {meta.path.name}: {e}"
                )
        
        if calculated > 0:
            self.logger.info(
                f"✅ Duración calculada para {calculated} videos"
            )
        if failed > 0:
            self.logger.warning(
                f"⚠️ No se pudo obtener duración de {failed} videos "
                f"(pueden no ser videos válidos o estar corruptos)"
            )

    def _normalize_name(self, name: str) -> str:
        """
        Normaliza el nombre eliminando sufijos comunes añadidos por renombrados.
        
        Args:
            name: Nombre del archivo sin extensión
            
        Returns:
            Nombre normalizado en minúsculas
        """
        name = name.lower()
        suffixes = ['_photo', '_video', ' photo', ' video', '-photo', '-video']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name

    def _log_group_metadata(
        self, 
        video_meta: FileMetadata, 
        photo_metas: List[FileMetadata]
    ) -> None:
        """Log de metadatos para diagnóstico de grupos rechazados."""
        self.logger.info(f"  Video: {video_meta.get_summary(verbose=True)}")
        for i, photo_meta in enumerate(photo_metas):
            self.logger.info(f"  Imagen {i+1}: {photo_meta.get_summary(verbose=True)}")

    def _create_empty_result(self) -> LivePhotosAnalysisResult:
        """Crea un resultado vacío para casos de cancelación o sin datos."""
        return LivePhotosAnalysisResult(
            groups=[],
            rejected_groups=[],
            items_count=0,
            bytes_total=0,
            total_space=0
        )

    def _reset_stats(self) -> None:
        """Reinicia las estadísticas del servicio."""
        for key in self.stats:
            self.stats[key] = 0

    def get_stats(self) -> Dict:
        """Obtiene una copia de las estadísticas actuales."""
        return self.stats.copy()
