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
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger
from utils.callback_utils import safe_progress_callback
from utils.settings_manager import settings_manager
from services.result_types import RenameResult, RenameAnalysisResult
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
    ) -> RenameAnalysisResult:
        """
        Analiza un directorio para renombrado

        Args:
            directory: Directorio a analizar
            progress_callback: Función callback(current, total, message) para
                             reportar progreso

        Returns:
            RenameAnalysisResult con análisis detallado
        """
        self.logger.info(f"Analizando directorio para renombrado: {directory}")

        all_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file() and Config.is_supported_file(file_path.name):
                all_files.append(file_path)

        total_files = len(all_files)
        renaming_map = {}
        already_renamed = 0
        cannot_process = 0
        conflicts = 0
        files_by_year = Counter()
        renaming_plan = []
        issues = []
        
        # Obtener max_workers de la configuración
        max_workers = settings_manager.get_max_workers(Config.MAX_WORKERS)
        self.logger.debug(f"Usando {max_workers} workers para análisis paralelo")

        # Función para procesar un archivo
        def process_file(file_path):
            """Procesa un archivo y retorna su información de renombrado"""
            # Archivo ya renombrado
            if is_renamed_filename(file_path.name):
                return ('already_renamed', file_path, None)
            
            # Obtener fecha del archivo
            file_date = get_file_date(file_path)
            if not file_date:
                return ('no_date', file_path, f"No se pudo obtener fecha: {file_path.name}")
            
            # Verificar tipo de archivo
            file_type = Config.get_file_type(file_path.name)
            if file_type == 'OTHER':
                return ('unsupported', file_path, f"Tipo de archivo no soportado: {file_path.name}")
            
            extension = file_path.suffix
            renamed_name = format_renamed_name(file_date, file_type, extension)
            
            return ('rename', file_path, {
                'renamed_name': renamed_name,
                'original_path': file_path,
                'date': file_date,
                'type': file_type,
                'extension': extension
            })

        # Procesar archivos en paralelo
        processed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file, f): f for f in all_files}
            
            for future in as_completed(futures):
                processed += 1
                
                if processed % 10 == 0:
                    safe_progress_callback(progress_callback, processed, total_files, "Analizando nombres de archivos")
                
                status, file_path, data = future.result()
                
                if status == 'already_renamed':
                    already_renamed += 1
                elif status == 'no_date':
                    cannot_process += 1
                    issues.append(data)
                elif status == 'unsupported':
                    cannot_process += 1
                    issues.append(data)
                elif status == 'rename':
                    renamed_name = data['renamed_name']
                    if renamed_name not in renaming_map:
                        renaming_map[renamed_name] = []
                    renaming_map[renamed_name].append(data)
                    files_by_year[data['date'].year] += 1

        safe_progress_callback(progress_callback, total_files, total_files, "Analizando nombres de archivos")

        need_renaming = 0
        for renamed_name, file_list in renaming_map.items():
            if len(file_list) == 1:
                file_info = file_list[0]
                renaming_plan.append({
                    'original_path': file_info['original_path'],
                    'new_name': renamed_name,
                    'date': file_info['date'],
                    'has_conflict': False,
                    'sequence': None
                })
                need_renaming += 1
            else:
                conflicts += len(file_list) - 1

                file_list.sort(key=lambda x: x['original_path'].stat().st_mtime)

                for i, file_info in enumerate(file_list, 1):
                    sequenced_name = format_renamed_name(
                        file_info['date'],
                        file_info['type'],
                        file_info['extension'],
                        sequence=i
                    )

                    renaming_plan.append({
                        'original_path': file_info['original_path'],
                        'new_name': sequenced_name,
                        'date': file_info['date'],
                        'has_conflict': True,
                        'sequence': i
                    })
                    need_renaming += 1

        self.logger.info(
            f"Análisis completado: {need_renaming} archivos para renombrar"
        )
        
        return RenameAnalysisResult(
            success=True,
            total_files=total_files,
            already_renamed=already_renamed,
            need_renaming=need_renaming,
            cannot_process=cannot_process,
            conflicts=conflicts,
            files_by_year=dict(files_by_year),
            renaming_plan=renaming_plan,
            issues=issues
        )

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
            return RenameResult(
                success=True,
                files_renamed=0,
                message='No hay archivos para renombrar'
            )

        self.logger.info(f"Iniciando renombrado de {len(renaming_plan)} archivos")

        results = RenameResult(success=True)

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

                safe_progress_callback(progress_callback, 0, len(renaming_plan), "Creando backup...")

                backup_path = launch_backup_creation(
                    (item['original_path'] for item in renaming_plan),
                    directory,
                    backup_prefix='backup_renaming',
                    progress_callback=progress_callback,
                    metadata_name='renaming_metadata.txt'
                )
                results.backup_path = str(backup_path)
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
                        results.add_error(f"{original_path}: {error_msg}")
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
                        results.conflicts_resolved += 1

                    original_path.rename(new_path)

                    results.files_renamed += 1
                    files_processed += 1
                    date_obj = item.get('date') if isinstance(item, dict) else None
                    if date_obj is not None:
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = ''

                    results.renamed_files.append({
                        'original': original_path.name,
                        'new_name': new_name,
                        'date': date_str,
                        'had_conflict': item.get('has_conflict', False) if isinstance(item, dict) else False
                    })

                    safe_progress_callback(progress_callback, files_processed, total_files,
                                       f"Renombrando archivos... {files_processed}/{total_files}")

                    self.logger.info(f"Renombrado: {original_path.name} -> {new_name}")

                except Exception as e:
                    error_msg = f"Error renombrando {original_path.name}: {str(e)}"
                    self.logger.error(error_msg)
                    self.logger.error(f"  → Archivo origen: {original_path}")
                    self.logger.error(f"  → Destino intentado: {new_path}")
                    self.logger.error(f"  → Tipo de error: {type(e).__name__}")
                    self.logger.error(f"  → Detalle: {str(e)}")

                    results.add_error(f"{original_path.name}: {str(e)}")

            if results.has_errors:
                results.success = len(results.errors) < len(renaming_plan)

            self.logger.info(
                f"Renombrado completado: {results.files_renamed} archivos renombrados, "
                f"{results.conflicts_resolved} conflictos resueltos, "
                f"{len(results.errors)} errores"
            )

            if results.has_errors:
                self.logger.error("=" * 70)
                self.logger.error(f"RESUMEN DE ERRORES ({len(results.errors)} archivos):")
                self.logger.error("=" * 70)
                for i, error in enumerate(results.errors, 1):
                    self.logger.error(f"{i}. {error}")
                self.logger.error("=" * 70)

        except Exception as e:
            self.logger.error(f"Error crítico en renombrado: {str(e)}")
            results.success = False
            results.add_error(f"Error crítico: {str(e)}")

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
            if file_path.is_file() and Config.is_supported_file(file_path.name):
                all_files.append(file_path)

        total_files = len(all_files)
        renamed_files = 0

        for file_path in all_files:
            renamed_files += 1

            safe_progress_callback(progress_callback, renamed_files, total_files, f"Renombrando archivo {renamed_files} de {total_files}")

        safe_progress_callback(progress_callback, total_files, total_files, "Renombrado completado")
