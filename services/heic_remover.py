"""
Eliminador de HEIC Duplicados
"""
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
import hashlib

import config
from utils.logger import get_logger
from utils.file_utils import validate_file_exists, to_path

@dataclass
class DuplicatePair:
    """Representa un par de archivos duplicados (HEIC + JPG)"""
    heic_path: Path
    jpg_path: Path
    base_name: str
    heic_size: int
    jpg_size: int
    directory: Path
    heic_date: Optional[datetime] = None
    jpg_date: Optional[datetime] = None
    similarity_score: float = 1.0  # 1.0 = idénticos (mismo nombre base)

    def __post_init__(self):
        """Validaciones"""
        try:
            validate_file_exists(self.heic_path)
        except FileNotFoundError as e:
            # Preserve previous behavior which raised ValueError
            raise ValueError(str(e))

        try:
            validate_file_exists(self.jpg_path)
        except FileNotFoundError as e:
            raise ValueError(str(e))

        # Obtener fechas si no se proporcionaron
        if not self.heic_date:
            self.heic_date = datetime.fromtimestamp(self.heic_path.stat().st_mtime)
        if not self.jpg_date:
            self.jpg_date = datetime.fromtimestamp(self.jpg_path.stat().st_mtime)

    @property
    def total_size(self) -> int:
        """Tamaño total del par"""
        return self.heic_size + self.jpg_size

    @property
    def size_saving_keep_jpg(self) -> int:
        """Ahorro eliminando HEIC"""
        return self.heic_size

    @property
    def size_saving_keep_heic(self) -> int:
        """Ahorro eliminando JPG"""
        return self.jpg_size

    @property
    def compression_ratio(self) -> float:
        """Ratio de compresión HEIC vs JPG"""
        if self.jpg_size > 0:
            return self.heic_size / self.jpg_size
        return 0.0

    def format_sizes(self) -> str:
        """Formatea tamaños para display"""
        def format_bytes(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"

        heic_str = format_bytes(self.heic_size)
        jpg_str = format_bytes(self.jpg_size)
        saving_str = format_bytes(self.heic_size)  # Asumiendo que eliminamos HEIC

        return f"HEIC: {heic_str}, JPG: {jpg_str}, Ahorro: {saving_str}"

class HEICDuplicateRemover:
    """
    Eliminador de HEIC Duplicados - Compara archivos HEIC con sus equivalentes JPG
    """

    def __init__(self):
        self.logger = get_logger("HEICDuplicateRemover")
        self.backup_dir = None

        # Configuración
        self.heic_extensions = {'.heic', '.heif'}
        self.jpg_extensions = {'.jpg', '.jpeg'}

        # Estadísticas
        self.stats = {
            'heic_files_found': 0,
            'jpg_files_found': 0,
            'duplicate_pairs_found': 0,
            'total_heic_size': 0,
            'total_jpg_size': 0,
            'potential_savings': 0
        }

    def analyze_heic_duplicates(self, directory: Path, recursive: bool = True) -> Dict:
        """
        Analiza duplicados HEIC/JPG en un directorio

        Args:
            directory: Directorio a analizar
            recursive: Si buscar recursivamente en subdirectorios

        Returns:
            Análisis detallado de duplicados
        """
        self.logger.info(f"Analizando duplicados HEIC en: {directory}")
        self._reset_stats()

        results = {
            'directory': directory,
            'duplicate_pairs': [],
            'orphan_heic': [],
            'orphan_jpg': [],
            'total_heic_files': 0,
            'total_jpg_files': 0,
            'total_duplicates': 0,
            'potential_savings_keep_jpg': 0,
            'potential_savings_keep_heic': 0,
            'by_directory': defaultdict(int),
            'compression_stats': {
                'min_ratio': float('inf'),
                'max_ratio': 0.0,
                'avg_ratio': 0.0
            }
        }

        # Encontrar archivos HEIC y JPG
        heic_files = {}
        jpg_files = {}

        file_iterator = directory.rglob("*") if recursive else directory.iterdir()

        for file_path in file_iterator:
            if not file_path.is_file():
                continue

            extension = file_path.suffix.lower()
            base_name = file_path.stem

            if extension in self.heic_extensions:
                heic_files[base_name] = file_path
                self.stats['total_heic_size'] += file_path.stat().st_size
            elif extension in self.jpg_extensions:
                jpg_files[base_name] = file_path
                self.stats['total_jpg_size'] += file_path.stat().st_size

        results['total_heic_files'] = len(heic_files)
        results['total_jpg_files'] = len(jpg_files)

        self.stats['heic_files_found'] = len(heic_files)
        self.stats['jpg_files_found'] = len(jpg_files)

        # Encontrar pares duplicados
        duplicate_pairs = []
        matched_heic = set()
        matched_jpg = set()

        for base_name, heic_path in heic_files.items():
            if base_name in jpg_files:
                jpg_path = jpg_files[base_name]

                try:
                    # Crear par de duplicados
                    duplicate_pair = DuplicatePair(
                        heic_path=heic_path,
                        jpg_path=jpg_path,
                        base_name=base_name,
                        heic_size=heic_path.stat().st_size,
                        jpg_size=jpg_path.stat().st_size,
                        directory=heic_path.parent
                    )

                    duplicate_pairs.append(duplicate_pair)
                    matched_heic.add(base_name)
                    matched_jpg.add(base_name)

                    # Actualizar estadísticas
                    results['potential_savings_keep_jpg'] += duplicate_pair.heic_size
                    results['potential_savings_keep_heic'] += duplicate_pair.jpg_size
                    results['by_directory'][str(heic_path.parent)] += 1

                    self.logger.debug(f"Duplicado encontrado: {base_name}")

                except Exception as e:
                    self.logger.error(f"Error procesando par {base_name}: {e}")

        results['duplicate_pairs'] = duplicate_pairs
        results['total_duplicates'] = len(duplicate_pairs)

        self.stats['duplicate_pairs_found'] = len(duplicate_pairs)
        self.stats['potential_savings'] = results['potential_savings_keep_jpg']

        # Encontrar huérfanos (archivos sin pareja)
        results['orphan_heic'] = [heic_files[name] for name in heic_files.keys() if name not in matched_heic]
        results['orphan_jpg'] = [jpg_files[name] for name in jpg_files.keys() if name not in matched_jpg]

        # Calcular estadísticas de compresión
        if duplicate_pairs:
            compression_ratios = [pair.compression_ratio for pair in duplicate_pairs if pair.compression_ratio > 0]
            if compression_ratios:
                results['compression_stats']['min_ratio'] = min(compression_ratios)
                results['compression_stats']['max_ratio'] = max(compression_ratios)
                results['compression_stats']['avg_ratio'] = sum(compression_ratios) / len(compression_ratios)

        self.logger.info(f"Análisis completado: {len(duplicate_pairs)} pares duplicados encontrados")
        return results

    # Backup creation delegated to utils.file_utils.create_backup

    def execute_removal(self, duplicate_pairs: List[DuplicatePair], 
                       keep_format: str = 'jpg', 
                       create_backup: bool = True) -> Dict:
        """
        Ejecuta la eliminación de duplicados

        Args:
            duplicate_pairs: Lista de pares duplicados
            keep_format: 'jpg' o 'heic' - formato a mantener
            create_backup: Si crear backup antes de eliminar

        Returns:
            Resultados de la operación
        """
        if not duplicate_pairs:
            return {
                'success': True,
                'files_deleted': 0,
                'space_freed': 0,
                'errors': [],
                'message': 'No hay archivos duplicados para eliminar'
            }

        self.logger.info(f"Iniciando eliminación de duplicados HEIC: {len(duplicate_pairs)} pares")

        results = {
            'success': True,
            'files_deleted': 0,
            'space_freed': 0,
            'errors': [],
            'deleted_files': [],
            'backup_path': None,
            'format_kept': keep_format
        }

        try:
            # Determinar archivos a eliminar
            files_to_delete = []
            if keep_format.lower() == 'jpg':
                files_to_delete = [pair.heic_path for pair in duplicate_pairs]
            else:  # keep_format == 'heic'
                files_to_delete = [pair.jpg_path for pair in duplicate_pairs]

            # Crear backup si se solicita
            if create_backup and files_to_delete:
                root_directory = duplicate_pairs[0].directory

                # Encontrar directorio común
                for pair in duplicate_pairs[1:]:
                    try:
                        root_directory = Path(os.path.commonpath([root_directory, pair.directory]))
                    except ValueError:
                        break
                from utils.file_utils import launch_backup_creation
                try:
                    backup_path = launch_backup_creation(
                        files_to_delete,
                        root_directory,
                        backup_prefix='backup_heic_removal',
                        metadata_name='heic_removal_metadata.txt'
                    )
                    results['backup_path'] = str(backup_path)
                    self.backup_dir = backup_path
                except ValueError as ve:
                    err_msg = f"Backup abortado: entrada inválida para launch_backup_creation: {ve}"
                    self.logger.error(err_msg)
                    results['errors'].append(err_msg)
                    results['success'] = False
                    return results

            for pair in duplicate_pairs:
                file_to_delete = to_path(pair, ('heic_path', 'jpg_path', 'path', 'source_path', 'original_path')) if keep_format.lower() == 'jpg' else to_path(pair, ('jpg_path', 'heic_path', 'path', 'source_path', 'original_path'))
                file_to_keep = to_path(pair, ('jpg_path', 'heic_path', 'path', 'source_path', 'original_path')) if keep_format.lower() == 'jpg' else to_path(pair, ('heic_path', 'jpg_path', 'path', 'source_path', 'original_path'))
                base_name = None
                if isinstance(pair, dict) and 'base_name' in pair:
                    base_name = pair['base_name']
                elif hasattr(pair, 'base_name'):
                    base_name = getattr(pair, 'base_name')

                try:
                    try:
                        validate_file_exists(file_to_delete)
                    except FileNotFoundError as e:
                        results['errors'].append(str(e))
                        self.logger.error(str(e))
                        continue

                    try:
                        validate_file_exists(file_to_keep)
                    except FileNotFoundError as e:
                        results['errors'].append(str(e))
                        self.logger.error(str(e))
                        continue

                    file_size = file_to_delete.stat().st_size
                    file_to_delete.unlink()

                    results['files_deleted'] += 1
                    results['space_freed'] += file_size
                    results['deleted_files'].append({
                        'deleted': str(file_to_delete),
                        'kept': str(file_to_keep),
                        'base_name': base_name,
                        'size_freed': file_size,
                        'format_deleted': file_to_delete.suffix.upper()
                    })

                    self.logger.info(f"Eliminado: {file_to_delete.name}, Mantenido: {file_to_keep.name}")

                except Exception as e:
                    error_msg = f"Error eliminando {file_to_delete}: {str(e)}"
                    results['errors'].append(error_msg)
                    self.logger.error(error_msg)

            if results['errors']:
                results['success'] = len(results['errors']) < len(duplicate_pairs)

            from utils.format_utils import format_size
            freed = format_size(results['space_freed'])

            results['files_removed'] = results.get('files_deleted', 0)
            results['kept_format'] = results.get('format_kept')

            self.logger.info(f"Eliminación completada: {results['files_deleted']} archivos eliminados, "
                           f"{freed} liberados, {len(results['errors'])} errores")

        except Exception as e:
            error_msg = f"Error durante eliminación: {str(e)}"
            results['errors'].append(error_msg)
            results['success'] = False
            self.logger.error(error_msg)

        return results

    def _reset_stats(self):
        """Reinicia estadísticas"""
        for key in self.stats:
            self.stats[key] = 0

    def get_stats(self) -> Dict:
        """Obtiene estadísticas actuales"""
        return self.stats.copy()

