"""Utilities for file operations shared across services.

Functions:
- calculate_file_hash(path, chunk_size=8192, cache=None)
- create_backup(files, base_directory, backup_prefix, progress_callback=None)
- cleanup_empty_directories(root_directory)
- find_next_available_name(base_path, base_name, extension)

These are pure helpers designed to centralize duplicated code from services.
"""
from pathlib import Path
from datetime import datetime
import shutil
from typing import Iterable, Optional, Tuple, List
import hashlib
import os

from utils.format_utils import format_size
from utils.callback_utils import safe_progress_callback


def validate_file_exists(path) -> Path:
    """Normalize input to Path and verify the file exists and is a file.

    Args:
        path: str or Path-like to validate

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: if the path does not exist or is not a file
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {p}")
    if not p.is_file():
        raise FileNotFoundError(f"No es un archivo válido: {p}")
    return p


def validate_files_list(paths: Iterable) -> Tuple[List[Path], List[str]]:
    """Validate an iterable of paths and return a tuple (valid_paths, missing_paths).

    This function will not raise on missing items. Instead it returns two
    collections:
      - valid_paths: list of Path objects that exist and are files
      - missing_paths: list of string paths that were missing or not files

    Callers can then decide whether to abort, log, or continue.
    """
    valid: List[Path] = []
    missing: List[str] = []
    for p in paths:
        try:
            valid.append(validate_file_exists(p))
        except FileNotFoundError:
            missing.append(str(p))

    return valid, missing


def to_path(obj, attr_names=('path', 'source_path', 'original_path')) -> Path:
    """Convierte un objeto flexible a Path.

    Args:
        obj: str, bytes, Path, dict o objeto con atributos
        attr_names: tuple de nombres de atributos a buscar

    Returns:
        Path: ruta del archivo

    Raises:
        ValueError: si no se puede extraer una ruta válida
    """
    if isinstance(obj, (str, bytes)):
        return Path(obj)
    if isinstance(obj, Path):
        return obj
    if isinstance(obj, dict):
        for k in attr_names:
            if k in obj:
                return Path(obj[k])
        if obj:
            return Path(next(iter(obj.values())))
    for k in attr_names:
        if hasattr(obj, k):
            return Path(getattr(obj, k))

    try:
        return Path(obj)
    except (TypeError, ValueError) as e:
        raise ValueError(f"No se pudo convertir {type(obj).__name__} a Path") from e


def calculate_file_hash(file_path: Path, chunk_size: int = 8192, cache: Optional[dict] = None) -> str:
    """Calculate SHA256 hash of a file.

    If a cache dict is provided, the function will store and reuse computed hashes
    keyed by the file's string path.
    """
    key = str(file_path)
    if cache is not None and key in cache:
        return cache[key]

    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(chunk_size), b''):
            sha256.update(chunk)

    digest = sha256.hexdigest()
    if cache is not None:
        cache[key] = digest
    return digest


def _ensure_backup_dir(backup_dir: Path):
    backup_dir.mkdir(parents=True, exist_ok=True)


def launch_backup_creation(
    files: Iterable[Path],
    base_directory: Path,
    backup_prefix: str = "backup",
    progress_callback=None,
    metadata_name: Optional[str] = None
) -> Path:
    """Create a backup directory and copy the given files preserving relative paths.

    Args:
        files: Iterable of Path objects to back up
        base_directory: Base directory used to compute relative paths
        backup_prefix: Prefix used to name the backup folder
        progress_callback: optional callback (current, total, message)
        metadata_name: filename used to store metadata (defaults to backup_prefix + '_metadata.txt')

    Returns:
        Path to the created backup directory
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{backup_prefix}_{base_directory.name}_{timestamp}"

    from config import Config
    backup_root = Config.DEFAULT_BACKUP_DIR

    backup_path = backup_root / backup_name
    _ensure_backup_dir(backup_path)

    files_list = []
    for item in files:
        try:
            normalized = to_path(item)
            files_list.append(normalized)
        except ValueError as ve:
            raise ValueError(
                f"launch_backup_creation: cannot normalize item to a path: type={type(item).__name__}, repr={repr(item)}"
            ) from ve

    total = len(files_list)
    copied = 0
    total_size = 0

    for file_path in files_list:
        try:
            if base_directory in file_path.parents:
                relative_path = file_path.relative_to(base_directory)
            else:
                relative_path = file_path.parent.name / file_path.name

            dest = backup_path / relative_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest)
            copied += 1
            total_size += file_path.stat().st_size

            safe_progress_callback(progress_callback, copied, total, f"Creando backup: {backup_path} ({copied}/{total})")

        except Exception:
            raise

    # Write metadata
    metadata_name = metadata_name or f"{backup_prefix}_metadata.txt"
    metadata_path = backup_path / metadata_name
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(f"BACKUP: {backup_prefix}\n")
        f.write(f"Creado: {datetime.now()}\n")
        f.write(f"Directorio base: {base_directory}\n")
        f.write(f"Archivos respaldados: {copied}\n")
        f.write(f"Tamaño total: {format_size(total_size)}\n")
        f.write("\nARCHIVOS RESPALDADOS:\n")
        for p in files_list:
            f.write(f"- {p}\n")

    return backup_path


def cleanup_empty_directories(root_directory: Path) -> int:
    """Remove empty directories under root_directory (excluding root).

    Returns the number of directories removed.
    """
    removed_count = 0
    for item in sorted(root_directory.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if item.is_dir() and item != root_directory:
            try:
                if not any(item.iterdir()):
                    item.rmdir()
                    removed_count += 1
            except OSError:
                pass
    return removed_count


def find_next_available_name(base_path: Path, base_name: str, extension: str) -> Tuple[str, int]:
    """Find next available filename with numeric suffix (XXX) in base_path.

    Returns (new_name, sequence)
    
    Si el nombre base termina en un sufijo numérico de 3 dígitos (_XXX), lo reemplaza.
    Si termina en un sufijo numérico de otra longitud (_X, _XX, _XXXX), lo preserva y añade el nuevo sufijo.
    """
    parts = base_name.split('_')
    
    # Detectar si tiene un sufijo numérico de 3 dígitos (patrón estándar)
    if len(parts) >= 4 and len(parts[-1]) == 3 and parts[-1].isdigit():
        base_without_suffix = '_'.join(parts[:-1])
        start_sequence = int(parts[-1])
    else:
        # No tiene sufijo de 3 dígitos, usar el nombre completo como base
        base_without_suffix = base_name
        start_sequence = 0

    existing_sequences = set()
    for file_path in base_path.iterdir():
        if file_path.is_file() and file_path.stem.startswith(base_without_suffix):
            file_parts = file_path.stem.split('_')
            if file_parts and len(file_parts[-1]) == 3 and file_parts[-1].isdigit():
                existing_sequences.add(int(file_parts[-1]))

    if existing_sequences:
        sequence = max(existing_sequences) + 1
    else:
        sequence = start_sequence + 1 if start_sequence > 0 else 1

    while sequence in existing_sequences:
        sequence += 1

    new_name = f"{base_without_suffix}_{sequence:03d}{extension}"
    return new_name, sequence
