"""
Limpiador de Live Photos - DEPRECATED

ESTE MÓDULO ESTÁ OBSOLETO Y SERÁ ELIMINADO EN UNA VERSIÓN FUTURA.
Por favor, usa LivePhotoService en su lugar.

Migración:
    ANTES:
        from services.live_photo_cleaner import LivePhotoCleaner, CleanupMode
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(directory, CleanupMode.KEEP_IMAGE)
        result = cleaner.execute_cleanup(analysis, create_backup=True)
    
    DESPUÉS:
        from services.live_photo_service import LivePhotoService, CleanupMode
        service = LivePhotoService()
        analysis = service.analyze(directory, cleanup_mode=CleanupMode.KEEP_IMAGE)
        result = service.execute(analysis, create_backup=True)
"""
import shutil
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from enum import Enum
import warnings

from config import Config
from utils.logger import get_logger
from utils.decorators import deprecated
from services.live_photo_detector import LivePhotoGroup, LivePhotoDetector
from services.result_types import LivePhotoCleanupAnalysisResult, LivePhotoCleanupResult
from services.base_service import BaseService

# Emitir advertencia al importar
warnings.warn(
    "LivePhotoCleaner está obsoleto. Usa LivePhotoService en su lugar.",
    DeprecationWarning,
    stacklevel=2
)

class CleanupMode(Enum):
    """Modos de limpieza de Live Photos"""
    KEEP_IMAGE = "keep_image"          # Mantener imagen, eliminar video
    KEEP_VIDEO = "keep_video"          # Mantener video, eliminar imagen
    KEEP_LARGER = "keep_larger"        # Mantener el archivo más grande
    KEEP_SMALLER = "keep_smaller"      # Mantener el archivo más pequeño
    CUSTOM = "custom"                  # Selección manual por archivo

