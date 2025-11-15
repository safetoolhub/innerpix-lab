"""
Renombrador de nombres de archivos multimedia - VERSIÓN FINAL
Con logs detallados y resolución inteligente de conflictos
"""
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger, log_section_header_relevant, log_section_footer_relevant, log_section_header_discrete, log_section_footer_discrete
from utils.settings_manager import settings_manager
from services.result_types import RenameResult, RenameAnalysisResult
from services.base_service import BaseService, ProgressCallback
from utils.date_utils import (
    get_date_from_file,
    get_all_file_dates,
    format_renamed_name,
    is_renamed_filename,
    parse_renamed_name
)
from utils.file_utils import (
    launch_backup_creation,
    find_next_available_name,
    validate_file_exists,
)
from utils.decorators import deprecated
from services.metadata_cache import FileMetadataCache

class FileRenamer(BaseService):
    """
    Renombrador de nombres de archivos multimedia
    """
    def __init__(self):
        super().__init__("FileRenamer")
    
    # ========================================================================
    # MÉTODOS UNIFICADOS (Nomenclatura estándar desde Nov 2025)
    # ========================================================================
    
    def analyze(
        self,
        directory: Path,
        progress_callback: Optional[ProgressCallback] = None,
        metadata_cache: Optional[FileMetadataCache] = None
    ) -> RenameAnalysisResult:
        """
        Analiza un directorio para renombrado.
        
        Este es el método estándar de análisis.
        
        Args:
            directory: Directorio a analizar
            progress_callback: Función callback(current, total, message) para
                             reportar progreso
            metadata_cache: Caché opcional de metadatos para reutilizar fechas EXIF
            
        Returns:
            RenameAnalysisResult con análisis detallado
        
        Raises:
            FileNotFoundError: Si directory no existe
        """
        log_section_header_discrete(self.logger, f"ANALIZANDO DIRECTORIO PARA RENOMBRADO: {directory}")

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
            
            # Intentar obtener fecha de la caché primero
            file_date = None
            if metadata_cache:
                file_date = metadata_cache.get_exif_date(file_path)
            
            # Si no está en caché, extraer y cachear
            if not file_date:
                file_date = get_date_from_file(file_path)
                
                # Cachear la fecha si se obtuvo y hay caché disponible
                if file_date and metadata_cache:
                    # Obtener todas las fechas para cachear el máximo de info
                    all_dates = get_all_file_dates(file_path)
                    metadata_cache.set_exif_dates(
                        file_path,
                        exif_date=all_dates.get('exif_date'),
                        exif_date_original=all_dates.get('exif_date_original')
                    )
            
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
        # OPTIMIZACIÓN: Reducir frecuencia de callbacks (de 10 a 50 archivos)
        # Menor overhead de comunicación Qt sin perder responsividad
        progress_interval = 50
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file, f): f for f in all_files}
            
            for future in as_completed(futures):
                processed += 1
                
                if processed % progress_interval == 0:
                    # Si el callback retorna False, detener procesamiento
                    if not self._report_progress(progress_callback, processed, total_files, "Analizando nombres de archivos"):
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                
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

        self._report_progress(progress_callback, total_files, total_files, "Analizando nombres de archivos")

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

        log_section_footer_discrete(self.logger, f"Análisis completado: {need_renaming} archivos para renombrar")
        
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
    
    def execute(
        self,
        renaming_plan: List[Dict],
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[ProgressCallback] = None
    ) -> RenameResult:
        """
        Ejecuta el renombrado según el plan.
        
        Si el destino existe, busca siguiente sufijo disponible.
        
        Args:
            renaming_plan: Plan de renombrado del análisis
            create_backup: Si crear backup antes de proceder
            dry_run: Si True, simula la operación sin renombrar archivos
            progress_callback: Callback para reportar progreso
            
        Returns:
            RenameResult con resultados de la operación
        """
        if not renaming_plan:
            return RenameResult(
                success=True,
                files_renamed=0,
                message='No hay archivos para renombrar',
                dry_run=dry_run
            )

        mode_label = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(
            self.logger,
            "INICIANDO RENOMBRADO DE ARCHIVOS",
            mode=mode_label
        )
        self.logger.info(f"*** Archivos a renombrar: {len(renaming_plan)}")

        results = RenameResult(success=True, dry_run=dry_run)

        try:
            # Crear backup usando método centralizado
            if create_backup and renaming_plan and not dry_run:
                self._report_progress(progress_callback, 0, len(renaming_plan), "Creando backup...")
                
                try:
                    from services.base_service import BackupCreationError
                    backup_path = self._create_backup_for_operation(
                        renaming_plan,
                        'renaming',
                        progress_callback
                    )
                    if backup_path:
                        results.backup_path = str(backup_path)
                except BackupCreationError as e:
                    error_msg = f"Error creando backup: {e}"
                    self.logger.error(error_msg)
                    results.add_error(error_msg)
                    results.message = error_msg
                    return results

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
                        # Preservar sufijos no estándar del nombre original
                        # (sufijos que no sean de 3 dígitos generados por este programa)
                        original_stem = original_path.stem
                        original_parts = original_stem.split('_')
                        
                        # Detectar si el original tiene un sufijo numérico que no sea de 3 dígitos
                        preserved_suffix = ""
                        if len(original_parts) > 0 and original_parts[-1].isdigit() and len(original_parts[-1]) != 3:
                            preserved_suffix = f"_{original_parts[-1]}"
                        
                        base_name = Path(new_name).stem
                        extension = Path(new_name).suffix

                        # Añadir el sufijo preservado al nombre base antes de buscar secuencia
                        base_name_with_preserved = base_name + preserved_suffix

                        new_name, sequence = find_next_available_name(
                            original_path.parent,
                            base_name_with_preserved,
                            extension
                        )

                        new_path = original_path.parent / new_name
                        conflict_label = f"{mode_label} " if dry_run else ""
                        self.logger.info(
                            f"{conflict_label}⚠️  Conflicto resuelto: {original_path.name} -> "
                            f"{new_name} (secuencia {sequence})"
                        )
                        results.conflicts_resolved += 1

                    # Solo renombrar si no es simulación
                    if not dry_run:
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

                    progress_label = "Simulando renombrado" if dry_run else "Renombrando archivos"
                    # Si el callback retorna False, detener procesamiento
                    if not self._report_progress(progress_callback, files_processed, total_files,
                                       f"{progress_label}... {files_processed}/{total_files}"):
                        break

                    action_verb = "Se renombraría" if dry_run else "✓ Renombrado"
                    self.logger.info(f"{action_verb}: {original_path} → {new_path}")

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

            completion_label = "RENOMBRADO DE ARCHIVOS COMPLETADO"
            result_verb = "se renombrarían" if dry_run else "renombrados"
            conflicts_verb = "se resolverían" if dry_run else "resueltos"
            
            summary = f"{completion_label}\nResultado: {results.files_renamed} archivos {result_verb}, {results.conflicts_resolved} conflictos {conflicts_verb}"
            log_section_footer_relevant(self.logger, summary)
            
            # Construir mensaje para UI
            if dry_run:
                results.message = f"Simulación completada: {results.files_renamed} archivos se renombrarían"
            else:
                results.message = f"Renombrados {results.files_renamed} archivos"
                if results.conflicts_resolved > 0:
                    results.message += f", resueltos {results.conflicts_resolved} conflictos"
                if results.backup_path:
                    results.message += f"\n\nBackup creado en:\n{results.backup_path}"
            
            if results.has_errors:
                self.logger.info(f"*** Errores encontrados durante el renombrado:")
                for error in results.errors:
                    self.logger.error(f"  ✗ {error}")
                results.message += f"\n\nAdvertencia: {len(results.errors)} errores encontrados"

        except Exception as e:
            self.logger.error(f"Error crítico en renombrado: {str(e)}")
            results.success = False
            results.add_error(f"Error crítico: {str(e)}")
            results.message = f"Error crítico: {str(e)}"

        return results
    
    def rename_files(self, directory: Path, progress_callback: Optional[ProgressCallback] = None):
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

            self._report_progress(progress_callback, renamed_files, total_files, f"Renombrando archivo {renamed_files} de {total_files}")

        self._report_progress(progress_callback, total_files, total_files, "Renombrado completado")
