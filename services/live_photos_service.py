"""
Servicio unificado de Live Photos - Detección y limpieza consolidados

Este servicio fusiona LivePhotoDetector y LivePhotoCleaner en una sola clase
para simplificar la API y eliminar duplicación de código.
"""
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from config import Config
from utils.date_utils import get_date_from_file
from services.result_types import LivePhotoCleanupAnalysisResult, LivePhotoCleanupResult
from services.base_service import BaseService, BackupCreationError
from services.metadata_cache import FileMetadataCache
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
    metadata_cache: Optional[FileMetadataCache] = None

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
        # para evitar bloquear el procesamiento durante la creación de grupos

    def _ensure_dates_loaded(self) -> bool:
        """
        Intenta cargar fechas desde caché o calcularlas si es necesario.
        
        Prioriza usar caché para evitar cálculos costosos durante análisis masivo.
        Si hay metadata_cache pero las fechas no están, usa fallback rápido (skip_expensive_ops).
        Si NO hay metadata_cache, calcula síncronamente (para tests).
        
        Returns:
            True si ambas fechas están disponibles, False si alguna falta
        """
        if not self.image_date:
            # Primero intentar desde caché
            if self.metadata_cache:
                cached_date, source = self.metadata_cache.get_selected_date(self.image_path)
                if cached_date:
                    self.image_date = cached_date
                    self.image_date_source = source
            
            # Si no hay caché o no estaba cacheado, calcular
            if not self.image_date:
                if self.metadata_cache:
                    # Con cache disponible: usar fallback rápido (evita ffprobe/EXIF costosos)
                    self.image_date = get_date_from_file(self.image_path, metadata_cache=self.metadata_cache, skip_expensive_ops=True)
                    self.image_date_source = "mtime_fallback"
                else:
                    # Sin cache (tests): calcular completo
                    self.image_date = get_date_from_file(self.image_path)
                    self.image_date_source = "test_calculation"
                    if not self.image_date:
                        self.image_date = datetime.fromtimestamp(self.image_path.stat().st_mtime)
                        self.image_date_source = "mtime"
        
        if not self.video_date:
            # Primero intentar desde caché
            if self.metadata_cache:
                cached_date, source = self.metadata_cache.get_selected_date(self.video_path)
                if cached_date:
                    self.video_date = cached_date
                    self.video_date_source = source
            
            # Si no hay caché o no estaba cacheado, calcular
            if not self.video_date:
                if self.metadata_cache:
                    # Con cache disponible: usar fallback rápido (evita ffprobe costoso)
                    self.video_date = get_date_from_file(self.video_path, metadata_cache=self.metadata_cache, skip_expensive_ops=True)
                    self.video_date_source = "mtime_fallback"
                else:
                    # Sin cache (tests): calcular completo
                    self.video_date = get_date_from_file(self.video_path)
                    self.video_date_source = "test_calculation"
                    if not self.video_date:
                        self.video_date = datetime.fromtimestamp(self.video_path.stat().st_mtime)
                        self.video_date_source = "mtime"
        
        # Retornar True solo si AMBAS fechas están disponibles
        return self.image_date is not None and self.video_date is not None
    
    @property
    def total_size(self) -> int:
        """Tamaño total del grupo"""
        return self.image_size + self.video_size

    def _is_filesystem_source(self, source: str) -> bool:
        """Verifica si la fuente de fecha es del sistema de archivos"""
        if not source: return False
        s = source.lower()
        return 'mtime' in s or 'ctime' in s or 'filesystem' in s or 'fallback' in s

    def _is_exif_source(self, source: str) -> bool:
        """Verifica si la fuente de fecha es EXIF"""
        if not source: return False
        s = source.lower()
        return 'exif' in s

    def get_comparison_dates(self) -> tuple[datetime, datetime, str, str]:
        """
        Obtiene las fechas ajustadas para comparación justa.
        
        LÓGICA CRÍTICA DE AJUSTE:
        Si el video usa fecha de sistema (mtime/ctime/filesystem), SIEMPRE
        ajustamos la imagen también a mtime, incluso si tiene EXIF.
        
        Razón: Los Live Photos deben sincronizarse en el momento de captura,
        pero cuando los archivos se mueven/sincronizan, sus mtimes pueden 
        desincronizarse. Si comparamos EXIF (creación real) vs mtime (última
        modificación), casi siempre diferirán y rechazaremos Live Photos válidos.
        
        Priorizamos DETECTAR Live Photos (menos falsos negativos) sobre 
        PRECISIÓN temporal (algunos falsos positivos aceptables).
        
        Returns:
            Tupla (img_date, vid_date, img_source, vid_source) ajustadas
        """
        if not self._ensure_dates_loaded():
            return None, None, "unavailable", "unavailable"
        
        img_date = self.image_date
        img_source = self.image_date_source
        vid_date = self.video_date
        vid_source = self.video_date_source
        
        # REGLA CRÍTICA: Si el video usa mtime, forzar mtime también en imagen
        # Esto asegura comparación "mtime vs mtime" en lugar de "EXIF vs mtime"
        if self._is_filesystem_source(vid_source) and self._is_exif_source(img_source):
            try:
                # Obtener mtime de imagen para comparación
                mtime_date = None
                if self.metadata_cache:
                    # El método correcto en cache es get_file_stats que incluye mtime
                    stats = self.metadata_cache.get_file_stats(self.image_path)
                    if stats and 'mtime' in stats:
                        mtime_date = stats['mtime']
                
                if not mtime_date:
                    mtime_date = datetime.fromtimestamp(self.image_path.stat().st_mtime)
                
                if mtime_date:
                    # SIEMPRE usar mtime para comparación cuando video usa mtime
                    img_date = mtime_date
                    img_source = f"{img_source}→mtime_adjusted"
                    # No podemos loggear aquí porque es un dataclass sin logger
            except Exception:
                # Silenciar error, no es crítico
                pass
        
        return img_date, vid_date, img_source, vid_source

    @property
    def time_difference(self) -> float:
        """
        Diferencia en segundos entre imagen y video.
        
        Calcula fechas si es necesario (lazy loading optimizado con caché).
        Si el video usa fecha de sistema (mtime) y la imagen usa EXIF,
        se fuerza el uso de mtime para la imagen para una comparación justa.
        
        Returns:
            Diferencia en segundos, o 0.0 si no se pueden obtener fechas
        """
        img_date, vid_date, _, _ = self.get_comparison_dates()
        if img_date and vid_date:
            return abs((img_date - vid_date).total_seconds())
        return 0.0  # Fallback si no se pudieron cargar fechas


