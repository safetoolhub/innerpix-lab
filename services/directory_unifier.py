"""
Unificador de Directorios
"""
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Callable
from collections import defaultdict, Counter
from dataclasses import dataclass

import config
from utils.logger import get_logger
from utils.date_utils import parse_renamed_name

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

    def __post_init__(self):
        """Validaciones"""
        if not self.source_path.exists():
            raise ValueError(f"Archivo origen no existe: {self.source_path}")

    @property
    def will_rename(self) -> bool:
        """True si el archivo será renombrado"""
        return self.original_name != self.new_name

class DirectoryUnifier:
    """
    Unificador de directorios - Mueve archivos multimedia de subdirectorios al directorio raíz
    """

    def __init__(self):
        self.logger = get_logger("DirectoryUnifier")
        self.backup_dir = None

    def analyze_directory_structure(self, root_directory: Path) -> Dict:
        """
        Analiza la estructura de directorios para unificación

        Args:
            root_directory: Directorio raíz a analizar

        Returns:
            Diccionario con análisis detallado
        """
        self.logger.info(f"Analizando estructura de directorios para unificación: {root_directory}")

        results = {
            'root_directory': str(root_directory),
            'subdirectories': {},
            'total_files_to_move': 0,
            'total_size_to_move': 0,
            'potential_conflicts': 0,
            'files_by_type': Counter(),
            'move_plan': []
        }

        # Obtener archivos en raíz (para detectar conflictos)
        root_files = set()
        for item in root_directory.iterdir():
            if item.is_file() and config.config.is_supported_file(item.name):
                root_files.add(item.name)

        # Analizar subdirectorios
        for item in root_directory.iterdir():
            if not item.is_dir():
                continue

            subdir_name = item.name
            subdir_files = []
            total_size = 0

            # Recolectar archivos multimedia en subdirectorio, ignorando subdirectorios con el mismo nombre
            for file_path in item.iterdir():  # Cambiado de rglob a iterdir para solo buscar en el primer nivel
                if file_path.is_file() and config.config.is_supported_file(file_path.name):
                    file_size = file_path.stat().st_size
                    file_type = config.config.get_file_type(file_path.name)

                    subdir_files.append({
                        'path': file_path,
                        'name': file_path.name,
                        'size': file_size,
                        'type': file_type
                    })

                    total_size += file_size
                    results['files_by_type'][file_type] += 1

            if subdir_files:
                results['subdirectories'][subdir_name] = {
                    'path': str(item),
                    'file_count': len(subdir_files),
                    'total_size': total_size,
                    'files': subdir_files
                }

                results['total_files_to_move'] += len(subdir_files)
                results['total_size_to_move'] += total_size

        # Generar plan de movimiento con resolución de conflictos
        if results['subdirectories']:
            results['move_plan'] = self._generate_move_plan(
                results['subdirectories'],
                root_directory,
                root_files
            )
            results['potential_conflicts'] = sum(1 for move in results['move_plan'] if move.has_conflict)

        self.logger.info(f"Análisis completado: {results['total_files_to_move']} archivos para mover desde {len(results['subdirectories'])} subdirectorios")

        return results

    def _generate_move_plan(self, subdirectories: Dict, root_directory: Path, existing_files: Set[str]) -> List[
        FileMove]:
        """
        Genera plan de movimiento con resolución de conflictos
        CORREGIDO: Maneja correctamente múltiples archivos con el mismo nombre
        """
        move_plan = []
        name_conflicts = defaultdict(list)

        # Agrupar archivos por nombre para detectar conflictos
        for subdir_name, subdir_data in subdirectories.items():
            for file_info in subdir_data['files']:
                file_path = file_info['path']
                file_name = file_info['name']

                # Solo procesar si el archivo existe
                if Path(file_path).exists():
                    # Verificar si ya existe en raíz
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

        # Resolver conflictos
        for file_name, moves in name_conflicts.items():
            if len(moves) == 1 and not moves[0].has_conflict:
                # Sin conflicto - un solo archivo y no existe en destino
                move_plan.append(moves[0])
            else:
                # Hay conflicto - resolver con secuencias
                base_name = Path(file_name).stem
                extension = Path(file_name).suffix

                # Verificar si el archivo ya tiene sufijo numérico de renombrado
                parsed = parse_renamed_name(file_name)
                if parsed and parsed.get('sequence'):
                        # Ya tiene sufijo de renombrado
                    parts = base_name.split('_')
                    # Si el último part es numérico de 3 dígitos, es un sufijo
                    if len(parts) >= 4 and len(parts[-1]) == 3 and parts[-1].isdigit():
                        # Reconstruir sin el último sufijo
                        base_name_without_suffix = '_'.join(parts[:-1])
                        start_sequence = int(parts[-1])
                    else:
                        base_name_without_suffix = base_name
                        start_sequence = 0
                else:
                    # No tiene sufijo, usar el nombre completo como base
                    base_name_without_suffix = base_name
                    start_sequence = 0

                # Encontrar todas las secuencias que ya existen en el directorio destino
                existing_sequences = set()
                for item in root_directory.iterdir():
                    if item.is_file():
                        item_stem = item.stem
                        # Verificar si empieza con nuestra base
                        if item_stem.startswith(base_name_without_suffix):
                            # Extraer número al final si existe
                            parts = item_stem.split('_')
                            if parts and len(parts[-1]) == 3 and parts[-1].isdigit():
                                existing_sequences.add(int(parts[-1]))

                # También añadir la secuencia del nombre original si la tiene
                if start_sequence > 0:
                    existing_sequences.add(start_sequence)

                # Asignar secuencias ÚNICAS para cada archivo en moves
                for i, move in enumerate(moves):
                    # Encontrar la siguiente secuencia disponible
                    if existing_sequences:
                        sequence = max(existing_sequences) + 1
                    else:
                        sequence = start_sequence + 1 if start_sequence > 0 else 1

                    # Asegurarse de que no existe
                    while sequence in existing_sequences:
                        sequence += 1

                    # Crear nuevo nombre
                    new_name = f"{base_name_without_suffix}_{sequence:03d}{extension}"

                    # Actualizar el move
                    move.new_name = new_name
                    move.target_path = root_directory / new_name
                    move.has_conflict = True
                    move.sequence = sequence

                    # CRÍTICO: Añadir esta secuencia al set ANTES de procesar el siguiente archivo
                    existing_sequences.add(sequence)

                    # Añadir al plan
                    move_plan.append(move)

                    self.logger.debug(f"Asignado {move.original_name} -> {new_name} (secuencia {sequence})")

        return move_plan

    def create_backup(self, root_directory: Path, progress_callback=None) -> Path:
        """
        Crea backup de la estructura completa antes de unificar

        Args:
            root_directory: Directorio a respaldar
            progress_callback: Función para reportar progreso
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_unification_{root_directory.name}_{timestamp}"
        backup_path = config.Config.DEFAULT_BACKUP_DIR / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Creando backup en: {backup_path}")

        # Informar al UI/worker sobre la ruta del backup
        if progress_callback:
            try:
                progress_callback(0, 0, f"Creando backup en: {backup_path}")
            except Exception:
                pass

        # Obtener total de archivos para el progreso
        total_files = sum(1 for f in root_directory.rglob("*") 
                         if f.is_file() and config.Config.is_supported_file(f.name))

        if progress_callback:
            progress_callback(0, total_files, "Iniciando creación de backup...")

        # Copiar toda la estructura (no mover, solo copiar)
        files_backed_up = 0
        for item in root_directory.rglob("*"):
            if item.is_file() and config.Config.is_supported_file(item.name):
                relative_path = item.relative_to(root_directory)
                backup_file_path = backup_path / relative_path
                backup_file_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    shutil.copy2(item, backup_file_path)
                    files_backed_up += 1
                except Exception as e:
                    self.logger.warning(f"Error copiando {item.name} al backup: {e}")
                finally:
                    # Emitir progreso intermedio incluyendo la ruta del backup
                    if progress_callback:
                        try:
                            progress_callback(files_backed_up, total_files, f"Creando backup en: {backup_path} ({files_backed_up}/{total_files})")
                        except Exception:
                            pass

        self.logger.info(f"Backup completado: {files_backed_up} archivos")
        self.backup_dir = backup_path
        return backup_path

    def execute_unification(self, move_plan: List[FileMove], create_backup: bool = True,
                            cleanup_empty_dirs: bool = True, progress_callback=None) -> Dict:
        """
        Ejecuta la unificación según el plan con resolución dinámica de conflictos
        """
        if not move_plan:
            return {
                'success': True,
                'files_moved': 0,
                'empty_directories_removed': 0,
                'errors': [],
                'message': 'No hay archivos para mover'
            }

        self.logger.info(f"Iniciando unificación de {len(move_plan)} archivos")

        results = {
            'success': True,
            'files_moved': 0,
            'empty_directories_removed': 0,
            'errors': [],
            'moved_files': [],
            'backup_path': None
        }

        try:
            # Determinar el directorio raíz
            root_directory = move_plan[0].target_path.parent

            # Crear backup ANTES de mover archivos
            if create_backup and move_plan:
                try:
                    if progress_callback:
                        progress_callback(0, len(move_plan), "Creando backup antes de unificar...")
                    backup_path = self.create_backup(root_directory, progress_callback)
                    results['backup_path'] = str(backup_path)
                except Exception as e:
                    self.logger.error(f"Error creando backup: {e}")
                    results['errors'].append({
                        'file': 'BACKUP',
                        'error': f'Error creando backup: {str(e)}'
                    })

            # Track de nombres ya usados durante la ejecución
            used_names = set()
            # Cargar nombres existentes en el directorio raíz
            for item in root_directory.iterdir():
                if item.is_file():
                    used_names.add(item.name)

            # Ejecutar movimientos con resolución dinámica de conflictos
            files_processed = 0
            total_files = len(move_plan)

            if progress_callback:
                progress_callback(0, total_files, "Iniciando unificación de directorios...")

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

                    # Verificar conflicto en tiempo real
                    target_name = move.new_name
                    target_path = root_directory / target_name

                    # Si el destino ya existe o ya fue usado en esta ejecución, buscar nuevo nombre
                    if target_path.exists() or target_name in used_names:
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
                            new_target_path = root_directory / new_name

                            if not new_target_path.exists() and new_name not in used_names:
                                target_name = new_name
                                target_path = new_target_path
                                move.new_name = new_name
                                move.target_path = new_target_path
                                move.sequence = sequence
                                self.logger.info(f"Renombrado por conflicto: {move.original_name} -> {new_name}")
                                break

                            sequence += 1

                            # Protección contra bucle infinito
                            if sequence > 9999:
                                raise Exception(f"No se pudo encontrar nombre único después de 9999 intentos")

                    # Asegurar que el directorio destino existe
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # Mover archivo con verificación adicional
                    try:
                        # Verificar una última vez que el archivo existe y es accesible
                        if move.source_path.exists() and move.source_path.is_file():
                            move.source_path.rename(target_path)
                            # Añadir a la lista de nombres usados
                            used_names.add(target_name)
                        else:
                            raise FileNotFoundError(f"Archivo no encontrado o no accesible: {move.source_path}")
                    except (FileNotFoundError, PermissionError, OSError) as e:
                        raise Exception(f"Error moviendo archivo: {str(e)}")

                    results['files_moved'] += 1
                    files_processed += 1
                    
                    if progress_callback:
                        progress_callback(files_processed, total_files,
                                       f"Unificando directorios... {files_processed}/{total_files}")

                    results['moved_files'].append({
                        'original': str(move.source_path),
                        'new_location': str(target_path),
                        'renamed': move.will_rename,
                        'had_conflict': move.has_conflict
                    })

                    self.logger.info(f"Movido: {move.source_path.name} -> {target_name}")

                except Exception as e:
                    self.logger.error(f"Error moviendo {move.source_path.name}: {str(e)}")
                    results['errors'].append({
                        'file': str(move.source_path),
                        'error': str(e)
                    })

            # Limpiar directorios vacíos
            if cleanup_empty_dirs:
                try:
                    removed = self._cleanup_empty_directories(root_directory)
                    results['empty_directories_removed'] = removed
                except Exception as e:
                    self.logger.error(f"Error limpiando directorios: {e}")

            # Determinar éxito general
            if results['errors']:
                results['success'] = len(results['errors']) < len(move_plan)

            self.logger.info(
                f"Unificación completada: {results['files_moved']} archivos movidos, "
                f"{len(results['errors'])} errores"
            )

        except Exception as e:
            self.logger.error(f"Error crítico en unificación: {str(e)}")
            results['success'] = False
            results['errors'].append({
                'file': 'GENERAL',
                'error': str(e)
            })

        return results

    def _cleanup_empty_directories(self, root_directory: Path) -> int:
        """
        Elimina directorios vacíos
        """
        removed_count = 0

        for item in sorted(root_directory.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if item.is_dir() and item != root_directory:
                try:
                    if not any(item.iterdir()):
                        item.rmdir()
                        removed_count += 1
                        self.logger.info(f"Directorio vacío eliminado: {item.name}")
                except OSError:
                    pass

        return removed_count

    def unify_directory(self, root_directory: Path, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        Unifica los archivos de subdirectorios al directorio raíz

        Args:
            root_directory: Directorio raíz a unificar
            progress_callback: Función callback(current, total, message) para reportar progreso
        """
        self.logger.info(f"Unificando directorio: {root_directory}")

        # Obtener todos los archivos a mover
        all_files = []
        for item in root_directory.rglob("*"):
            if item.is_file() and config.config.is_supported_file(item.name):
                all_files.append(item)

        total_files = len(all_files)
        moved_files = 0

        for file_path in all_files:
            moved_files += 1

            # Reportar progreso cada archivo
            if progress_callback:
                progress_callback(moved_files, total_files, f"Moviendo archivo {moved_files} de {total_files}")

            # Aquí iría la lógica para mover el archivo
            # shutil.move(file_path, destino)

        if progress_callback:
            progress_callback(total_files, total_files, "Unificación completada")
