"""
Organizador de Archivos
"""
import shutil
import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger, log_section_header_relevant, log_section_footer_relevant, log_section_header_discrete, log_section_footer_discrete
from utils.settings_manager import settings_manager
from utils.date_utils import parse_renamed_name, get_date_from_file
from utils.file_utils import is_whatsapp_file, detect_file_source
from services.result_types import OrganizationResult, OrganizationAnalysisResult
from services.base_service import BaseService, ProgressCallback
from utils.decorators import deprecated

class OrganizationType(Enum):
    """Tipos de organización disponibles"""
    # Organización temporal
    BY_MONTH = "by_month"
    BY_YEAR = "by_year"
    BY_YEAR_MONTH = "by_year_month"
    
    # Organización por tipo/fuente
    BY_TYPE = "by_type"
    BY_SOURCE = "by_source"
    
    # Organización simple
    TO_ROOT = "to_root"


@dataclass
class FileMove:
    """Representa un movimiento de archivo"""
    source_path: Path
    target_path: Path
    original_name: str
    new_name: str
    subdirectory: str
    file_type: str
    size: int
    has_conflict: bool = False
    sequence: Optional[int] = None
    target_folder: Optional[str] = None  # Carpeta destino (para organizaciones con carpetas: BY_MONTH, BY_YEAR, BY_YEAR_MONTH, BY_TYPE, BY_SOURCE)
    source: str = "Unknown"  # Fuente detectada (WhatsApp, iPhone, etc.)

    def __post_init__(self):
        """Validaciones"""
        if not self.source_path.exists():
            raise ValueError(f"Archivo origen no existe: {self.source_path}")

    @property
    def will_rename(self) -> bool:
        """True si el archivo será renombrado"""
        return self.original_name != self.new_name


