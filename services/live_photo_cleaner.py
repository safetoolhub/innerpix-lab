"""
Limpiador de Live Photos - Eliminación segura con backup
"""
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from enum import Enum

import config
from utils.logger import get_logger
from services.live_photo_detector import LivePhotoGroup, LivePhotoDetector

class CleanupMode(Enum):
    """Modos de limpieza de Live Photos"""
    KEEP_IMAGE = "keep_image"          # Mantener imagen, eliminar video
    KEEP_VIDEO = "keep_video"          # Mantener video, eliminar imagen
    KEEP_LARGER = "keep_larger"        # Mantener el archivo más grande
    KEEP_SMALLER = "keep_smaller"      # Mantener el archivo más pequeño
    CUSTOM = "custom"                  # Selección manual por archivo

class LivePhotoCleaner:
    """
    Limpiador seguro de Live Photos con backup y confirmación
    """

    def __init__(self):
        self.logger = get_logger("LivePhotoCleaner")
        self.detector = LivePhotoDetector()

        # Estado del limpiador
        self.backup_dir = None
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

    def analyze_cleanup(self, directory: Path, mode: CleanupMode = CleanupMode.KEEP_IMAGE) -> Dict:
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
            return {
                'live_photos_found': 0,
                'files_to_delete': [],
                'files_to_keep': [],
                'space_to_free': 0,
                'total_space': 0,
                'cleanup_mode': mode.value
            }

        # Generar plan de limpieza
        cleanup_plan = self._generate_cleanup_plan(live_photos, mode)

        # Calcular estadísticas
        total_space = sum(lp.total_size for lp in live_photos)
        space_to_free = sum(item['size'] for item in cleanup_plan['files_to_delete'])

        result = {
            'live_photos_found': len(live_photos),
            'files_to_delete': cleanup_plan['files_to_delete'],
            'files_to_keep': cleanup_plan['files_to_keep'],
            'space_to_free': space_to_free,
            'total_space': total_space,
            'cleanup_mode': mode.value,
            'space_savings_percent': (space_to_free / total_space * 100) if total_space > 0 else 0,
            'detailed_analysis': self.detector.analyze_live_photos(live_photos)
        }

        self.logger.info(f"Análisis completado: {len(cleanup_plan['files_to_delete'])} archivos a eliminar")
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

    def create_backup(self, files_to_delete: List[Dict], base_directory: Path, progress_callback=None) -> Path:
        """
        Crea backup de archivos antes de eliminarlos

        Args:
            files_to_delete: Lista de archivos a eliminar
            base_directory: Directorio base para estructurar backup

        Returns:
            Ruta del backup creado
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_livephoto_cleanup_{base_directory.name}_{timestamp}"

        # Crear directorio de backup
        backup_path = config.config.DEFAULT_BACKUP_DIR / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Creando backup de Live Photos en: {backup_path}")

        # Informar al UI/worker sobre la ruta del backup
        total_files = len(files_to_delete)
        if progress_callback:
            try:
                progress_callback(0, total_files, f"Creando backup en: {backup_path}")
            except Exception:
                pass

        files_backed_up = 0
        backup_size = 0

        for file_info in files_to_delete:
            file_path = file_info['path']

            try:
                # Calcular ruta relativa desde el directorio base
                if base_directory in file_path.parents:
                    relative_path = file_path.relative_to(base_directory)
                else:
                    # Si no está en el directorio base, usar nombre del directorio padre + archivo
                    relative_path = file_path.parent.name / file_path.name

                backup_file_path = backup_path / relative_path

                # Crear directorios padre si es necesario
                backup_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Copiar archivo
                shutil.copy2(file_path, backup_file_path)

                files_backed_up += 1
                backup_size += file_info['size']

                self.logger.debug(f"Backup creado: {file_path.name}")

                # Emitir progreso intermedio incluyendo la ruta del backup
                if progress_callback:
                    try:
                        progress_callback(files_backed_up, total_files, f"Creando backup en: {backup_path} ({files_backed_up}/{total_files})")
                    except Exception:
                        pass

            except Exception as e:
                self.logger.error(f"Error creando backup de {file_path}: {e}")
                raise

        # Crear archivo de metadatos del backup
        metadata_path = backup_path / "backup_metadata.txt"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write("BACKUP DE LIMPIEZA DE LIVE PHOTOS\n")
            f.write(f"Creado: {datetime.now()}\n")
            f.write(f"Directorio original: {base_directory}\n")
            f.write(f"Archivos respaldados: {files_backed_up}\n")
            try:
                from ui.helpers import format_size
                f.write(f"Tamaño total: {format_size(backup_size)}\n")
            except Exception:
                f.write(f"Tamaño total: {backup_size / (1024*1024):.2f} MB\n")
            f.write("\nARCHIVOS RESPALDADOS:\n")
            for file_info in files_to_delete:
                f.write(f"- {file_info['path']} ({file_info['type']})\n")

        self.backup_dir = backup_path
        self.cleanup_stats['backup_created'] = True

        try:
            from ui.helpers import format_size
            self.logger.info(f"Backup completado: {files_backed_up} archivos, {format_size(backup_size)}")
        except Exception:
            self.logger.info(f"Backup completado: {files_backed_up} archivos, {backup_size/(1024*1024):.2f} MB")
        return backup_path

    def execute_cleanup(self, cleanup_analysis: Dict, create_backup: bool = True, 
                       dry_run: bool = False, progress_callback=None) -> Dict:
        """
        Ejecuta la limpieza de Live Photos

        Args:
            cleanup_analysis: Análisis de limpieza previo
            create_backup: Si crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar archivos reales

        Returns:
            Resultados de la limpieza
        """
        files_to_delete = cleanup_analysis['files_to_delete']

        if not files_to_delete:
            return {
                'success': True,
                'files_deleted': 0,
                'space_freed': 0,
                'errors': [],
                'dry_run': dry_run,
                'backup_path': None,
                'message': 'No hay archivos para eliminar'
            }

        self.logger.info(f"Iniciando limpieza de Live Photos: {len(files_to_delete)} archivos")
        self.dry_run = dry_run
        self._reset_cleanup_stats()

        results = {
            'success': True,
            'files_deleted': 0,
            'space_freed': 0,
            'errors': [],
            'deleted_files': [],
            'dry_run': dry_run,
            'backup_path': None
        }

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

            # Crear backup si se solicita
            if create_backup and not dry_run:
                backup_path = self.create_backup(files_to_delete, base_directory, progress_callback=progress_callback)
                results['backup_path'] = str(backup_path)

            # Ejecutar eliminaciones
            for file_info in files_to_delete:
                file_path = file_info['path']
                file_size = file_info['size']

                try:
                    if dry_run:
                        # Solo simular
                        if file_path.exists():
                            results['files_deleted'] += 1
                            results['space_freed'] += file_size
                            results['deleted_files'].append({
                                'path': str(file_path),
                                'type': file_info['type'],
                                'size': file_size,
                                'base_name': file_info['base_name'],
                                'simulated': True
                            })

                            self.logger.debug(f"SIMULADO - Eliminaría: {file_path.name}")
                        else:
                            results['errors'].append(f"Archivo no encontrado (simulación): {file_path.name}")
                    else:
                        # Eliminar realmente
                        if not file_path.exists():
                            error_msg = f"Archivo no encontrado: {file_path.name}"
                            results['errors'].append(error_msg)
                            self.cleanup_stats['errors'] += 1
                            continue

                        # Eliminar archivo
                        file_path.unlink()

                        # Registrar éxito
                        results['files_deleted'] += 1
                        results['space_freed'] += file_size
                        results['deleted_files'].append({
                            'path': str(file_path),
                            'type': file_info['type'],
                            'size': file_size,
                            'base_name': file_info['base_name'],
                            'simulated': False
                        })

                        self.cleanup_stats['files_deleted'] += 1
                        self.cleanup_stats['space_freed'] += file_size

                        self.logger.info(f"Eliminado: {file_path.name} ({file_info['type']})")

                except Exception as e:
                    error_msg = f"Error eliminando {file_path.name}: {str(e)}"
                    results['errors'].append(error_msg)
                    self.cleanup_stats['errors'] += 1
                    self.logger.error(error_msg)

            # Verificar éxito general
            self.cleanup_stats['live_photos_processed'] = len(files_to_delete)
            results['success'] = len(results['errors']) == 0

            operation_type = "Simulación" if dry_run else "Limpieza"
            try:
                from ui.helpers import format_size
                freed = format_size(results['space_freed'])
            except Exception:
                freed = f"{results['space_freed']/(1024*1024):.2f} MB"

            self.logger.info(f"{operation_type} completada: {results['files_deleted']} archivos eliminados, "
                           f"{freed} liberados, {len(results['errors'])} errores")

        except Exception as e:
            error_msg = f"Error durante limpieza: {str(e)}"
            results['errors'].append(error_msg)
            results['success'] = False
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

