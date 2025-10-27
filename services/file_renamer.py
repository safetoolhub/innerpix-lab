"""
Renombrador de nombres de archivos multimedia - VERSIÓN FINAL
Con logs detallados y resolución inteligente de conflictos
"""
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Callable
from collections import defaultdict, Counter

import config
from utils.logger import get_logger
from utils.date_utils import (
    get_file_date,
    format_renamed_name,
    is_renamed_filename,
    parse_renamed_name
)
from utils.file_utils import (
    launch_backup_creation,
    find_next_available_name,
    validate_file_exists,
)

class FileRenamer:
    """
    Renombrador de nombres de archivos multimedia
    """
    def __init__(self):
        self.logger = get_logger("FileRenamer")
        self.backup_dir = None

    def analyze_directory(
        self,
        directory: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict:
        """
        Analiza un directorio para renombrado

        Args:
            directory: Directorio a analizar
            progress_callback: Función callback(current, total, message) para
                             reportar progreso

        Returns:
            Diccionario con análisis detallado
        """
        self.logger.info(f"Analizando directorio para renombrado: {directory}")

        results = {
            'total_files': 0,
            'already_renamed': 0,
            'need_renaming': 0,
            'cannot_process': 0,
            'conflicts': 0,
            'files_by_year': Counter(),
            'renaming_plan': [],
            'issues': []
        }

        all_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file() and config.config.is_supported_file(file_path.name):
                all_files.append(file_path)

        results['total_files'] = len(all_files)
        total_files = len(all_files)

        renaming_map = {}
        processed = 0

        for file_path in all_files:
            processed += 1

            if progress_callback and processed % 10 == 0:
                progress_callback(processed, total_files, "Analizando nombres de archivos")

            if is_renamed_filename(file_path.name):
                results['already_renamed'] += 1
                continue

            file_date = get_file_date(file_path)
            if not file_date:
                results['cannot_process'] += 1
                results['issues'].append(f"No se pudo obtener fecha: {file_path.name}")
                continue

            file_type = config.config.get_file_type(file_path.name)
            if file_type == 'OTHER':
                results['cannot_process'] += 1
                results['issues'].append(f"Tipo de archivo no soportado: {file_path.name}")
                continue

            extension = file_path.suffix
            renamed_name = format_renamed_name(file_date, file_type, extension)

            if renamed_name not in renaming_map:
                renaming_map[renamed_name] = []

            renaming_map[renamed_name].append({
                'original_path': file_path,
                'date': file_date,
                'type': file_type,
                'extension': extension
            })

            results['files_by_year'][file_date.year] += 1

        if progress_callback:
            progress_callback(total_files, total_files, "Analizando nombres de archivos")

        for renamed_name, file_list in renaming_map.items():
            if len(file_list) == 1:
                file_info = file_list[0]
                results['renaming_plan'].append({
                    'original_path': file_info['original_path'],
                    'new_name': renamed_name,
                    'date': file_info['date'],
                    'has_conflict': False,
                    'sequence': None
                })
                results['need_renaming'] += 1
            else:
                results['conflicts'] += len(file_list) - 1

                file_list.sort(key=lambda x: x['original_path'].stat().st_mtime)

                for i, file_info in enumerate(file_list, 1):
                    sequenced_name = format_renamed_name(
                        file_info['date'],
                        file_info['type'],
                        file_info['extension'],
                        sequence=i
                    )

                    results['renaming_plan'].append({
                        'original_path': file_info['original_path'],
                        'new_name': sequenced_name,
                        'date': file_info['date'],
                        'has_conflict': True,
                        'sequence': i
                    })
                    results['need_renaming'] += 1

        self.logger.info(
            f"Análisis completado: {results['need_renaming']} archivos para renombrar"
        )
        return results

    def execute_renaming(
        self,
        renaming_plan: List[Dict],
        create_backup: bool = True,
        progress_callback=None
    ) -> Dict:
        """
        Ejecuta el renombrado según el plan. Si el destino existe, busca siguiente sufijo disponible.

        Args:
            renaming_plan: Plan de renombrado del análisis
            create_backup: Si crear backup antes de proceder

        Returns:
            Resultados de la operación
        """
        if not renaming_plan:
            return {
                'success': True,
                'files_renamed': 0,
                'errors': [],
                'message': 'No hay archivos para renombrar'
            }

        self.logger.info(f"Iniciando renombrado de {len(renaming_plan)} archivos")

        results = {
            'success': True,
            'files_renamed': 0,
            'errors': [],
            'renamed_files': [],
            'backup_path': None,
            'conflicts_resolved': 0
        }

        try:
            if create_backup and renaming_plan:
                first_file = renaming_plan[0]['original_path']
                directory = first_file.parent

                for item in renaming_plan[1:]:
                    try:
                        directory = Path(
                            os.path.commonpath([directory, item['original_path'].parent])
                        )
                    except ValueError:
                        break

                if progress_callback:
                    progress_callback(0, len(renaming_plan), "Creando backup...")

                backup_path = launch_backup_creation(
                    (item['original_path'] for item in renaming_plan),
                    directory,
                    backup_prefix='backup_renaming',
                    progress_callback=progress_callback,
                    metadata_name='renaming_metadata.txt'
                )
                results['backup_path'] = str(backup_path)
                self.backup_dir = backup_path

            total_files = len(renaming_plan)
            files_processed = 0
            for item in renaming_plan:
                original_path = item['original_path']
                new_name = item['new_name']
                new_path = original_path.parent / new_name

                try:
                    try:
                        validate_file_exists(original_path)
                    except FileNotFoundError:
                        error_msg = f"Archivo no encontrado: {original_path.name}"
                        self.logger.error(error_msg)
                        self.logger.error(f"  → Ruta completa: {original_path}")
                        results['errors'].append({
                            'file': str(original_path),
                            'error': error_msg,
                            'type': 'FileNotFoundError'
                        })
                        continue

                    if new_path.exists():
                        base_name = Path(new_name).stem
                        extension = Path(new_name).suffix

                        new_name, sequence = find_next_available_name(
                            original_path.parent,
                            base_name,
                            extension
                        )

                        new_path = original_path.parent / new_name
                        self.logger.info(
                            f"Conflicto resuelto: {original_path.name} -> "
                            f"{new_name} (secuencia {sequence})"
                        )
                        results['conflicts_resolved'] += 1

                    original_path.rename(new_path)

                    results['files_renamed'] += 1
                    files_processed += 1
                    date_obj = item.get('date') if isinstance(item, dict) else None
                    if date_obj is not None:
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = ''

                    results['renamed_files'].append({
                        'original': original_path.name,
                        'new_name': new_name,
                        'date': date_str,
                        'had_conflict': item.get('has_conflict', False) if isinstance(item, dict) else False
                    })

                    if progress_callback:
                        progress_callback(files_processed, total_files,
                                       f"Renombrando archivos... {files_processed}/{total_files}")

                    self.logger.info(f"Renombrado: {original_path.name} -> {new_name}")

                except Exception as e:
                    error_msg = f"Error renombrando {original_path.name}: {str(e)}"
                    self.logger.error(error_msg)
                    self.logger.error(f"  → Archivo origen: {original_path}")
                    self.logger.error(f"  → Destino intentado: {new_path}")
                    self.logger.error(f"  → Tipo de error: {type(e).__name__}")
                    self.logger.error(f"  → Detalle: {str(e)}")

                    results['errors'].append({
                        'file': str(original_path),
                        'error': str(e),
                        'type': type(e).__name__
                    })

            if results['errors']:
                results['success'] = len(results['errors']) < len(renaming_plan)

            self.logger.info(
                f"Renombrado completado: {results['files_renamed']} archivos renombrados, "
                f"{results['conflicts_resolved']} conflictos resueltos, "
                f"{len(results['errors'])} errores"
            )

            if results['errors']:
                self.logger.error("=" * 70)
                self.logger.error(f"RESUMEN DE ERRORES ({len(results['errors'])} archivos):")
                self.logger.error("=" * 70)
                for i, error in enumerate(results['errors'], 1):
                    self.logger.error(f"{i}. {Path(error['file']).name}")
                    self.logger.error(f"   {error.get('type', 'Error')}: {error['error']}")
                self.logger.error("=" * 70)

        except Exception as e:
            self.logger.error(f"Error crítico en renombrado: {str(e)}")
            results['success'] = False
            results['errors'].append({
                'file': 'GENERAL',
                'error': str(e),
                'type': type(e).__name__
            })

        return results

    def rename_files(self, directory: Path, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        Renombra los archivos en el directorio dado

        Args:
            directory: Directorio donde se renombrarán los archivos
            progress_callback: Función callback(current, total, message) para reportar progreso
        """
        self.logger.info(f"Renombrando archivos en: {directory}")

        all_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file() and config.config.is_supported_file(file_path.name):
                all_files.append(file_path)

        total_files = len(all_files)
        renamed_files = 0

        for file_path in all_files:
            renamed_files += 1

            if progress_callback:
                progress_callback(renamed_files, total_files, f"Renombrando archivo {renamed_files} de {total_files}")

        if progress_callback:
            progress_callback(total_files, total_files, "Renombrado completado")