class FileOrganizer(BaseService):
    """Organizador de archivos - Mueve archivos multimedia de subdirectorios al directorio raíz"""

    def __init__(self):
        super().__init__("FileOrganizer")

    def analyze(self, 
                root_directory: Path, 
                organization_type: OrganizationType, 
                progress_callback: Optional[ProgressCallback] = None,
                group_by_source: bool = False,
                group_by_type: bool = False,
                date_grouping_type: Optional[str] = None) -> OrganizationAnalysisResult:
        """
        Analiza el directorio y genera un plan de organización.
        
        Args:
            root_directory: Directorio a analizar
            organization_type: Estrategia principal de organización
            progress_callback: Callback para reportar progreso
            group_by_source: Si True, agrupa secundariamente por fuente (WhatsApp, etc.)
            group_by_type: Si True, agrupa secundariamente por tipo (Foto/Video)
            date_grouping_type: Tipo de agrupación por fecha ('month', 'year', 'year_month') o None
        
        Raises:
            ValueError: Si root_directory no existe o no es un directorio válido
        """
        log_section_header_discrete(self.logger, f"ANALIZANDO ESTRUCTURA DE DIRECTORIOS PARA ORGANIZACIÓN ({organization_type.value}): {root_directory}")

        subdirectories = {}
        root_files = []
        total_files_to_move = 0
        total_size_to_move = 0
        potential_conflicts = 0
        files_by_type = Counter()
        move_plan = []
        folders_to_create = []

        # Obtener max_workers de la configuración
        max_workers = settings_manager.get_max_workers(Config.MAX_WORKERS)
        self.logger.debug(f"Usando {max_workers} workers para análisis paralelo")

        # Contar total de archivos para progress
        all_files_for_count = list(root_directory.rglob("*"))
        total_files = sum(1 for f in all_files_for_count if f.is_file() and Config.is_supported_file(f.name))
        processed_files = 0

        # Función para procesar información de archivo
        def get_file_info(file_path):
            """Obtiene información de un archivo"""
            try:
                file_size = file_path.stat().st_size
                file_type = Config.get_file_type(file_path.name)
                return {
                    'path': file_path,
                    'name': file_path.name,
                    'size': file_size,
                    'type': file_type
                }
            except Exception as e:
                self.logger.warning(f"Error al obtener info de {file_path}: {e}")
                return None

        # Obtener archivos en raíz
        root_file_names = set()
        root_file_info = []
        
        root_files_list = [item for item in root_directory.iterdir() 
                          if item.is_file() and Config.is_supported_file(item.name)]
        
        # Procesar archivos de raíz en paralelo si es necesario
        if organization_type in (OrganizationType.BY_MONTH, OrganizationType.BY_YEAR, OrganizationType.BY_YEAR_MONTH, OrganizationType.BY_TYPE, OrganizationType.BY_SOURCE) and root_files_list:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(get_file_info, f): f for f in root_files_list}
                for future in as_completed(futures):
                    file_path = futures[future]
                    root_file_names.add(file_path.name)
                    
                    info = future.result()
                    if info:
                        root_file_info.append(info)
                    
                    processed_files += 1
                    # Si el callback retorna False, cancelar análisis
                    if not self._report_progress(progress_callback, processed_files, total_files, "Analizando estructura de organización"):
                        executor.shutdown(wait=False, cancel_futures=True)
                        # Retornar resultado vacío al cancelar
                        return OrganizationAnalysisResult(
                            success=False,
                            total_files=0,
                            root_directory=str(root_directory),
                            organization_type=organization_type.value,
                            subdirectories={},
                            root_files=[],
                                total_files_to_move=0,
                                total_size_to_move=0,
                                potential_conflicts=0,
                                files_by_type={},
                                move_plan=[],
                                folders_to_create=[]
                            )
        else:
            # Solo necesitamos los nombres para TO_ROOT
            root_file_names = {item.name for item in root_files_list}
            processed_files += len(root_files_list)
            # Si el callback retorna False, cancelar análisis
            if not self._report_progress(progress_callback, processed_files, total_files, "Analizando estructura de organización"):
                return OrganizationAnalysisResult(
                    success=False,
                    total_files=0,
                    root_directory=str(root_directory),
                    organization_type=organization_type.value,
                    subdirectories={},
                    root_files=[],
                    total_files_to_move=0,
                    total_size_to_move=0,
                    potential_conflicts=0,
                    files_by_type={},
                    move_plan=[],
                        folders_to_create=[]
                    )

        # Procesar subdirectorios - USAR RECURSIÓN COMPLETA
        # Agrupar archivos por subdirectorio relativo a root
        all_files_in_subdirs = []
        
        # Encontrar todos los archivos en subdirectorios (cualquier nivel de anidación)
        for file_path in root_directory.rglob("*"):
            # Saltar si es directorio, archivo no soportado, o está en la raíz
            if file_path.is_dir():
                continue
            if not Config.is_supported_file(file_path.name):
                continue
            if file_path.parent == root_directory:
                continue  # Archivos en raíz ya fueron procesados
            
            all_files_in_subdirs.append(file_path)
        
        # Procesar archivos en subdirectorios en paralelo
        if all_files_in_subdirs:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(get_file_info, f): f for f in all_files_in_subdirs}
                
                for future in as_completed(futures):
                    file_path = futures[future]
                    info = future.result()
                    
                    if info:
                        # Obtener ruta relativa del subdirectorio respecto a root
                        # Usar el path relativo completo para mostrar la estructura anidada
                        relative_path = file_path.relative_to(root_directory)
                        subdir_name = str(relative_path.parent)
                        
                        if subdir_name not in subdirectories:
                            subdirectories[subdir_name] = {
                                'path': str(file_path.parent),
                                'file_count': 0,
                                'total_size': 0,
                                'files': []
                            }
                        
                        subdirectories[subdir_name]['files'].append(info)
                        subdirectories[subdir_name]['file_count'] += 1
                        subdirectories[subdir_name]['total_size'] += info['size']
                        
                        files_by_type[info['type']] += 1
                        total_files_to_move += 1
                        total_size_to_move += info['size']
                    
                    processed_files += 1
                    # Si el callback retorna False, cancelar análisis
                    if not self._report_progress(progress_callback, processed_files, total_files, "Analizando estructura de organización"):
                        executor.shutdown(wait=False, cancel_futures=True)
                        # Retornar resultado vacío al cancelar
                        return OrganizationAnalysisResult(
                            success=False,
                            total_files=0,
                            root_directory=str(root_directory),
                            organization_type=organization_type.value,
                            subdirectories={},
                            root_files=[],
                            total_files_to_move=0,
                            total_size_to_move=0,
                            potential_conflicts=0,
                            files_by_type={},
                            move_plan=[],
                            folders_to_create=[]
                        )

        # Para by_month, by_year, by_year_month, by_type, by_source, agregar archivos de raíz
        if organization_type in (OrganizationType.BY_MONTH, OrganizationType.BY_YEAR, OrganizationType.BY_YEAR_MONTH, OrganizationType.BY_TYPE, OrganizationType.BY_SOURCE):
            if root_file_info:
                root_files = root_file_info
                total_files_to_move += len(root_file_info)
                total_size_to_move += sum(f['size'] for f in root_file_info)
                
                for file_info in root_file_info:
                    files_by_type[file_info['type']] += 1

        # Generar plan de movimiento si hay archivos
        if subdirectories or root_files:
            move_plan = self._generate_move_plan(
                subdirectories,
                root_files,
                root_directory,
                root_file_names,
                organization_type,
                progress_callback, # Pass progress_callback
                group_by_source,
                group_by_type,
                date_grouping_type
            )
            potential_conflicts = sum(1 for move in move_plan if move.has_conflict)
            folders_to_create = sorted(set(move.target_folder for move in move_plan if move.target_folder))

        log_section_footer_discrete(self.logger, f"Análisis completado: {total_files_to_move} archivos para mover desde {len(subdirectories)} subdirectorios + {len(root_files)} en raíz")

        # Re-calculate total_files_to_move and total_size_to_move based on the final move_plan
        final_total_files_to_move = len(move_plan)
        final_total_size_to_move = sum(m.size for m in move_plan)
        
        # Re-aggregate files_by_type from the move_plan
        final_files_by_type = Counter()
        for move in move_plan:
            final_files_by_type[move.file_type] += 1

        # Re-aggregate subdirectories (files_by_subdir) from the move_plan
        files_by_subdir = defaultdict(self._get_default_subdir_info)
        for move in move_plan:
            subdir_key = move.subdirectory if move.subdirectory != '<root>' else 'root_files'
            if subdir_key not in files_by_subdir:
                # Attempt to get the original path for the subdirectory if it exists
                original_subdir_path = (root_directory / move.subdirectory).resolve() if move.subdirectory != '<root>' else root_directory.resolve()
                files_by_subdir[subdir_key]['path'] = str(original_subdir_path)
            
            files_by_subdir[subdir_key]['file_count'] += 1
            files_by_subdir[subdir_key]['total_size'] += move.size
            files_by_subdir[subdir_key]['files'].append({
                'path': move.source_path,
                'name': move.original_name,
                'size': move.size,
                'type': move.file_type
            })

        return OrganizationAnalysisResult(
            success=True,
            total_files=final_total_files_to_move,
            root_directory=str(root_directory),
            organization_type=organization_type.value,
            subdirectories=files_by_subdir,
            root_files=root_files, # Keep original root_files info for display
            total_files_to_move=final_total_files_to_move,
            total_size_to_move=final_total_size_to_move,
            potential_conflicts=potential_conflicts,
            files_by_type=dict(final_files_by_type),
            move_plan=move_plan,
            folders_to_create=folders_to_create,
            group_by_source=group_by_source,
            group_by_type=group_by_type,
            date_grouping_type=date_grouping_type
        )

    @staticmethod
    def _get_default_subdir_info():
        return {'path': '', 'file_count': 0, 'total_size': 0, 'files': []}

    def execute(self, move_plan: List[FileMove], create_backup: bool = True, cleanup_empty_dirs: bool = True, dry_run: bool = False, progress_callback: Optional[ProgressCallback] = None) -> OrganizationResult:
        """
        Ejecuta la organización según el plan con resolución dinámica de conflictos.

        Args:
            move_plan: Lista de FileMove con las operaciones a realizar
            create_backup: Si crear backup antes de mover archivos
            cleanup_empty_dirs: Si limpiar directorios vacíos al final
            dry_run: Si ejecutar en modo simulación (sin cambios reales)
            progress_callback: Función opcional (current, total, message) para reportar progreso

        Returns:
            OrganizationResult con el resultado de la operación
        """
        if not move_plan:
            return OrganizationResult(
                success=True,
                files_moved=0,
                empty_directories_removed=0,
                message='No hay archivos para mover'
            )

        mode_label = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(
            self.logger,
            "INICIANDO ORGANIZACIÓN DE ARCHIVOS",
            mode=mode_label
        )
        self.logger.info(f"*** Archivos a mover: {len(move_plan)}")

        results = OrganizationResult(success=True, dry_run=dry_run)

        try:
            # Determinar el directorio raíz correctamente
            # Buscar en los target_path para encontrar el verdadero root
            if move_plan[0].target_folder:
                # Contar niveles en la carpeta destino (puede ser jerárquica como "2025/11")
                folder_depth = len(Path(move_plan[0].target_folder).parts)
                # Subir tantos niveles como profundidad tenga la carpeta
                root_directory = move_plan[0].target_path.parent
                for _ in range(folder_depth):
                    root_directory = root_directory.parent
            else:
                # Si va directo a raíz, el root es parent
                root_directory = move_plan[0].target_path.parent
            
            # Verificar con otro archivo del plan para asegurarnos
            for move in move_plan:
                if not move.target_folder:
                    # Este archivo va directo al root, su parent ES el root
                    root_directory = move.target_path.parent
                    break

            # Crear carpetas necesarias (para organizaciones que usan carpetas) - solo si no es simulación
            folders_to_create = set(move.target_folder for move in move_plan if move.target_folder)
            if not dry_run:
                for folder_name in folders_to_create:
                    folder_path = root_directory / folder_name
                    if not folder_path.exists():
                        folder_path.mkdir(parents=True, exist_ok=True)
                        results.folders_created.append(str(folder_path))
                        self.logger.info(f"Carpeta creada: {folder_name}")
            else:
                # En simulación, solo reportar qué carpetas se crearían
                for folder_name in folders_to_create:
                    folder_path = root_directory / folder_name
                    if not folder_path.exists():
                        results.folders_created.append(str(folder_path))
                        self.logger.info(f"[SIMULACIÓN] Se crearía carpeta: {folder_name}")

            # Crear backup usando método centralizado (solo si no es simulación)
            if create_backup and move_plan and not dry_run:
                self._report_progress(progress_callback, 0, len(move_plan), "Creando backup antes de organizar...")
                
                try:
                    from services.base_service import BackupCreationError
                    backup_path = self._create_backup_for_operation(
                        move_plan,
                        'organization',
                        progress_callback
                    )
                    if backup_path:
                        results.backup_path = str(backup_path)
                except BackupCreationError as e:
                    error_msg = f"Error creando backup: {e}"
                    self.logger.error(error_msg)
                    results.add_error(error_msg)
                    return results

            # Track de nombres ya usados durante la ejecución (por carpeta)
            used_names_by_folder = defaultdict(set)
            
            # Cargar nombres existentes por carpeta
            folders_to_check = set([root_directory])
            for move in move_plan:
                if move.target_folder:
                    folders_to_check.add(root_directory / move.target_folder)
            
            for folder in folders_to_check:
                if folder.exists():
                    for item in folder.iterdir():
                        if item.is_file():
                            used_names_by_folder[str(folder)].add(item.name)

            # Ejecutar movimientos con resolución dinámica de conflictos
            files_processed = 0
            total_files = len(move_plan)

            self._report_progress(progress_callback, 0, total_files, "Iniciando organización de directorios...")

            for move in move_plan:
                try:
                    # Verificar que el archivo origen existe y es accesible
                    try:
                        if not move.source_path.exists():
                            self.logger.error(f"Archivo no existe: {move.source_path}")
                            results['errors'].append({
                                'file': str(move.source_path),
                                'error': 'Archivo no encontrado'
                            })
                            continue

                        # Verificar que podemos acceder al archivo
                        move.source_path.stat()
                    except (FileNotFoundError, PermissionError, OSError) as e:
                        self.logger.error(f"Error accediendo al archivo {move.source_path}: {str(e)}")
                        results['errors'].append({
                            'file': str(move.source_path),
                            'error': f'Error de acceso: {str(e)}'
                        })
                        continue

                    # Determinar carpeta destino
                    if move.target_folder:
                        target_folder = root_directory / move.target_folder
                        folder_key = str(target_folder)
                    else:
                        target_folder = root_directory
                        folder_key = str(root_directory)

                    # Verificar conflicto en tiempo real
                    target_name = move.new_name
                    target_path = target_folder / target_name

                    # Si el destino ya existe o ya fue usado en esta ejecución, buscar nuevo nombre
                    if target_path.exists() or target_name in used_names_by_folder[folder_key]:
                        move.has_conflict = True
                        self.logger.debug(f"Conflicto detectado para {target_name}, buscando nombre alternativo")

                        # Extraer partes del nombre
                        base_name = Path(target_name).stem
                        extension = Path(target_name).suffix

                        # Si ya tiene sufijo numérico, extraerlo
                        parsed = parse_renamed_name(target_name)
                        if parsed and parsed.get('sequence'):
                            parts = base_name.split('_')
                            if len(parts) >= 4 and len(parts[-1]) == 3 and parts[-1].isdigit():
                                base_name_without_suffix = '_'.join(parts[:-1])
                                start_sequence = int(parts[-1])
                            else:
                                base_name_without_suffix = base_name
                                start_sequence = 0
                        else:
                            base_name_without_suffix = base_name
                            start_sequence = 0

                        # Buscar siguiente secuencia disponible
                        sequence = start_sequence + 1 if start_sequence > 0 else 1
                        while True:
                            new_name = f"{base_name_without_suffix}_{sequence:03d}{extension}"
                            new_target_path = target_folder / new_name

                            if not new_target_path.exists() and new_name not in used_names_by_folder[folder_key]:
                                target_name = new_name
                                target_path = new_target_path
                                move.new_name = new_name
                                move.target_path = new_target_path
                                move.sequence = sequence
                                break

                            sequence += 1

                            # Protección contra bucle infinito
                            if sequence > 9999:
                                raise Exception(f"No se pudo encontrar nombre único después de 9999 intentos")

                    # Asegurar que el directorio destino existe (solo si no es simulación)
                    if not dry_run:
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Determinar si mostrar análisis detallado de fechas (solo para organización BY_MONTH)
                    # BY_MONTH usa carpetas con formato YYYY_MM (ej: 2023_07)
                    import re
                    is_by_month = move.target_folder and re.match(r'^\d{4}_\d{2}$', move.target_folder)
                    
                    # Obtener fecha del archivo (verbose solo para BY_MONTH)
                    try:
                        file_date = get_date_from_file(move.source_path, verbose=is_by_month)
                        date_str = file_date.strftime('%Y-%m-%d %H:%M:%S') if file_date else 'fecha desconocida'
                    except Exception as e:
                        self.logger.warning(f"Error obteniendo fecha de {move.source_path.name}: {e}")
                        date_str = 'fecha desconocida'

                    if dry_run:
                        # Solo simular: no mover archivos
                        # Añadir a la lista de nombres usados para simular conflictos correctamente
                        used_names_by_folder[folder_key].add(target_name)
                        results.files_moved += 1
                        files_processed += 1
                        results.moved_files.append(str(target_path))
                        
                        # Mostrar log de simulación según si hubo conflicto
                        if move.has_conflict or move.sequence:
                            self.logger.info(f"[SIMULACIÓN] ⚠️  Se resolvería conflicto: {move.source_path} → {target_path} (secuencia {move.sequence}, {date_str})")
                        else:
                            self.logger.info(f"[SIMULACIÓN] Se movería: {move.source_path} → {target_path} ({date_str})")
                    else:
                        # Mover archivo realmente
                        try:
                            # Verificar una última vez que el archivo existe y es accesible
                            if move.source_path.exists() and move.source_path.is_file():
                                move.source_path.rename(target_path)
                                # Añadir a la lista de nombres usados
                                used_names_by_folder[folder_key].add(target_name)
                            else:
                                raise FileNotFoundError(f"Archivo no encontrado o no accesible: {move.source_path}")
                        except (FileNotFoundError, PermissionError, OSError) as e:
                            raise Exception(f"Error moviendo archivo: {str(e)}")

                        results.files_moved += 1
                        files_processed += 1
                        results.moved_files.append(str(target_path))
                        
                        # Mostrar log apropiado según si hubo conflicto
                        if move.has_conflict or move.sequence:
                            self.logger.info(f"⚠️  Conflicto resuelto: {move.source_path} → {target_path} (secuencia {move.sequence}, {date_str})")
                        else:
                            self.logger.info(f"✓ Movido: {move.source_path} → {target_path} ({date_str})")

                    if not self._report_progress(progress_callback, files_processed, total_files,
                                       f"{'Simulando' if dry_run else 'Organizando'} directorios... {files_processed}/{total_files}"):
                        break

                except Exception as e:
                    self.logger.error(f"Error moviendo {move.source_path.name}: {str(e)}")
                    results.add_error(f"{move.source_path.name}: {str(e)}")

            # Limpiar directorios vacíos - solo si no es simulación
            if cleanup_empty_dirs and not dry_run:
                try:
                    from utils.file_utils import cleanup_empty_directories as _cleanup
                    removed = _cleanup(root_directory)
                    results.empty_directories_removed = removed
                    if removed > 0:
                        self.logger.info(f"Directorios vacíos eliminados: {removed}")
                except Exception as e:
                    self.logger.error(f"Error limpiando directorios: {e}")
            elif cleanup_empty_dirs and dry_run:
                self.logger.info("[SIMULACIÓN] Se limpiarían directorios vacíos al finalizar")

            # Determinar éxito general
            if results.has_errors:
                results.success = len(results.errors) < len(move_plan)

            completion_label = "ORGANIZACIÓN DE ARCHIVOS COMPLETADA"
            result_verb = "se moverían" if dry_run else "movidos"
            
            summary = f"{completion_label}\nResultado: {results.files_moved} archivos {result_verb}"
            log_section_footer_relevant(self.logger, summary)
            
            if dry_run:
                results.message = f"Simulación completada: {results.files_moved} archivos se moverían"
            else:
                results.message = f"Organizados {results.files_moved} archivos"
                if results.backup_path:
                    results.message += f"\n\nBackup creado en:\n{results.backup_path}"
            
            if results.errors:
                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                self.logger.info(f"*** {error_prefix}Errores encontrados durante la {'simulación' if dry_run else 'organización'}:")
                for error in results.errors:
                    self.logger.error(f"  ✗ {error}")
                results.message += f"\n\nAdvertencia: {len(results.errors)} errores encontrados"

        except Exception as e:
            self.logger.error(f"Error crítico en organización: {str(e)}")
            results.add_error(f"Error crítico: {str(e)}")
            results.message = f"Error crítico: {str(e)}"

        return results

    def _generate_move_plan(self, 
                          subdirectories: Dict, 
                          root_files: List[Dict], 
                          root_directory: Path, 
                          existing_file_names: Set[str], # Keep this parameter for TO_ROOT
                          organization_type: OrganizationType,
                          progress_callback: Optional[ProgressCallback] = None, # Added progress_callback
                          group_by_source: bool = False,
                          group_by_type: bool = False,
                          date_grouping_type: Optional[str] = None) -> List[FileMove]:
        """
        Genera plan de movimiento con resolución de conflictos según el tipo de organización
        
        Args:
            subdirectories: Diccionario de subdirectorios con sus archivos
            root_files: Lista de archivos en la raíz (para organizaciones temporales y por tipo)
            root_directory: Path del directorio raíz
            existing_file_names: Set de nombres de archivos existentes en raíz (solo para TO_ROOT)
            organization_type: Tipo de organización
            progress_callback: Función opcional (current, total, message) para reportar progreso
            group_by_source: Agrupar por fuente dentro de la carpeta principal
            group_by_type: Agrupar por tipo dentro de la carpeta principal
            date_grouping_type: Tipo de agrupación por fecha ('month', 'year', 'year_month') o None
        """
        if organization_type == OrganizationType.TO_ROOT:
            return self._generate_move_plan_to_root(subdirectories, root_directory, existing_file_names)
        elif organization_type == OrganizationType.BY_MONTH:
            return self._generate_move_plan_by_month(subdirectories, root_files, root_directory, group_by_source, group_by_type)
        elif organization_type == OrganizationType.BY_YEAR:
            return self._generate_move_plan_by_year(subdirectories, root_files, root_directory, group_by_source, group_by_type)
        elif organization_type == OrganizationType.BY_YEAR_MONTH:
            return self._generate_move_plan_by_year_month(subdirectories, root_files, root_directory, group_by_source, group_by_type)
        elif organization_type == OrganizationType.BY_TYPE:
            return self._generate_move_plan_by_type(subdirectories, root_files, root_directory, group_by_source, date_grouping_type)
        elif organization_type == OrganizationType.BY_SOURCE:
            return self._generate_move_plan_by_source(subdirectories, root_files, root_directory, date_grouping_type)
        else:
            raise ValueError(f"Tipo de organización no soportado: {organization_type}")

    def _generate_move_plan_to_root(self, subdirectories: Dict, root_directory: Path, existing_files: Set[str]) -> List[FileMove]:
        """Genera plan de movimiento a directorio raíz"""
        move_plan = []
        name_conflicts = defaultdict(list)

        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = file_info['path']
                file_name = file_info['name']

                if Path(file_path).exists():
                    has_conflict = file_name in existing_files

                    move = FileMove(
                        source_path=Path(file_path),
                        target_path=root_directory / file_name,
                        original_name=file_name,
                        new_name=file_name,
                        subdirectory=subdir_name,
                        file_type=file_info['type'],
                        size=file_info['size'],
                        has_conflict=has_conflict,
                        source=detect_file_source(file_name, Path(file_path))
                    )

                    name_conflicts[file_name].append(move)
                else:
                    self.logger.warning(f"Saltando archivo que no existe: {file_path}")

        for file_name, moves in name_conflicts.items():
            if len(moves) == 1 and not moves[0].has_conflict:
                move_plan.append(moves[0])
            else:
                base_name = Path(file_name).stem
                extension = Path(file_name).suffix

                parsed = parse_renamed_name(file_name)
                if parsed and parsed.get('sequence'):
                    parts = base_name.split('_')
                    if len(parts) >= 4 and len(parts[-1]) == 3 and parts[-1].isdigit():
                        base_name_without_suffix = '_'.join(parts[:-1])
                        start_sequence = int(parts[-1])
                    else:
                        base_name_without_suffix = base_name
                        start_sequence = 0
                else:
                    base_name_without_suffix = base_name
                    start_sequence = 0

                existing_sequences = set()
                for item in root_directory.iterdir():
                    if item.is_file():
                        item_stem = item.stem
                        if item_stem.startswith(base_name_without_suffix):
                            parts = item_stem.split('_')
                            if parts and len(parts[-1]) == 3 and parts[-1].isdigit():
                                existing_sequences.add(int(parts[-1]))

                if start_sequence > 0:
                    existing_sequences.add(start_sequence)

                for i, move in enumerate(moves):
                    if existing_sequences:
                        sequence = max(existing_sequences) + 1
                    else:
                        sequence = start_sequence + 1 if start_sequence > 0 else 1

                    while sequence in existing_sequences:
                        sequence += 1

                    new_name = f"{base_name_without_suffix}_{sequence:03d}{extension}"

                    move.new_name = new_name
                    move.target_path = root_directory / new_name
                    move.has_conflict = True
                    move.sequence = sequence

                    existing_sequences.add(sequence)

                    move_plan.append(move)

                    self.logger.debug(f"Asignado {move.original_name} -> {new_name} (secuencia {sequence})")

        return move_plan

    def _generate_move_plan_by_month(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path, group_by_source: bool = False, group_by_type: bool = False) -> List[FileMove]:
        """Genera plan de movimiento clasificado por carpetas YYYY_MM
        
        Args:
            subdirectories: Archivos en subdirectorios
            root_files: Archivos en la raíz
            root_directory: Directorio raíz
            group_by_source: Si True, crea subcarpetas por fuente (WhatsApp, etc)
            group_by_type: Si True, crea subcarpetas por tipo (Fotos, Videos)
        """
        move_plan = []
        files_by_month = defaultdict(list)

        # Procesar archivos de subdirectorios
        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = Path(file_info['path'])

                if not file_path.exists():
                    self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                    continue

                file_date = get_date_from_file(file_path)
                if not file_date:
                    self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                    file_date = datetime.now()

                folder_name = file_date.strftime('%Y_%m')
                
                if group_by_source:
                    source = detect_file_source(file_info['name'], file_path)
                    folder_name = f"{folder_name}/{source}"
                
                if group_by_type:
                    type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
                    type_name = type_map.get(file_info['type'], 'Otros')
                    folder_name = f"{folder_name}/{type_name}"

                files_by_month[folder_name].append({
                    'file_info': file_info,
                    'subdir_name': subdir_name,
                    'date': file_date,
                    'source': source if group_by_source else detect_file_source(file_info['name'], file_path)
                })

        # Procesar archivos de la raíz
        for file_info in root_files:
            file_path = Path(file_info['path'])

            if not file_path.exists():
                self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                continue

            file_date = get_date_from_file(file_path)
            if not file_date:
                self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                file_date = datetime.now()

            folder_name = file_date.strftime('%Y_%m')

            if group_by_source:
                source = detect_file_source(file_info['name'], file_path)
                folder_name = f"{folder_name}/{source}"
            
            if group_by_type:
                type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
                type_name = type_map.get(file_info['type'], 'Otros')
                folder_name = f"{folder_name}/{type_name}"

            files_by_month[folder_name].append({
                'file_info': file_info,
                'subdir_name': '<root>',  # Indicar que viene de raíz
                'date': file_date
            })

        for folder_name, file_list in files_by_month.items():
            target_folder = root_directory / folder_name
            name_conflicts = defaultdict(list)

            existing_files_in_folder = set()
            if target_folder.exists():
                for item in target_folder.iterdir():
                    if item.is_file():
                        existing_files_in_folder.add(item.name)

            for file_data in file_list:
                file_info = file_data['file_info']
                file_path = Path(file_info['path'])
                file_name = file_info['name']

                has_conflict = file_name in existing_files_in_folder

                move = FileMove(
                    source_path=file_path,
                    target_path=target_folder / file_name,
                    original_name=file_name,
                    new_name=file_name,
                    subdirectory=file_data['subdir_name'],
                    file_type=file_info['type'],
                    size=file_info['size'],
                    has_conflict=has_conflict,
                    target_folder=folder_name
                )

                name_conflicts[file_name].append(move)

            move_plan.extend(self._resolve_conflicts_in_folder(name_conflicts, target_folder))

        return move_plan

    def _generate_move_plan_whatsapp(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path) -> List[FileMove]:
        """Genera plan de movimiento separando archivos de WhatsApp
        
        Args:
            subdirectories: Archivos en subdirectorios
            root_files: Archivos en la raíz
            root_directory: Directorio raíz
        """
        move_plan = []
        whatsapp_files = []
        other_files = []

        # Procesar archivos de subdirectorios
        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = Path(file_info['path'])

                if not file_path.exists():
                    self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                    continue

                file_data = {
                    'file_info': file_info,
                    'subdir_name': subdir_name
                }

                # Pasar tanto nombre como path para mejor detección de WhatsApp
                if is_whatsapp_file(file_info['name'], file_path):
                    whatsapp_files.append(file_data)
                else:
                    other_files.append(file_data)

        # Procesar archivos de la raíz
        for file_info in root_files:
            file_path = Path(file_info['path'])

            if not file_path.exists():
                self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                continue

            file_data = {
                'file_info': file_info,
                'subdir_name': '<root>'
            }

            # Pasar tanto nombre como path para mejor detección de WhatsApp
            if is_whatsapp_file(file_info['name'], file_path):
                whatsapp_files.append(file_data)
            else:
                other_files.append(file_data)

        if whatsapp_files:
            whatsapp_folder = root_directory / "whatsapp"
            existing_in_whatsapp = set()
            if whatsapp_folder.exists():
                for item in whatsapp_folder.iterdir():
                    if item.is_file():
                        existing_in_whatsapp.add(item.name)

            name_conflicts = defaultdict(list)
            for file_data in whatsapp_files:
                file_info = file_data['file_info']
                file_path = Path(file_info['path'])
                file_name = file_info['name']

                has_conflict = file_name in existing_in_whatsapp

                move = FileMove(
                    source_path=file_path,
                    target_path=whatsapp_folder / file_name,
                    original_name=file_name,
                    new_name=file_name,
                    subdirectory=file_data['subdir_name'],
                    file_type=file_info['type'],
                    size=file_info['size'],
                    has_conflict=has_conflict,
                    target_folder="whatsapp"
                )

                name_conflicts[file_name].append(move)

            move_plan.extend(self._resolve_conflicts_in_folder(name_conflicts, whatsapp_folder))

        if other_files:
            existing_in_root = set()
            for item in root_directory.iterdir():
                if item.is_file():
                    existing_in_root.add(item.name)

            name_conflicts = defaultdict(list)
            for file_data in other_files:
                file_info = file_data['file_info']
                file_path = Path(file_info['path'])
                file_name = file_info['name']

                has_conflict = file_name in existing_in_root

                move = FileMove(
                    source_path=file_path,
                    target_path=root_directory / file_name,
                    original_name=file_name,
                    new_name=file_name,
                    subdirectory=file_data['subdir_name'],
                    file_type=file_info['type'],
                    size=file_info['size'],
                    has_conflict=has_conflict
                )

                name_conflicts[file_name].append(move)

            move_plan.extend(self._resolve_conflicts_in_folder(name_conflicts, root_directory))

        return move_plan

    def _resolve_conflicts_in_folder(self, name_conflicts: Dict, target_folder: Path) -> List[FileMove]:
        """Resuelve conflictos de nombres dentro de una carpeta específica"""
        move_plan = []

        for file_name, moves in name_conflicts.items():
            if len(moves) == 1 and not moves[0].has_conflict:
                move_plan.append(moves[0])
            else:
                base_name = Path(file_name).stem
                extension = Path(file_name).suffix

                parsed = parse_renamed_name(file_name)
                if parsed and parsed.get('sequence'):
                    parts = base_name.split('_')
                    if len(parts) >= 4 and len(parts[-1]) == 3 and parts[-1].isdigit():
                        base_name_without_suffix = '_'.join(parts[:-1])
                        start_sequence = int(parts[-1])
                    else:
                        base_name_without_suffix = base_name
                        start_sequence = 0
                else:
                    base_name_without_suffix = base_name
                    start_sequence = 0

                existing_sequences = set()
                if target_folder.exists():
                    for item in target_folder.iterdir():
                        if item.is_file():
                            item_stem = item.stem
                            if item_stem.startswith(base_name_without_suffix):
                                parts = item_stem.split('_')
                                if parts and len(parts[-1]) == 3 and parts[-1].isdigit():
                                    existing_sequences.add(int(parts[-1]))

                if start_sequence > 0:
                    existing_sequences.add(start_sequence)

                for move in moves:
                    if existing_sequences:
                        sequence = max(existing_sequences) + 1
                    else:
                        sequence = start_sequence + 1 if start_sequence > 0 else 1

                    while sequence in existing_sequences:
                        sequence += 1

                    new_name = f"{base_name_without_suffix}_{sequence:03d}{extension}"

                    move.new_name = new_name
                    move.target_path = target_folder / new_name
                    move.has_conflict = True
                    move.sequence = sequence

                    existing_sequences.add(sequence)

                    move_plan.append(move)

        return move_plan

    def _generate_move_plan_by_year(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path, group_by_source: bool = False, group_by_type: bool = False) -> List[FileMove]:
        """Genera plan de movimiento clasificado por carpetas YYYY
        
        Args:
            subdirectories: Archivos en subdirectorios
            root_files: Archivos en la raíz
            root_directory: Directorio raíz
            group_by_source: Si True, crea subcarpetas por fuente
            group_by_type: Si True, crea subcarpetas por tipo
        """
        move_plan = []
        files_by_year = defaultdict(list)

        # Procesar archivos de subdirectorios
        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = Path(file_info['path'])

                if not file_path.exists():
                    self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                    continue

                file_date = get_date_from_file(file_path)
                if not file_date:
                    self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                    file_date = datetime.now()

                folder_name = file_date.strftime('%Y')

                if group_by_source:
                    source = detect_file_source(file_info['name'], file_path)
                    folder_name = f"{folder_name}/{source}"
                
                if group_by_type:
                    type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
                    type_name = type_map.get(file_info['type'], 'Otros')
                    folder_name = f"{folder_name}/{type_name}"

                files_by_year[folder_name].append({
                    'file_info': file_info,
                    'subdir_name': subdir_name,
                    'date': file_date
                })

        # Procesar archivos de la raíz
        for file_info in root_files:
            file_path = Path(file_info['path'])

            if not file_path.exists():
                self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                continue

            file_date = get_date_from_file(file_path)
            if not file_date:
                self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                file_date = datetime.now()

            folder_name = file_date.strftime('%Y')

            if group_by_source:
                source = detect_file_source(file_info['name'], file_path)
                folder_name = f"{folder_name}/{source}"
            
            if group_by_type:
                type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
                type_name = type_map.get(file_info['type'], 'Otros')
                folder_name = f"{folder_name}/{type_name}"

            files_by_year[folder_name].append({
                'file_info': file_info,
                'subdir_name': '<root>',
                'date': file_date
            })

        for folder_name, file_list in files_by_year.items():
            target_folder = root_directory / folder_name
            name_conflicts = defaultdict(list)

            existing_files_in_folder = set()
            if target_folder.exists():
                for item in target_folder.iterdir():
                    if item.is_file():
                        existing_files_in_folder.add(item.name)

            for file_data in file_list:
                file_info = file_data['file_info']
                file_path = Path(file_info['path'])
                file_name = file_info['name']

                has_conflict = file_name in existing_files_in_folder

                move = FileMove(
                    source_path=file_path,
                    target_path=target_folder / file_name,
                    original_name=file_name,
                    new_name=file_name,
                    subdirectory=file_data['subdir_name'],
                    file_type=file_info['type'],
                    size=file_info['size'],
                    has_conflict=has_conflict,
                    target_folder=folder_name,
                    source=source if group_by_source else detect_file_source(file_info['name'], file_path)
                )

                name_conflicts[file_name].append(move)

            move_plan.extend(self._resolve_conflicts_in_folder(name_conflicts, target_folder))

        return move_plan

    def _generate_move_plan_by_year_month(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path, group_by_source: bool = False, group_by_type: bool = False) -> List[FileMove]:
        """Genera plan de movimiento con jerarquía YYYY/MM
        
        Args:
            subdirectories: Archivos en subdirectorios
            root_files: Archivos en la raíz
            root_directory: Directorio raíz
            group_by_source: Si True, crea subcarpetas por fuente
            group_by_type: Si True, crea subcarpetas por tipo
        """
        move_plan = []
        files_by_year_month = defaultdict(list)

        # Procesar archivos de subdirectorios
        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = Path(file_info['path'])

                if not file_path.exists():
                    self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                    continue

                file_date = get_date_from_file(file_path)
                if not file_date:
                    self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                    file_date = datetime.now()

                year_folder = file_date.strftime('%Y')
                month_folder = file_date.strftime('%m')
                folder_path = f"{year_folder}/{month_folder}"

                if group_by_source:
                    source = detect_file_source(file_info['name'], file_path)
                    folder_path = f"{folder_path}/{source}"
                
                if group_by_type:
                    type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
                    type_name = type_map.get(file_info['type'], 'Otros')
                    folder_path = f"{folder_path}/{type_name}"

                files_by_year_month[folder_path].append({
                    'file_info': file_info,
                    'subdir_name': subdir_name,
                    'date': file_date,
                    'year': year_folder,
                    'month': month_folder
                })

        # Procesar archivos de la raíz
        for file_info in root_files:
            file_path = Path(file_info['path'])

            if not file_path.exists():
                self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                continue

            file_date = get_date_from_file(file_path)
            if not file_date:
                self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                file_date = datetime.now()

            year_folder = file_date.strftime('%Y')
            month_folder = file_date.strftime('%m')
            folder_path = f"{year_folder}/{month_folder}"

            if group_by_source:
                source = detect_file_source(file_info['name'], file_path)
                folder_path = f"{folder_path}/{source}"
            
            if group_by_type:
                type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
                type_name = type_map.get(file_info['type'], 'Otros')
                folder_path = f"{folder_path}/{type_name}"

            files_by_year_month[folder_path].append({
                'file_info': file_info,
                'subdir_name': '<root>',
                'date': file_date,
                'year': year_folder,
                'month': month_folder
            })

        for folder_path, file_list in files_by_year_month.items():
            # folder_path tiene formato "YYYY/MM"
            parts = folder_path.split('/')
            year = parts[0]
            month = parts[1]
            target_folder = root_directory / year / month
            name_conflicts = defaultdict(list)

            existing_files_in_folder = set()
            if target_folder.exists():
                for item in target_folder.iterdir():
                    if item.is_file():
                        existing_files_in_folder.add(item.name)

            for file_data in file_list:
                file_info = file_data['file_info']
                file_path = Path(file_info['path'])
                file_name = file_info['name']

                has_conflict = file_name in existing_files_in_folder

                move = FileMove(
                    source_path=file_path,
                    target_path=target_folder / file_name,
                    original_name=file_name,
                    new_name=file_name,
                    subdirectory=file_data['subdir_name'],
                    file_type=file_info['type'],
                    size=file_info['size'],
                    has_conflict=has_conflict,
                    target_folder=folder_path,
                    source=source if group_by_source else detect_file_source(file_info['name'], file_path)
                )

                name_conflicts[file_name].append(move)

            move_plan.extend(self._resolve_conflicts_in_folder(name_conflicts, target_folder))

        return move_plan

    def _generate_move_plan_by_type(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path, group_by_source: bool = False, date_grouping_type: Optional[str] = None) -> List[FileMove]:
        """Genera plan de movimiento separando por tipo de archivo (Fotos/Videos)
        
        Args:
            subdirectories: Archivos en subdirectorios
            root_files: Archivos en la raíz
            root_directory: Directorio raíz
            group_by_source: Si True, crea subcarpetas por fuente
            date_grouping_type: Tipo de agrupación por fecha ('month', 'year', 'year_month') o None
        """
        move_plan = []
        files_by_type = defaultdict(list)
        
        # Mapeo de tipos de Config a nombres de carpeta en español
        type_folder_map = {
            'PHOTO': 'Fotos',
            'VIDEO': 'Videos'
        }

        # Procesar archivos de subdirectorios
        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = Path(file_info['path'])

                if not file_path.exists():
                    self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                    continue

                file_type = file_info['type']  # 'PHOTO' o 'VIDEO' desde Config
                folder_name = type_folder_map.get(file_type, 'Otros')

                if group_by_source:
                    source = detect_file_source(file_info['name'], file_path)
                    folder_name = f"{folder_name}/{source}"
                
                if date_grouping_type:
                    file_date = get_date_from_file(file_path)
                    if not file_date:
                        file_date = datetime.now()
                    
                    if date_grouping_type == 'month':
                        date_folder = file_date.strftime('%Y_%m')
                    elif date_grouping_type == 'year':
                        date_folder = file_date.strftime('%Y')
                    elif date_grouping_type == 'year_month':
                        date_folder = file_date.strftime('%Y/%m')
                    else:
                        date_folder = ''
                    
                    if date_folder:
                        folder_name = f"{folder_name}/{date_folder}"

                files_by_type[folder_name].append({
                    'file_info': file_info,
                    'subdir_name': subdir_name
                })

        # Procesar archivos de la raíz
        for file_info in root_files:
            file_path = Path(file_info['path'])

            if not file_path.exists():
                self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                continue

            file_type = file_info['type']
            folder_name = type_folder_map.get(file_type, 'Otros')

            if group_by_source:
                source = detect_file_source(file_info['name'], file_path)
                folder_name = f"{folder_name}/{source}"

            if date_grouping_type:
                file_date = get_date_from_file(file_path)
                if not file_date:
                    file_date = datetime.now()
                
                if date_grouping_type == 'month':
                    date_folder = file_date.strftime('%Y_%m')
                elif date_grouping_type == 'year':
                    date_folder = file_date.strftime('%Y')
                elif date_grouping_type == 'year_month':
                    date_folder = file_date.strftime('%Y/%m')
                else:
                    date_folder = ''
                
                if date_folder:
                    folder_name = f"{folder_name}/{date_folder}"

            files_by_type[folder_name].append({
                'file_info': file_info,
                'subdir_name': '<root>'
            })

        for type_name, file_list in files_by_type.items():
            target_folder = root_directory / type_name
            name_conflicts = defaultdict(list)

            existing_files_in_folder = set()
            if target_folder.exists():
                for item in target_folder.iterdir():
                    if item.is_file():
                        existing_files_in_folder.add(item.name)

            for file_data in file_list:
                file_info = file_data['file_info']
                file_path = Path(file_info['path'])
                file_name = file_info['name']

                has_conflict = file_name in existing_files_in_folder

                move = FileMove(
                    source_path=file_path,
                    target_path=target_folder / file_name,
                    original_name=file_name,
                    new_name=file_name,
                    subdirectory=file_data['subdir_name'],
                    file_type=file_info['type'],
                    size=file_info['size'],
                    has_conflict=has_conflict,
                    target_folder=type_name,
                    source=source if group_by_source else detect_file_source(file_info['name'], file_path)
                )

                name_conflicts[file_name].append(move)

            move_plan.extend(self._resolve_conflicts_in_folder(name_conflicts, target_folder))

        return move_plan

    def _generate_move_plan_by_source(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path, date_grouping_type: Optional[str] = None) -> List[FileMove]:
        """Genera plan de movimiento separando por fuente detectada (WhatsApp/iPhone/Android/etc)
        
        Args:
            subdirectories: Archivos en subdirectorios
            root_files: Archivos en la raíz
            root_directory: Directorio raíz
            date_grouping_type: Tipo de agrupación por fecha ('month', 'year', 'year_month') o None
        """
        move_plan = []
        files_by_source = defaultdict(list)

        # Procesar archivos de subdirectorios
        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = Path(file_info['path'])

                if not file_path.exists():
                    self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                    continue

                source = detect_file_source(file_info['name'], file_path)

                if date_grouping_type:
                    file_date = get_date_from_file(file_path)
                    if not file_date:
                        file_date = datetime.now()
                    
                    if date_grouping_type == 'month':
                        date_folder = file_date.strftime('%Y_%m')
                    elif date_grouping_type == 'year':
                        date_folder = file_date.strftime('%Y')
                    elif date_grouping_type == 'year_month':
                        date_folder = file_date.strftime('%Y/%m')
                    else:
                        date_folder = ''
                        
                    if date_folder:
                        source = f"{source}/{date_folder}"

                files_by_source[source].append({
                    'file_info': file_info,
                    'subdir_name': subdir_name
                })

        # Procesar archivos de la raíz
        for file_info in root_files:
            file_path = Path(file_info['path'])

            if not file_path.exists():
                self.logger.warning(f"Saltando archivo que no existe: {file_path}")
                continue

            source = detect_file_source(file_info['name'], file_path)

            if date_grouping_type:
                file_date = get_date_from_file(file_path)
                if not file_date:
                    file_date = datetime.now()
                
                if date_grouping_type == 'month':
                    date_folder = file_date.strftime('%Y_%m')
                elif date_grouping_type == 'year':
                    date_folder = file_date.strftime('%Y')
                elif date_grouping_type == 'year_month':
                    date_folder = file_date.strftime('%Y/%m')
                else:
                    date_folder = ''
                    
                if date_folder:
                    source = f"{source}/{date_folder}"

            files_by_source[source].append({
                'file_info': file_info,
                'subdir_name': '<root>'
            })

        for source_name, file_list in files_by_source.items():
            target_folder = root_directory / source_name
            name_conflicts = defaultdict(list)

            existing_files_in_folder = set()
            if target_folder.exists():
                for item in target_folder.iterdir():
                    if item.is_file():
                        existing_files_in_folder.add(item.name)

            for file_data in file_list:
                file_info = file_data['file_info']
                file_path = Path(file_info['path'])
                file_name = file_info['name']

                has_conflict = file_name in existing_files_in_folder

                move = FileMove(
                    source_path=file_path,
                    target_path=target_folder / file_name,
                    original_name=file_name,
                    new_name=file_name,
                    subdirectory=file_data['subdir_name'],
                    file_type=file_info['type'],
                    size=file_info['size'],
                    has_conflict=has_conflict,
                    target_folder=source_name,
                    source=source_name
                )

                name_conflicts[file_name].append(move)

            move_plan.extend(self._resolve_conflicts_in_folder(name_conflicts, target_folder))

        return move_plan

    def create_backup(self, root_directory: Path, progress_callback=None) -> Path:
        """
        Crea backup de la estructura completa antes de organizar

        Args:
            root_directory: Directorio a respaldar
            progress_callback: Función para reportar progreso
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_organization_{root_directory.name}_{timestamp}"
        backup_path = Config.DEFAULT_BACKUP_DIR / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        from utils.file_utils import launch_backup_creation
        files = [p for p in root_directory.rglob("*") if p.is_file() and Config.is_supported_file(p.name)]
        try:
            backup_path = launch_backup_creation(files, root_directory, backup_prefix='backup_organization', progress_callback=progress_callback, metadata_name='organization_metadata.txt')
            self.backup_dir = backup_path
            return backup_path
        except ValueError as ve:
            err_msg = f"Backup abortado: entrada inválida para launch_backup_creation: {ve}"
            self.logger.error(err_msg)
            raise
