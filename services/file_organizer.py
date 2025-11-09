"""
Organizador de Archivos
"""
import shutil
import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Callable
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger
from utils.callback_utils import safe_progress_callback
from utils.settings_manager import settings_manager
from utils.date_utils import parse_renamed_name, get_file_date
from services.result_types import OrganizationResult, OrganizationAnalysisResult


class OrganizationType(Enum):
    """Tipos de organización disponibles"""
    TO_ROOT = "to_root"
    BY_MONTH = "by_month"
    WHATSAPP_SEPARATE = "whatsapp_separate"


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
    target_folder: Optional[str] = None  # Carpeta destino (para BY_MONTH o WHATSAPP_SEPARATE)

    def __post_init__(self):
        """Validaciones"""
        if not self.source_path.exists():
            raise ValueError(f"Archivo origen no existe: {self.source_path}")

    @property
    def will_rename(self) -> bool:
        """True si el archivo será renombrado"""
        return self.original_name != self.new_name


class FileOrganizer:
    """
    Organizador de archivos - Mueve archivos multimedia de subdirectorios al directorio raíz
    """

    # Patrones de WhatsApp (iPhone y Android)
    WHATSAPP_PATTERNS = [
        r'^IMG-\d{8}-WA\d{4}\..*$',  # IMG-20231025-WA0001.jpg
        r'^VID-\d{8}-WA\d{4}\..*$',  # VID-20231025-WA0001.mp4
        r'^AUD-\d{8}-WA\d{4}\..*$',  # AUD-20231025-WA0001.opus
        r'^PTT-\d{8}-WA\d{4}\..*$',  # PTT (voice notes)
        r'^WhatsApp\s+Image\s+\d{4}-\d{2}-\d{2}\s+at\s+.*\..*$',  # WhatsApp Image 2023-10-25 at 12.34.56.jpg
        r'^WhatsApp\s+Video\s+\d{4}-\d{2}-\d{2}\s+at\s+.*\..*$',  # WhatsApp Video 2023-10-25 at 12.34.56.mp4
    ]

    def __init__(self):
        self.logger = get_logger("FileOrganizer")
        self.backup_dir = None

    @classmethod
    def is_whatsapp_file(cls, filename: str) -> bool:
        """
        Verifica si un archivo es de WhatsApp basándose en su nombre

        Args:
            filename: Nombre del archivo

        Returns:
            True si el nombre coincide con patrones de WhatsApp
        """
        for pattern in cls.WHATSAPP_PATTERNS:
            if re.match(pattern, filename, re.IGNORECASE):
                return True
        return False

    def analyze_directory_structure(self, root_directory: Path, organization_type: OrganizationType = OrganizationType.TO_ROOT, progress_callback=None) -> OrganizationAnalysisResult:
        """
        Analiza la estructura de directorios para organización

        Args:
            root_directory: Directorio raíz a analizar
            organization_type: Tipo de organización a realizar
            progress_callback: Función opcional (current, total, message) para reportar progreso

        Returns:
            OrganizationAnalysisResult con análisis detallado
        """
        self.logger.info(f"Analizando estructura de directorios para organización ({organization_type.value}): {root_directory}")

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
        if organization_type in (OrganizationType.BY_MONTH, OrganizationType.WHATSAPP_SEPARATE) and root_files_list:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(get_file_info, f): f for f in root_files_list}
                for future in as_completed(futures):
                    file_path = futures[future]
                    root_file_names.add(file_path.name)
                    
                    info = future.result()
                    if info:
                        root_file_info.append(info)
                    
                    processed_files += 1
                    if progress_callback:
                        # Si el callback retorna False, cancelar análisis
                        if not progress_callback(processed_files, total_files, "Analizando estructura de organización"):
                            self.logger.info("Análisis de organización cancelado por el usuario")
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
            if progress_callback:
                # Si el callback retorna False, cancelar análisis
                if not progress_callback(processed_files, total_files, "Analizando estructura de organización"):
                    self.logger.info("Análisis de organización cancelado por el usuario")
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

        # Procesar subdirectorios
        for item in root_directory.iterdir():
            if not item.is_dir():
                continue

            subdir_name = item.name
            subdir_files_list = [file_path for file_path in item.iterdir()
                                if file_path.is_file() and Config.is_supported_file(file_path.name)]
            
            if not subdir_files_list:
                continue

            # Procesar archivos del subdirectorio en paralelo
            subdir_files = []
            total_size = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(get_file_info, f): f for f in subdir_files_list}
                for future in as_completed(futures):
                    info = future.result()
                    if info:
                        subdir_files.append(info)
                        total_size += info['size']
                        files_by_type[info['type']] += 1
                    
                    processed_files += 1
                    if progress_callback:
                        # Si el callback retorna False, cancelar análisis
                        if not progress_callback(processed_files, total_files, "Analizando estructura de organización"):
                            self.logger.info("Análisis de organización cancelado por el usuario")
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

            if subdir_files:
                subdirectories[subdir_name] = {
                    'path': str(item),
                    'file_count': len(subdir_files),
                    'total_size': total_size,
                    'files': subdir_files
                }

                total_files_to_move += len(subdir_files)
                total_size_to_move += total_size

        # Para by_month y whatsapp_separate, agregar archivos de raíz
        if organization_type in (OrganizationType.BY_MONTH, OrganizationType.WHATSAPP_SEPARATE):
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
                organization_type
            )
            potential_conflicts = sum(1 for move in move_plan if move.has_conflict)
            folders_to_create = sorted(set(move.target_folder for move in move_plan if move.target_folder))

        self.logger.info(f"Análisis completado: {total_files_to_move} archivos para mover desde {len(subdirectories)} subdirectorios + {len(root_files)} en raíz")

        return OrganizationAnalysisResult(
            success=True,
            total_files=total_files_to_move,
            root_directory=str(root_directory),
            organization_type=organization_type.value,
            subdirectories=subdirectories,
            root_files=root_files,
            total_files_to_move=total_files_to_move,
            total_size_to_move=total_size_to_move,
            potential_conflicts=potential_conflicts,
            files_by_type=dict(files_by_type),
            move_plan=move_plan,
            folders_to_create=folders_to_create
        )

    def _generate_move_plan(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path, existing_file_names: Set[str], organization_type: OrganizationType) -> List[FileMove]:
        """
        Genera plan de movimiento con resolución de conflictos según el tipo de organización
        
        Args:
            subdirectories: Diccionario de subdirectorios con sus archivos
            root_files: Lista de archivos en la raíz (para by_month y whatsapp_separate)
            root_directory: Path del directorio raíz
            existing_file_names: Set de nombres de archivos existentes en raíz
            organization_type: Tipo de organización
        """
        if organization_type == OrganizationType.TO_ROOT:
            return self._generate_move_plan_to_root(subdirectories, root_directory, existing_file_names)
        elif organization_type == OrganizationType.BY_MONTH:
            return self._generate_move_plan_by_month(subdirectories, root_files, root_directory)
        elif organization_type == OrganizationType.WHATSAPP_SEPARATE:
            return self._generate_move_plan_whatsapp(subdirectories, root_files, root_directory)
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
                        has_conflict=has_conflict
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

    def _generate_move_plan_by_month(self, subdirectories: Dict, root_files: List[Dict], root_directory: Path) -> List[FileMove]:
        """Genera plan de movimiento clasificado por carpetas YYYY_MM
        
        Args:
            subdirectories: Archivos en subdirectorios
            root_files: Archivos en la raíz
            root_directory: Directorio raíz
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

                file_date = get_file_date(file_path)
                if not file_date:
                    self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                    file_date = datetime.now()

                folder_name = file_date.strftime('%Y_%m')

                files_by_month[folder_name].append({
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

            file_date = get_file_date(file_path)
            if not file_date:
                self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
                file_date = datetime.now()

            folder_name = file_date.strftime('%Y_%m')

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

                if self.is_whatsapp_file(file_info['name']):
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

            if self.is_whatsapp_file(file_info['name']):
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

    def execute_organization(self, move_plan: List[FileMove], create_backup: bool = True,
                            cleanup_empty_dirs: bool = True, dry_run: bool = False, 
                            progress_callback=None) -> Dict:
        """
        Ejecuta la organización según el plan con resolución dinámica de conflictos
        
        Args:
            move_plan: Plan de movimientos a ejecutar
            create_backup: Si crear backup antes de mover
            cleanup_empty_dirs: Si limpiar directorios vacíos al final
            dry_run: Si solo simular sin mover archivos reales
            progress_callback: Callback de progreso
        """
        if not move_plan:
            return OrganizationResult(
                success=True,
                files_moved=0,
                empty_directories_removed=0,
                message='No hay archivos para mover'
            )

        self.logger.info("=" * 80)
        self.logger.info("*** INICIANDO ORGANIZACIÓN DE ARCHIVOS")
        self.logger.info(f"*** Archivos a mover: {len(move_plan)}")
        if dry_run:
            self.logger.info("*** Modo: SIMULACIÓN")
        self.logger.info("=" * 80)

        results = OrganizationResult(success=True, dry_run=dry_run)

        try:
            # Determinar el directorio raíz correctamente
            # Buscar en los target_path para encontrar el verdadero root
            if move_plan[0].target_folder:
                # Si el primer archivo va a una subcarpeta, el root es parent.parent
                root_directory = move_plan[0].target_path.parent.parent
            else:
                # Si va directo a raíz, el root es parent
                root_directory = move_plan[0].target_path.parent
            
            # Verificar con otro archivo del plan para asegurarnos
            for move in move_plan:
                if not move.target_folder:
                    # Este archivo va directo al root, su parent ES el root
                    root_directory = move.target_path.parent
                    break

            # Crear carpetas necesarias (BY_MONTH o WHATSAPP_SEPARATE) - solo si no es simulación
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

            # Crear backup ANTES de mover archivos - solo si no es simulación
            if create_backup and move_plan and not dry_run:
                safe_progress_callback(progress_callback, 0, len(move_plan), "Creando backup antes de organizar...")
                from utils.file_utils import launch_backup_creation
                files = [m.source_path for m in move_plan]
                try:
                    backup_path = launch_backup_creation(files, root_directory, backup_prefix='backup_organization', progress_callback=progress_callback, metadata_name='organization_metadata.txt')
                    results.backup_path = str(backup_path)
                except ValueError as ve:
                    err_msg = f"Backup abortado: entrada inválida para launch_backup_creation: {ve}"
                    self.logger.error(err_msg)
                    results.add_error(err_msg)
                    return results
                except Exception as e:
                    self.logger.error(f"Error creando backup: {e}")
                    results.add_error(f'Error creando backup: {str(e)}')

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

            safe_progress_callback(progress_callback, 0, total_files, "Iniciando organización de directorios...")

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
                        file_date = get_file_date(move.source_path, verbose=is_by_month)
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

                    safe_progress_callback(progress_callback, files_processed, total_files,
                                       f"{'Simulando' if dry_run else 'Organizando'} directorios... {files_processed}/{total_files}")

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

            self.logger.info("=" * 80)
            if dry_run:
                self.logger.info("*** SIMULACIÓN DE ORGANIZACIÓN DE ARCHIVOS COMPLETADA")
                self.logger.info(f"*** Resultado: {results.files_moved} archivos se moverían")
            else:
                self.logger.info("*** ORGANIZACIÓN DE ARCHIVOS COMPLETADA")
                self.logger.info(f"*** Resultado: {results.files_moved} archivos movidos")
            if results.errors:
                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                self.logger.info(f"*** {error_prefix}Errores encontrados durante la {'simulación' if dry_run else 'organización'}:")
                for error in results.errors:
                    self.logger.error(f"  ✗ {error}")
            self.logger.info("=" * 80)

        except Exception as e:
            self.logger.error(f"Error crítico en organización: {str(e)}")
            results.add_error(f"Error crítico: {str(e)}")

        return results

    # Empty directory cleanup delegated to utils.file_utils.cleanup_empty_directories

    def organize_directory(self, root_directory: Path, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        Organiza los archivos de subdirectorios al directorio raíz

        Args:
            root_directory: Directorio raíz a organizar
            progress_callback: Función callback(current, total, message) para reportar progreso
        """
        self.logger.info(f"Organizando directorio: {root_directory}")

        # Obtener todos los archivos a mover
        all_files = []
        for item in root_directory.rglob("*"):
            if item.is_file() and Config.is_supported_file(item.name):
                all_files.append(item)

        total_files = len(all_files)
        moved_files = 0

        for file_path in all_files:
            moved_files += 1

            # Reportar progreso cada archivo
            safe_progress_callback(progress_callback, moved_files, total_files, f"Moviendo archivo {moved_files} de {total_files}")

        safe_progress_callback(progress_callback, total_files, total_files, "Organización completada")