class CleanupMode(Enum):
    """Modos de limpieza de Live Photos"""
    KEEP_IMAGE = "keep_image"          # Mantener imagen, eliminar video
    KEEP_VIDEO = "keep_video"          # Mantener video, eliminar imagen
    KEEP_LARGER = "keep_larger"        # Mantener el archivo más grande
    KEEP_SMALLER = "keep_smaller"      # Mantener el archivo más pequeño
    CUSTOM = "custom"                  # Selección manual por archivo


class LivePhotoService(BaseService):
    """
    Servicio unificado de Live Photos: detección y limpieza.
    
    Combina la funcionalidad de LivePhotoDetector y LivePhotoCleaner
    en una sola clase con API consistente (analyze + execute).
    
    Hereda de BaseService para logging estandarizado y gestión de backup.
    """

    def __init__(self):
        super().__init__("LivePhotoService")

        # Extensiones para Live Photos - Convertir todas a mayúsculas para comparación
        self.photo_extensions = {ext.upper() for ext in {'.heic', '.jpg', '.jpeg'}}
        self.video_extensions = {'.MOV'}  # Live Photos usan específicamente .MOV
        
        self.logger.info(f"Extensiones de foto configuradas: {self.photo_extensions}")
        self.logger.info(f"Extensiones de video configuradas: {self.video_extensions}")

        # Tolerancia de tiempo para matching (5 segundos máximo)
        self.time_tolerance = 5.0

    def analyze(
        self, 
        directory: Path,
        cleanup_mode: CleanupMode = CleanupMode.KEEP_IMAGE,
        recursive: bool = True,
        progress_callback: Optional[Callable[[int, int, str], bool]] = None,
        metadata_cache: Optional[FileMetadataCache] = None
    ) -> LivePhotoCleanupAnalysisResult:
        """
        Analiza Live Photos y genera plan de limpieza.
        
        Combina detección + análisis de limpieza en una sola operación.
        
        Args:
            directory: Directorio a analizar
            cleanup_mode: Modo de limpieza a aplicar
            recursive: Si buscar recursivamente en subdirectorios
            progress_callback: Función opcional (current, total, message) -> bool
                              Retorna False para cancelar la operación
            metadata_cache: Caché opcional de metadatos para reutilizar datos del scan
            
        Returns:
            LivePhotoCleanupAnalysisResult con plan de limpieza detallado
        
        Raises:
            ValueError: Si directory no existe
        """
        log_section_header_discrete(self.logger, "ANÁLISIS DE LIVE PHOTOS")
        self.logger.info(f"Analizando en: {directory}")
        self.logger.info(f"Modo de limpieza: {cleanup_mode.value}")
        if metadata_cache:
            self.logger.info("✓ Usando caché de metadatos (optimizado)")

        if not directory.exists():
            raise ValueError(f"Directorio no existe: {directory}")

        # Paso 1: Detectar Live Photos
        live_photos = self._detect_in_directory(directory, recursive, progress_callback, metadata_cache)
        
        # Si se canceló la detección, retornar resultado vacío
        if live_photos is None:
            return LivePhotoCleanupAnalysisResult(
                total_files=0,
                live_photos_found=0,
                files_to_delete=[],
                files_to_keep=[],
                space_to_free=0,
                total_space=0,
                cleanup_mode=cleanup_mode.value,
                groups=[]
            )

        if not live_photos:
            self.logger.info("No se encontraron Live Photos")
            return LivePhotoCleanupAnalysisResult(
                total_files=0,
                live_photos_found=0,
                files_to_delete=[],
                files_to_keep=[],
                space_to_free=0,
                total_space=0,
                cleanup_mode=cleanup_mode.value,
                groups=[]
            )

        # Paso 2: Generar plan de limpieza según el modo
        cleanup_plan = self._generate_cleanup_plan(live_photos, cleanup_mode)

        # Paso 3: Calcular estadísticas
        total_space = sum(lp.total_size for lp in live_photos)
        space_to_free = sum(item['size'] for item in cleanup_plan['files_to_delete'])

        result = LivePhotoCleanupAnalysisResult(
            total_files=len(live_photos) * 2,
            live_photos_found=len(live_photos),
            files_to_delete=cleanup_plan['files_to_delete'],
            files_to_keep=cleanup_plan['files_to_keep'],
            space_to_free=space_to_free,
            total_space=total_space,
            cleanup_mode=cleanup_mode.value,
            groups=live_photos  # Incluir los grupos para compatibilidad con UI
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
        analysis: LivePhotoCleanupAnalysisResult,
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], bool]] = None
    ) -> LivePhotoCleanupResult:
        """
        Ejecuta la limpieza de Live Photos según análisis previo.
        
        Args:
            analysis: Resultado del análisis previo (de analyze())
            create_backup: Si crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar archivos reales
            progress_callback: Función opcional para reportar progreso
            
        Returns:
            LivePhotoCleanupResult con resultados de la operación
        """
        files_to_delete = analysis.files_to_delete

        if not files_to_delete:
            return LivePhotoCleanupResult(
                success=True,
                files_deleted=0,
                space_freed=0,
                dry_run=dry_run,
                message='No hay archivos para eliminar'
            )

        mode_label = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(
            self.logger,
            "INICIANDO LIMPIEZA DE LIVE PHOTOS",
            mode=mode_label
        )
        self.logger.info(f"*** Archivos a procesar: {len(files_to_delete)}")

        results = LivePhotoCleanupResult(success=True, dry_run=dry_run)

        try:
            # Crear backup usando método centralizado (solo si no es simulación)
            if create_backup and not dry_run:
                try:
                    # Extraer rutas de archivos del análisis
                    files_for_backup = [item['path'] for item in files_to_delete]
                    
                    backup_path = self._create_backup_for_operation(
                        files_for_backup,
                        'livephoto_cleanup',
                        progress_callback
                    )
                    if backup_path:
                        results.backup_path = str(backup_path)
                        self.logger.info(f"Backup creado exitosamente: {backup_path}")
                    else:
                        # Si no se pudo crear backup, no continuar con la operación
                        error_msg = "No se pudo crear el backup. Operación cancelada por seguridad."
                        self.logger.error(error_msg)
                        results.success = False
                        results.add_error(error_msg)
                        results.message = error_msg
                        return results
                except BackupCreationError as e:
                    error_msg = f"Error creando backup: {e}"
                    self.logger.error(error_msg)
                    results.success = False
                    results.add_error(error_msg)
                    results.message = error_msg
                    return results

            # Ejecutar eliminaciones
            total = len(files_to_delete)
            
            for idx, file_info in enumerate(files_to_delete):
                # Reportar progreso al callback (UI) con formato de dos líneas
                if progress_callback and (idx + 1) % Config.UI_UPDATE_INTERVAL == 0:
                    action = "[Simulación] Eliminaría" if dry_run else "Eliminando"
                    file_name = Path(file_info['path']).name
                    progress_msg = f"{action}\n{file_name}"
                    if not progress_callback(idx + 1, total, progress_msg):
                        self.logger.info("Limpieza cancelada por el usuario")
                        break
                
                    # Log de progreso: según intervalo configurado en INFO, más detallado en DEBUG
                if (idx + 1) % Config.LOG_PROGRESS_INTERVAL == 0:
                    self.logger.info(f"Procesados {idx + 1}/{total} archivos en limpieza de Live Photos")
                elif (idx + 1) % Config.UI_UPDATE_INTERVAL == 0:
                    self.logger.debug(f"Procesados {idx + 1}/{total} archivos en limpieza de Live Photos")

                file_path = file_info['path']
                file_size = file_info['size']

                try:
                    # Verificar que el archivo existe
                    if not file_path.exists():
                        # Archivo desapareció entre análisis y ejecución
                        # Loguear como warning pero NO contar como error bloqueante
                        # NO incrementar estadísticas (files_deleted/space_freed) de algo no borrado
                        msg = f"Archivo no encontrado durante eliminación: {file_path}"
                        if dry_run:
                            self.logger.warning(f"[SIMULACIÓN] {msg}")
                        else:
                            self.logger.warning(msg)
                        # Simplemente continuamos al siguiente archivo sin hacer nada más
                        continue

                    # IMPORTANTE: Capturar fecha ANTES de eliminar el archivo
                    from utils.format_utils import format_size
                    from utils.date_utils import get_date_from_file
                    
                    try:
                        file_date = get_date_from_file(file_path, verbose=False)
                        file_date_str = file_date.strftime('%Y-%m-%d %H:%M:%S') if file_date else 'unknown'
                    except Exception:
                        file_date_str = 'unknown'

                    if dry_run:
                        # Solo simular: no modificar counters reales, usar campos simulados
                        results.simulated_files_deleted += 1
                        results.simulated_space_freed += file_size
                        results.deleted_files.append(str(file_path))
                        
                        # Construir log detallado con archivo complementario
                        log_msg = (
                            f"FILE_DELETED_SIMULATION: {file_path} | Size: {format_size(file_size)} | "
                            f"Type: {file_info['type']} | Date: {file_date_str}"
                        )
                        
                        # Añadir información del archivo emparejado si existe
                        if 'paired_file' in file_info:
                            paired_file = file_info['paired_file']
                            try:
                                paired_size = paired_file.stat().st_size
                                # Determinar el tipo del archivo emparejado
                                paired_ext = paired_file.suffix.upper()
                                paired_type = 'image' if paired_ext in self.photo_extensions else 'video'
                                log_msg += (
                                    f" | Kept: {paired_file} | "
                                    f"Kept_Size: {format_size(paired_size)} | "
                                    f"Kept_Type: {paired_type} | "
                                    f"Mode: {analysis.cleanup_mode}"
                                )
                            except Exception as e:
                                self.logger.debug(f"No se pudo obtener info del archivo emparejado: {e}")
                                log_msg += f" | Kept: {paired_file} | Mode: {analysis.cleanup_mode}"
                        
                        self.logger.info(log_msg)
                        
                        # WARNING si el archivo eliminado es un video que supera el tamaño esperado
                        if file_info['type'] == 'video' and file_size > Config.LIVE_PHOTO_MAX_VIDEO_SIZE:
                            self.logger.warning(
                                f"⚠️  SOSPECHA: Video eliminado supera tamaño típico de Live Photo | "
                                f"Archivo: {file_path} | "
                                f"Tamaño: {format_size(file_size)} | "
                                f"Límite: {format_size(Config.LIVE_PHOTO_MAX_VIDEO_SIZE)} | "
                                f"Puede no ser realmente un video de Live Photo"
                            )
                    else:
                        # Eliminar realmente
                        file_path.unlink()

                        # Registrar éxito
                        results.files_deleted += 1
                        results.space_freed += file_size
                        results.deleted_files.append(str(file_path))
                        
                        # Construir log detallado con archivo complementario
                        log_msg = (
                            f"FILE_DELETED: {file_path} | Size: {format_size(file_size)} | "
                            f"Type: {file_info['type']} | Date: {file_date_str}"
                        )
                        
                        # Añadir información del archivo emparejado si existe
                        if 'paired_file' in file_info:
                            paired_file = file_info['paired_file']
                            try:
                                paired_size = paired_file.stat().st_size
                                # Determinar el tipo del archivo emparejado
                                paired_ext = paired_file.suffix.upper()
                                paired_type = 'image' if paired_ext in self.photo_extensions else 'video'
                                log_msg += (
                                    f" | Kept: {paired_file} | "
                                    f"Kept_Size: {format_size(paired_size)} | "
                                    f"Kept_Type: {paired_type} | "
                                    f"Mode: {analysis.cleanup_mode}"
                                )
                            except Exception as e:
                                self.logger.debug(f"No se pudo obtener info del archivo emparejado: {e}")
                                log_msg += f" | Kept: {paired_file} | Mode: {analysis.cleanup_mode}"
                        
                        self.logger.info(log_msg)
                        
                        # WARNING si el archivo eliminado es un video que supera el tamaño esperado
                        if file_info['type'] == 'video' and file_size > Config.LIVE_PHOTO_MAX_VIDEO_SIZE:
                            self.logger.warning(
                                f"⚠️  SOSPECHA: Video eliminado supera tamaño típico de Live Photo | "
                                f"Archivo: {file_path} | "
                                f"Tamaño: {format_size(file_size)} | "
                                f"Límite: {format_size(Config.LIVE_PHOTO_MAX_VIDEO_SIZE)} | "
                                f"Puede no ser realmente un video de Live Photo"
                            )

                except Exception as e:
                    error_msg = f"Error eliminando {file_path.name}: {str(e)}"
                    results.add_error(error_msg)
                    self.logger.error(error_msg)

            # Verificar éxito general
            results.success = len(results.errors) == 0

            # Preparar mensaje informativo teniendo en cuenta dry_run
            from utils.format_utils import format_size
            
            if dry_run:
                simulated_count = results.simulated_files_deleted
                simulated_space = results.simulated_space_freed
                freed = format_size(simulated_space)

                # Usar método centralizado de formato
                summary = self._format_operation_summary(
                    "Limpieza Live Photos",
                    simulated_count,
                    simulated_space,
                    dry_run
                )
                if results.errors:
                    summary += f"\nErrores: {len(results.errors)}"
                log_section_footer_relevant(self.logger, summary)
                
                # Construir mensaje para UI
                results.message = f"Simulación completada: {simulated_count} archivos ({freed}) se eliminarían"
            else:
                freed = format_size(results.space_freed)

                # Usar método centralizado de formato
                summary = self._format_operation_summary(
                    "Limpieza Live Photos",
                    results.files_deleted,
                    results.space_freed,
                    dry_run
                )
                log_section_footer_relevant(self.logger, summary)
                
                if results.errors:
                    self.logger.info(f"*** Errores encontrados durante la limpieza:")
                    for error in results.errors:
                        self.logger.error(f"  ✗ {error}")
                
                # Construir mensaje para UI
                results.message = f"Eliminados {results.files_deleted} archivos, liberados {freed}"
                if results.backup_path:
                    results.message += f"\n\nBackup creado en:\n{results.backup_path}"

        except Exception as e:
            error_msg = f"Error durante limpieza: {str(e)}"
            results.add_error(error_msg)
            results.message = error_msg
            self.logger.error(error_msg)

        return results

    # ==================== MÉTODOS PRIVADOS ====================

    def _detect_in_directory(
        self, 
        directory: Path, 
        recursive: bool = True, 
        progress_callback: Optional[Callable] = None,
        metadata_cache: Optional[FileMetadataCache] = None
    ) -> Optional[List[LivePhotoGroup]]:
        """
        Detecta Live Photos en un directorio.
        
        Args:
            directory: Directorio a analizar
            recursive: Si buscar recursivamente
            progress_callback: Callback opcional para progreso
            metadata_cache: Caché opcional de metadatos
            
        Returns:
            Lista de LivePhotoGroup detectados, o None si se canceló
        """
        self.logger.info(f"Detectando Live Photos en: {directory}")

        # Recopilar archivos
        photos = []
        videos = []
        
        # OPTIMIZACIÓN: Procesar en streaming sin bloquear
        # No crear lista completa primero (puede tardar minutos)
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        processed = 0

        self.logger.info(f"Escaneando archivos para detectar Live Photos...")

        for file_path in iterator:
            if not file_path.is_file():
                continue
                
            # Reportar progreso cada N archivos (progreso indeterminado)
            if processed % Config.UI_UPDATE_INTERVAL == 0 and progress_callback:
                if not progress_callback(processed, -1, "Escaneando archivos"):
                    self.logger.info("Detección de Live Photos cancelada por el usuario")
                    return None  # Señal de cancelación
            
            ext = file_path.suffix.upper()  # Convertir la extensión a mayúsculas
            
            if ext in self.photo_extensions:
                photos.append(file_path)
            elif ext in self.video_extensions:
                videos.append(file_path)
            
            processed += 1

        # Reportar finalización del escaneo
        if progress_callback:
            if not progress_callback(processed, processed, f"Escaneados {processed} archivos"):
                self.logger.info("Detección de Live Photos cancelada por el usuario")
                return None

        self.logger.info(f"Encontrados: {len(photos)} fotos, {len(videos)} videos")

        if not photos or not videos:
            return []

        # Detectar grupos con progreso
        self.logger.info("Iniciando matching de Live Photos...")
        groups = self._detect_live_photos(photos, videos, progress_callback, metadata_cache)

        if groups is None:  # Cancelación durante matching
            return None

        # Eliminar duplicados
        unique_groups = self._remove_duplicate_groups(groups)

        self.logger.info(f"Detectados {len(unique_groups)} grupos de Live Photos")

        return unique_groups

    def _normalize_name(self, name: str) -> str:
        """Normaliza el nombre eliminando sufijos comunes de fotos y videos"""
        name = name.lower()
        # Eliminar sufijos comunes que se añaden al renombrar
        suffixes = ['_photo', '_video', ' photo', ' video', '-photo', '-video']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name

    def _detect_live_photos(
        self, 
        photos: List[Path], 
        videos: List[Path], 
        progress_callback: Optional[Callable] = None,
        metadata_cache: Optional[FileMetadataCache] = None
    ) -> Optional[List[LivePhotoGroup]]:
        """
        Detecta Live Photos buscando parejas de fotos con videos .MOV.
        
        IMPORTANTE: Si Config.USE_VIDEO_METADATA está desactivado, la validación temporal
        se omite completamente, detectando Live Photos solo por coincidencia de nombres.
        Esto evita el costo de extraer metadata de video pero puede detectar falsos positivos.
        
        Args:
            photos: Lista de fotos a procesar
            videos: Lista de videos a buscar
            progress_callback: Callback opcional para reportar progreso
            metadata_cache: Caché opcional de metadatos para optimizar acceso a tamaños
            
        Returns:
            Lista de grupos encontrados, o None si se cancela
        """
        from config import Config
        
        groups = []
        total_photos = len(photos)
        
        # NOTA: Siempre validamos timestamps. Si Config.USE_VIDEO_METADATA está desactivado,
        # simplemente usaremos las fechas del sistema de archivos (mtime) que son rápidas y siempre disponibles.
        # La lógica de fallback está en _ensure_dates_loaded y get_date_from_file.
        
        self.logger.info(f"Construyendo mapa de videos ({len(videos)} videos)...")
        
        # Crear un mapa de nombres base a videos .MOV
        video_map = defaultdict(list)
        for video in videos:
            normalized_name = self._normalize_name(video.stem)
            video_map[normalized_name].append(video)

        self.logger.info(f"Mapa de videos construido con {len(video_map)} nombres únicos")
        self.logger.info(f"Procesando {total_photos} fotos para matching...")

        # Por cada foto, buscar su video .MOV correspondiente usando nombres normalizados
        for idx, photo in enumerate(photos, 1):
            # Verificar cancelación en cada iteración del UI_UPDATE_INTERVAL
            if progress_callback and idx % Config.UI_UPDATE_INTERVAL == 0:
                if not progress_callback(idx, total_photos, "Matching Live Photos"):
                    self.logger.info("Matching de Live Photos cancelado por el usuario")
                    return None  # Señal de cancelación
            
            # Log de progreso: según intervalo configurado en INFO, más detallado en DEBUG
            if idx % Config.LOG_PROGRESS_INTERVAL == 0:
                self.logger.info(f"Procesadas {idx}/{total_photos} fotos, {len(groups)} Live Photos encontrados hasta ahora")
            elif idx % Config.UI_UPDATE_INTERVAL == 0:
                self.logger.debug(f"Procesadas {idx}/{total_photos} fotos, {len(groups)} Live Photos encontrados hasta ahora")
            
            normalized_name = self._normalize_name(photo.stem)
            
            if normalized_name in video_map:
                original_name = photo.stem
                for video in video_map[normalized_name]:
                    if photo.parent == video.parent:
                        try:
                            # Intentar obtener tamaños de caché primero
                            image_size = None
                            video_size = None
                            if metadata_cache:
                                image_size = metadata_cache.get_size(photo)
                                video_size = metadata_cache.get_size(video)
                            
                            # Si no están en caché, obtener del filesystem
                            if image_size is None:
                                image_size = photo.stat().st_size
                            if video_size is None:
                                video_size = video.stat().st_size
                            
                            group = LivePhotoGroup(
                                image_path=photo,
                                video_path=video,
                                base_name=original_name,
                                directory=photo.parent,
                                image_size=image_size,
                                video_size=video_size,
                                metadata_cache=metadata_cache
                            )
                            
                            # Validar diferencia de tiempo SIEMPRE
                            # Usamos el método time_difference del grupo que ya maneja la lógica de
                            # usar caché o fallback rápido (skip_expensive_ops) para no bloquear.
                            
                            time_diff = group.time_difference
                            if time_diff <= self.time_tolerance:
                                groups.append(group)
                                self.logger.debug(f"Live Photo válido: {original_name} (Δt={time_diff:.2f}s)")
                            else:
                                # Obtener las fechas AJUSTADAS usadas en la comparación
                                img_d_comp, vid_d_comp, img_s_comp, vid_s_comp = group.get_comparison_dates()
                                
                                # Formatear fechas para el log
                                img_d = img_d_comp.strftime('%Y-%m-%d %H:%M:%S') if img_d_comp else 'None'
                                vid_d = vid_d_comp.strftime('%Y-%m-%d %H:%M:%S') if vid_d_comp else 'None'
                                
                                # Indicar si hubo ajuste de fecha
                                adjustment_note = ""
                                if "→mtime_adjusted" in img_s_comp:
                                    adjustment_note = " [Img ajustada a mtime porque video no tiene metadata interna]"
                                elif "video_metadata_from_cache" in vid_s_comp:
                                    adjustment_note = " [Video usa metadata interna en vez de mtime para comparación precisa]"
                                
                                self.logger.debug(
                                    f"Par rechazado por diferencia de tiempo: {original_name} "
                                    f"(Δt={time_diff:.2f}s > {self.time_tolerance}s){adjustment_note} | "
                                    f"Img: {img_d} ({img_s_comp}) | "
                                    f"Vid: {vid_d} ({vid_s_comp})"
                                )
                        except Exception as e:
                            self.logger.warning(f"Error creando grupo para {original_name}: {e}")

        # Log final
        self.logger.info(f"Matching completado: {len(groups)} Live Photos válidos encontrados")
        
        return groups

    def _remove_duplicate_groups(self, groups: List[LivePhotoGroup]) -> List[LivePhotoGroup]:
        """Elimina grupos duplicados, priorizando los que tienen mejor validación temporal"""
        unique_groups = []
        seen_pairs = set()

        # Ordenar por time_difference (menor = más confiable)
        sorted_groups = sorted(groups, key=lambda g: g.time_difference)

        for group in sorted_groups:
            pair_id = (str(group.image_path), str(group.video_path))

            if pair_id not in seen_pairs:
                unique_groups.append(group)
                seen_pairs.add(pair_id)

        return unique_groups

    def _generate_cleanup_plan(
        self, 
        live_photos: List[LivePhotoGroup], 
        mode: CleanupMode
    ) -> dict:
        """
        Genera plan de limpieza según el modo especificado.
        
        Maneja correctamente múltiples imágenes compartiendo el mismo video:
        - KEEP_IMAGE: mantiene TODAS las imágenes, elimina el video UNA vez
        - KEEP_VIDEO: elimina TODAS las imágenes, mantiene el video UNA vez
        
        Args:
            live_photos: Grupos de Live Photos detectados (puede haber múltiples con mismo video)
            mode: Modo de limpieza a aplicar
            
        Returns:
            Dict con keys 'files_to_delete' y 'files_to_keep'
        """
        plan = {
            'files_to_delete': [],
            'files_to_keep': []
        }
        
        # Usar sets para evitar duplicados cuando múltiples imágenes comparten el mismo video
        seen_delete = set()
        seen_keep = set()

        for lp in live_photos:
            if mode == CleanupMode.KEEP_IMAGE:
                # Mantener imagen, eliminar video
                keep_key = str(lp.image_path)
                delete_key = str(lp.video_path)
                
                # Siempre añadir la imagen (puede haber múltiples imágenes)
                if keep_key not in seen_keep:
                    plan['files_to_keep'].append({
                        'path': lp.image_path,
                        'type': 'image',
                        'size': lp.image_size,
                        'base_name': lp.base_name
                    })
                    seen_keep.add(keep_key)
                
                # Solo añadir el video UNA vez (aunque esté en múltiples grupos)
                if delete_key not in seen_delete:
                    plan['files_to_delete'].append({
                        'path': lp.video_path,
                        'type': 'video', 
                        'size': lp.video_size,
                        'base_name': lp.base_name,
                        'paired_file': lp.image_path  # Archivo que se mantiene
                    })
                    seen_delete.add(delete_key)

            elif mode == CleanupMode.KEEP_VIDEO:
                # Mantener video, eliminar imagen
                keep_key = str(lp.video_path)
                delete_key = str(lp.image_path)
                
                # Solo añadir el video UNA vez (aunque esté en múltiples grupos)
                if keep_key not in seen_keep:
                    plan['files_to_keep'].append({
                        'path': lp.video_path,
                        'type': 'video',
                        'size': lp.video_size,
                        'base_name': lp.base_name
                    })
                    seen_keep.add(keep_key)
                
                # Siempre añadir la imagen (puede haber múltiples imágenes)
                if delete_key not in seen_delete:
                    plan['files_to_delete'].append({
                        'path': lp.image_path,
                        'type': 'image',
                        'size': lp.image_size,
                        'base_name': lp.base_name,
                        'paired_file': lp.video_path  # Archivo que se mantiene
                    })
                    seen_delete.add(delete_key)

            elif mode == CleanupMode.KEEP_LARGER:
                # Mantener el archivo más grande
                if lp.image_size >= lp.video_size:
                    keep_path, keep_type, keep_size = lp.image_path, 'image', lp.image_size
                    delete_path, delete_type, delete_size = lp.video_path, 'video', lp.video_size
                else:
                    keep_path, keep_type, keep_size = lp.video_path, 'video', lp.video_size
                    delete_path, delete_type, delete_size = lp.image_path, 'image', lp.image_size
                
                keep_key = str(keep_path)
                delete_key = str(delete_path)
                
                if keep_key not in seen_keep:
                    plan['files_to_keep'].append({
                        'path': keep_path,
                        'type': keep_type,
                        'size': keep_size,
                        'base_name': lp.base_name
                    })
                    seen_keep.add(keep_key)
                
                if delete_key not in seen_delete:
                    plan['files_to_delete'].append({
                        'path': delete_path,
                        'type': delete_type,
                        'size': delete_size,
                        'base_name': lp.base_name,
                        'paired_file': keep_path  # Archivo que se mantiene
                    })
                    seen_delete.add(delete_key)

            elif mode == CleanupMode.KEEP_SMALLER:
                # Mantener el archivo más pequeño
                if lp.image_size <= lp.video_size:
                    keep_path, keep_type, keep_size = lp.image_path, 'image', lp.image_size
                    delete_path, delete_type, delete_size = lp.video_path, 'video', lp.video_size
                else:
                    keep_path, keep_type, keep_size = lp.video_path, 'video', lp.video_size
                    delete_path, delete_type, delete_size = lp.image_path, 'image', lp.image_size
                
                keep_key = str(keep_path)
                delete_key = str(delete_path)
                
                if keep_key not in seen_keep:
                    plan['files_to_keep'].append({
                        'path': keep_path,
                        'type': keep_type,
                        'size': keep_size,
                        'base_name': lp.base_name
                    })
                    seen_keep.add(keep_key)
                
                if delete_key not in seen_delete:
                    plan['files_to_delete'].append({
                        'path': delete_path,
                        'type': delete_type,
                        'size': delete_size,
                        'base_name': lp.base_name,
                        'paired_file': keep_path  # Archivo que se mantiene
                    })
                    seen_delete.add(delete_key)

        return plan
