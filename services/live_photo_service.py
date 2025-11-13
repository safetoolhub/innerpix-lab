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
from services.result_types import LivePhotoCleanupAnalysisResult, LivePhotoCleanupResult
from services.base_service import BaseService, BackupCreationError
from utils.logger import log_section_header_discrete, log_section_footer_discrete, log_section_header_relevant, log_section_footer_relevant


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

    def __post_init__(self):
        """Validaciones y cálculos adicionales"""
        if not self.image_path.exists():
            raise ValueError(f"Imagen no existe: {self.image_path}")
        if not self.video_path.exists():
            raise ValueError(f"Video no existe: {self.video_path}")

        if not self.image_date:
            self.image_date = datetime.fromtimestamp(self.image_path.stat().st_mtime)
        if not self.video_date:
            self.video_date = datetime.fromtimestamp(self.video_path.stat().st_mtime)

    @property
    def total_size(self) -> int:
        """Tamaño total del grupo"""
        return self.image_size + self.video_size

    @property
    def time_difference(self) -> float:
        """Diferencia en segundos entre imagen y video"""
        if self.image_date and self.video_date:
            return abs((self.image_date - self.video_date).total_seconds())
        return 0.0


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
        
        self.logger.debug(f"Extensiones de foto configuradas: {self.photo_extensions}")
        self.logger.debug(f"Extensiones de video configuradas: {self.video_extensions}")

        # Tolerancia de tiempo para matching (5 segundos máximo)
        self.time_tolerance = 5.0

    def analyze(
        self, 
        directory: Path,
        cleanup_mode: CleanupMode = CleanupMode.KEEP_IMAGE,
        recursive: bool = True,
        progress_callback: Optional[Callable[[int, int, str], bool]] = None
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
            
        Returns:
            LivePhotoCleanupAnalysisResult con plan de limpieza detallado
        
        Raises:
            ValueError: Si directory no existe
        """
        log_section_header_discrete(self.logger, "ANÁLISIS DE LIVE PHOTOS")
        self.logger.info(f"Analizando en: {directory}")
        self.logger.info(f"Modo de limpieza: {cleanup_mode.value}")

        if not directory.exists():
            raise ValueError(f"Directorio no existe: {directory}")

        # Paso 1: Detectar Live Photos
        live_photos = self._detect_in_directory(directory, recursive, progress_callback)
        
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
        
        self.logger.info(f"Análisis completado: {len(cleanup_plan['files_to_delete'])} archivos a eliminar")

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
                except BackupCreationError as e:
                    error_msg = f"Error creando backup: {e}"
                    self.logger.error(error_msg)
                    results.add_error(error_msg)
                    return results

            # Ejecutar eliminaciones
            total = len(files_to_delete)
            for idx, file_info in enumerate(files_to_delete):
                # Reportar progreso cada 1000 archivos
                if (idx + 1) % 1000 == 0:
                    self.logger.info(f"Procesados {idx + 1}/{total} archivos en limpieza de Live Photos")

                # Reportar progreso
                if progress_callback:
                    if not progress_callback(idx + 1, total, f"Procesando {idx + 1}/{total}"):
                        self.logger.info("Limpieza cancelada por el usuario")
                        break

                file_path = file_info['path']
                file_size = file_info['size']

                try:
                    if dry_run:
                        # Solo simular: no modificar counters reales, usar campos simulados
                        if file_path.exists():
                            results.simulated_files_deleted += 1
                            results.simulated_space_freed += file_size
                            results.deleted_files.append(str(file_path))
                            from utils.format_utils import format_size
                            self.logger.debug(f"[SIMULACIÓN] Eliminaría: {file_path} ({file_info['type']}, {format_size(file_size)})")
                        else:
                            error_msg = f"Archivo no encontrado (simulación): {file_path}"
                            results.add_error(error_msg)
                            self.logger.warning(f"[SIMULACIÓN] {error_msg}")
                    else:
                        # Eliminar realmente
                        if not file_path.exists():
                            error_msg = f"Archivo no encontrado: {file_path}"
                            results.add_error(error_msg)
                            self.logger.error(error_msg)
                            continue

                        # Eliminar archivo
                        file_path.unlink()

                        # Registrar éxito
                        results.files_deleted += 1
                        results.space_freed += file_size
                        results.deleted_files.append(str(file_path))
                        
                        from utils.format_utils import format_size
                        self.logger.debug(f"✓ Eliminado: {file_path} ({file_info['type']}, {format_size(file_size)})")

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
        progress_callback: Optional[Callable] = None
    ) -> Optional[List[LivePhotoGroup]]:
        """
        Detecta Live Photos en un directorio.
        
        Args:
            directory: Directorio a analizar
            recursive: Si buscar recursivamente
            progress_callback: Callback opcional para progreso
            
        Returns:
            Lista de LivePhotoGroup detectados, o None si se canceló
        """
        self.logger.info(f"Detectando Live Photos en: {directory}")

        # Recopilar archivos
        photos = []
        videos = []
        
        # Primero contamos total de archivos para progress
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        all_files = [f for f in iterator if f.is_file()]
        total_files = len(all_files)
        processed = 0

        self.logger.info(f"Escaneando {total_files} archivos para detectar Live Photos")

        for file_path in all_files:
            # Reportar progreso y verificar si se solicitó cancelación
            if progress_callback:
                if not progress_callback(processed, total_files, "Detectando Live Photos"):
                    self.logger.info("Detección de Live Photos cancelada por el usuario")
                    return None  # Señal de cancelación
            
            ext = file_path.suffix.upper()  # Convertir la extensión a mayúsculas
            
            if ext in self.photo_extensions:
                photos.append(file_path)
            elif ext in self.video_extensions:
                videos.append(file_path)
            
            processed += 1

        # Reportar progreso final (100%)
        if progress_callback:
            if not progress_callback(total_files, total_files, "Detectando Live Photos"):
                self.logger.info("Detección de Live Photos cancelada por el usuario")
                return None

        self.logger.info(f"Encontrados: {len(photos)} fotos, {len(videos)} videos")

        if not photos or not videos:
            return []

        # Detectar grupos con progreso
        self.logger.info("Iniciando matching de Live Photos...")
        groups = self._detect_live_photos(photos, videos, progress_callback)

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
        progress_callback: Optional[Callable] = None
    ) -> Optional[List[LivePhotoGroup]]:
        """
        Detecta Live Photos buscando parejas de fotos con videos .MOV.
        
        Args:
            photos: Lista de fotos a procesar
            videos: Lista de videos a buscar
            progress_callback: Callback opcional para reportar progreso
            
        Returns:
            Lista de grupos encontrados, o None si se cancela
        """
        groups = []
        total_photos = len(photos)
        
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
            # Reportar progreso cada 1000 fotos
            if idx % 1000 == 0:
                self.logger.info(f"Procesadas {idx}/{total_photos} fotos, {len(groups)} Live Photos encontrados hasta ahora")
                
                # Verificar cancelación
                if progress_callback:
                    if not progress_callback(idx, total_photos, "Matching Live Photos"):
                        self.logger.info("Matching de Live Photos cancelado por el usuario")
                        return None  # Señal de cancelación
            
            normalized_name = self._normalize_name(photo.stem)
            
            if normalized_name in video_map:
                original_name = photo.stem
                for video in video_map[normalized_name]:
                    if photo.parent == video.parent:
                        try:
                            group = LivePhotoGroup(
                                image_path=photo,
                                video_path=video,
                                base_name=original_name,
                                directory=photo.parent,
                                image_size=photo.stat().st_size,
                                video_size=video.stat().st_size
                            )
                            
                            # Validar diferencia de tiempo (debe ser <= 5 segundos)
                            if group.time_difference <= self.time_tolerance:
                                groups.append(group)
                                self.logger.debug(f"Live Photo válido: {original_name} (Δt={group.time_difference:.2f}s)")
                            else:
                                self.logger.debug(
                                    f"Par rechazado por diferencia de tiempo: {original_name} "
                                    f"(Δt={group.time_difference:.2f}s > {self.time_tolerance}s)"
                                )
                        except Exception as e:
                            self.logger.warning(f"Error creando grupo para {original_name}: {e}")

        # Log final
        self.logger.info(f"Matching completado: {len(groups)} Live Photos válidos encontrados")
        
        return groups

    def _remove_duplicate_groups(self, groups: List[LivePhotoGroup]) -> List[LivePhotoGroup]:
        """Elimina grupos duplicados"""
        unique_groups = []
        seen_pairs = set()

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
        
        Args:
            live_photos: Grupos de Live Photos detectados
            mode: Modo de limpieza a aplicar
            
        Returns:
            Dict con keys 'files_to_delete' y 'files_to_keep'
        """
        plan = {
            'files_to_delete': [],
            'files_to_keep': []
        }

        for lp in live_photos:
            if mode == CleanupMode.KEEP_IMAGE:
                # Mantener imagen, eliminar video
                plan['files_to_keep'].append({
                    'path': lp.image_path,
                    'type': 'image',
                    'size': lp.image_size,
                    'base_name': lp.base_name
                })
                plan['files_to_delete'].append({
                    'path': lp.video_path,
                    'type': 'video', 
                    'size': lp.video_size,
                    'base_name': lp.base_name
                })

            elif mode == CleanupMode.KEEP_VIDEO:
                # Mantener video, eliminar imagen
                plan['files_to_keep'].append({
                    'path': lp.video_path,
                    'type': 'video',
                    'size': lp.video_size,
                    'base_name': lp.base_name
                })
                plan['files_to_delete'].append({
                    'path': lp.image_path,
                    'type': 'image',
                    'size': lp.image_size,
                    'base_name': lp.base_name
                })

            elif mode == CleanupMode.KEEP_LARGER:
                # Mantener el archivo más grande
                if lp.image_size >= lp.video_size:
                    keep_path, keep_type, keep_size = lp.image_path, 'image', lp.image_size
                    delete_path, delete_type, delete_size = lp.video_path, 'video', lp.video_size
                else:
                    keep_path, keep_type, keep_size = lp.video_path, 'video', lp.video_size
                    delete_path, delete_type, delete_size = lp.image_path, 'image', lp.image_size

                plan['files_to_keep'].append({
                    'path': keep_path,
                    'type': keep_type,
                    'size': keep_size,
                    'base_name': lp.base_name
                })
                plan['files_to_delete'].append({
                    'path': delete_path,
                    'type': delete_type,
                    'size': delete_size,
                    'base_name': lp.base_name
                })

            elif mode == CleanupMode.KEEP_SMALLER:
                # Mantener el archivo más pequeño
                if lp.image_size <= lp.video_size:
                    keep_path, keep_type, keep_size = lp.image_path, 'image', lp.image_size
                    delete_path, delete_type, delete_size = lp.video_path, 'video', lp.video_size
                else:
                    keep_path, keep_type, keep_size = lp.video_path, 'video', lp.video_size
                    delete_path, delete_type, delete_size = lp.image_path, 'image', lp.image_size

                plan['files_to_keep'].append({
                    'path': keep_path,
                    'type': keep_type,
                    'size': keep_size,
                    'base_name': lp.base_name
                })
                plan['files_to_delete'].append({
                    'path': delete_path,
                    'type': delete_type,
                    'size': delete_size,
                    'base_name': lp.base_name
                })

        return plan