@deprecated(
    reason="Usa LivePhotoService que integra detección y limpieza en una sola clase",
    replacement="LivePhotoService"
)
class LivePhotoCleaner(BaseService):
    """
    Limpiador seguro de Live Photos con backup y confirmación
    
    DEPRECATED: Esta clase será eliminada. Usa LivePhotoService en su lugar.
    """

    def __init__(self):
        super().__init__("LivePhotoCleaner")
        self.detector = LivePhotoDetector()
        self.dry_run = False

        # Estadísticas de limpieza
        self.cleanup_stats = {
            'live_photos_processed': 0,
            'files_deleted': 0,
            'files_kept': 0,
            'space_freed': 0,
            'errors': 0,
            'backup_created': False
        }

    def analyze(self, directory: Path, mode: CleanupMode = CleanupMode.KEEP_IMAGE) -> LivePhotoCleanupAnalysisResult:
        """
        Analiza qué archivos se eliminarían con el modo dado (método unificado)

        Args:
            directory: Directorio a analizar
            mode: Modo de limpieza a aplicar

        Returns:
            LivePhotoCleanupAnalysisResult con el análisis de limpieza
        """
        return self.analyze_cleanup(directory, mode)

    def execute(self, cleanup_analysis: LivePhotoCleanupAnalysisResult, create_backup: bool = True, dry_run: bool = False, progress_callback=None) -> LivePhotoCleanupResult:
        """
        Ejecuta la limpieza de Live Photos (método unificado)

        Args:
            cleanup_analysis: Resultado del análisis previo
            create_backup: Si crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar
            progress_callback: Función opcional para reportar progreso

        Returns:
            LivePhotoCleanupResult con el resultado de la operación
        """
        return self.execute_cleanup(cleanup_analysis, create_backup, dry_run, progress_callback)

    @deprecated(reason="Nomenclatura inconsistente", replacement="analyze()")
    def analyze_cleanup(self, directory: Path, mode: CleanupMode = CleanupMode.KEEP_IMAGE) -> LivePhotoCleanupAnalysisResult:
        """
        Analiza qué archivos se eliminarían con el modo dado

        Args:
            directory: Directorio a analizar
            mode: Modo de limpieza

        Returns:
            Análisis detallado de la limpieza propuesta
        """
        self.logger.info(f"Analizando limpieza de Live Photos en: {directory}")

        # Detectar Live Photos
        live_photos = self.detector.detect_in_directory(directory)

        if not live_photos:
            return LivePhotoCleanupAnalysisResult(
                total_files=0,
                live_photos_found=0,
                files_to_delete=[],
                files_to_keep=[],
                space_to_free=0,
                total_space=0,
                cleanup_mode=mode.value
            )

        # Generar plan de limpieza
        cleanup_plan = self._generate_cleanup_plan(live_photos, mode)

        # Calcular estadísticas
        total_space = sum(lp.total_size for lp in live_photos)
        space_to_free = sum(item['size'] for item in cleanup_plan['files_to_delete'])

        result = LivePhotoCleanupAnalysisResult(
            total_files=len(live_photos) * 2,
            live_photos_found=len(live_photos),
            files_to_delete=cleanup_plan['files_to_delete'],
            files_to_keep=cleanup_plan['files_to_keep'],
            space_to_free=space_to_free,
            total_space=total_space,
            cleanup_mode=mode.value
        )

        self.logger.info(f"Análisis completado: {len(cleanup_plan['files_to_delete'])} archivos a eliminar")
        
        # Logging detallado de archivos a eliminar
        from utils.format_utils import format_size
        self.logger.info("=" * 80)
        self.logger.info("ANÁLISIS DE LIVE PHOTOS - ARCHIVOS A ELIMINAR:")
        for file_info in cleanup_plan['files_to_delete']:
            self.logger.info(f"  → A eliminar: {file_info['path']} ({file_info['type']}, {format_size(file_info['size'])})")
        
        self.logger.info("ARCHIVOS A CONSERVAR:")
        for file_info in cleanup_plan['files_to_keep']:
            self.logger.info(f"  ✓ A conservar: {file_info['path']} ({file_info['type']}, {format_size(file_info['size'])})")
        self.logger.info("=" * 80)
        
        return result

    def _generate_cleanup_plan(self, live_photos: List[LivePhotoGroup], mode: CleanupMode) -> Dict:
        """Genera plan de limpieza según el modo especificado"""
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

    # Backup creation delegated to utils.file_utils.create_backup

    @deprecated(reason="Nomenclatura inconsistente", replacement="execute()")
    def execute_cleanup(self, cleanup_analysis: LivePhotoCleanupAnalysisResult, create_backup: bool = True, 
                       dry_run: bool = False, progress_callback=None) -> LivePhotoCleanupResult:
        """
        Ejecuta la limpieza de Live Photos

        Args:
            cleanup_analysis: Análisis de limpieza previo (SOLO acepta dataclass)
            create_backup: Si crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar archivos reales

        Returns:
            Resultados de la limpieza
        """
        files_to_delete = cleanup_analysis.files_to_delete

        if not files_to_delete:
            return LivePhotoCleanupResult(
                success=True,
                files_deleted=0,
                space_freed=0,
                dry_run=dry_run,
                message='No hay archivos para eliminar'
            )

        mode_label = "SIMULACIÓN" if dry_run else ""
        self._log_section_header(
            "INICIANDO LIMPIEZA DE LIVE PHOTOS",
            mode=mode_label
        )
        self.logger.info(f"*** Archivos a procesar: {len(files_to_delete)}")
        
        self.dry_run = dry_run
        self._reset_cleanup_stats()

        results = LivePhotoCleanupResult(success=True, dry_run=dry_run)

        try:
            # Determinar directorio base para backup
            if files_to_delete:
                first_file = files_to_delete[0]['path']
                base_directory = first_file.parent

                # Encontrar directorio común
                for file_info in files_to_delete[1:]:
                    try:
                        base_directory = Path(os.path.commonpath([base_directory, file_info['path'].parent]))
                    except ValueError:
                        # Si no hay path común, usar el primer directorio
                        break

            # Crear backup usando método centralizado (solo si no es simulación)
            if create_backup and not dry_run:
                try:
                    from services.base_service import BackupCreationError
                    backup_path = self._create_backup_for_operation(
                        files_to_delete,
                        'livephoto_cleanup',
                        progress_callback
                    )
                    if backup_path:
                        results.backup_path = str(backup_path)
                        self.cleanup_stats['backup_created'] = True
                except BackupCreationError as e:
                    error_msg = f"Error creando backup: {e}"
                    self.logger.error(error_msg)
                    results.add_error(error_msg)
                    return results

            # Ejecutar eliminaciones
            for file_info in files_to_delete:
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
                            self.logger.info(f"[SIMULACIÓN] Eliminaría: {file_path} ({file_info['type']}, {format_size(file_size)})")
                        else:
                            error_msg = f"Archivo no encontrado (simulación): {file_path}"
                            results.add_error(error_msg)
                            self.logger.warning(f"[SIMULACIÓN] {error_msg}")
                    else:
                        # Eliminar realmente
                        if not file_path.exists():
                            error_msg = f"Archivo no encontrado: {file_path}"
                            results.add_error(error_msg)
                            self.cleanup_stats['errors'] += 1
                            self.logger.error(error_msg)
                            continue

                        # Eliminar archivo
                        file_path.unlink()

                        # Registrar éxito
                        results.files_deleted += 1
                        results.space_freed += file_size
                        results.deleted_files.append(str(file_path))

                        self.cleanup_stats['files_deleted'] += 1
                        self.cleanup_stats['space_freed'] += file_size
                        
                        from utils.format_utils import format_size
                        self.logger.info(f"✓ Eliminado: {file_path} ({file_info['type']}, {format_size(file_size)})")

                except Exception as e:
                    error_msg = f"Error eliminando {file_path.name}: {str(e)}"
                    results.add_error(error_msg)
                    self.cleanup_stats['errors'] += 1
                    self.logger.error(error_msg)
                    self.logger.error(error_msg)

            # Verificar éxito general
            self.cleanup_stats['live_photos_processed'] = len(files_to_delete)
            results.success = len(results.errors) == 0

            # Preparar mensaje informativo teniendo en cuenta dry_run
            if dry_run:
                simulated_count = results.simulated_files_deleted
                simulated_space = results.simulated_space_freed
                from utils.format_utils import format_size
                freed = format_size(simulated_space)

                summary = f"LIMPIEZA DE LIVE PHOTOS COMPLETADA\nResultado: {simulated_count} archivos, {freed} potencialmente liberados"
                if results.errors:
                    summary += f"\nErrores: {len(results.errors)}"
                self._log_section_footer(summary)
                
                # Construir mensaje para UI
                results.message = f"Simulación completada: {simulated_count} archivos ({freed}) se eliminarían"
            else:
                try:
                    from utils.format_utils import format_size
                    freed = format_size(results.space_freed)
                except Exception:
                    freed = f"{results.space_freed/(1024*1024):.2f} MB"

                summary = f"LIMPIEZA DE LIVE PHOTOS COMPLETADA\nResultado: {results.files_deleted} archivos eliminados, {freed} liberados"
                self._log_section_footer(summary)
                
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

    def _reset_cleanup_stats(self):
        """Reinicia estadísticas de limpieza"""
        for key in self.cleanup_stats:
            if isinstance(self.cleanup_stats[key], bool):
                self.cleanup_stats[key] = False
            else:
                self.cleanup_stats[key] = 0

    def get_cleanup_stats(self) -> Dict:
        """Obtiene estadísticas de limpieza"""
        return self.cleanup_stats.copy()

    def restore_from_backup(self, backup_path: Path) -> Dict:
        """
        Restaura archivos desde un backup (funcionalidad futura)

        Args:
            backup_path: Ruta del backup

        Returns:
            Resultados de la restauración
        """
        # Funcionalidad para restaurar archivos eliminados
        # (implementar en versión futura si es necesario)
        return {
            'success': False,
            'message': 'Funcionalidad de restauración no implementada aún'
        }

