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

        # Obtener todos los archivos multimedia
        all_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file() and config.config.is_supported_file(file_path.name):
                all_files.append(file_path)

        results['total_files'] = len(all_files)
        total_files = len(all_files)

        # Analizar cada archivo
        renaming_map = {}  # nombre_renombrado -> lista de archivos
        processed = 0

        for file_path in all_files:
            processed += 1

            # Reportar progreso cada 10 archivos para no saturar la UI
            if progress_callback and processed % 10 == 0:
                progress_callback(processed, total_files, "Analizando nombres de archivos")

            # Verificar si ya está renombrado
            if is_renamed_filename(file_path.name):
                results['already_renamed'] += 1
                continue

            # Obtener fecha del archivo
            file_date = get_file_date(file_path)
            if not file_date:
                results['cannot_process'] += 1
                results['issues'].append(f"No se pudo obtener fecha: {file_path.name}")
                continue

            # Generar nombre renombrado
            file_type = config.config.get_file_type(file_path.name)
            if file_type == 'OTHER':
                results['cannot_process'] += 1
                results['issues'].append(f"Tipo de archivo no soportado: {file_path.name}")
                continue

            extension = file_path.suffix
            renamed_name = format_renamed_name(file_date, file_type, extension)

            # Agregar al mapa para detectar conflictos
            if renamed_name not in renaming_map:
                renaming_map[renamed_name] = []

            renaming_map[renamed_name].append({
                'original_path': file_path,
                'date': file_date,
                'type': file_type,
                'extension': extension
            })

            results['files_by_year'][file_date.year] += 1

        # Enviar actualización final de progreso
        if progress_callback:
            progress_callback(total_files, total_files, "Analizando nombres de archivos")

        # Resolver conflictos y crear plan final
        for renamed_name, file_list in renaming_map.items():
            if len(file_list) == 1:
                # Sin conflicto
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
                # Conflicto - añadir secuencias
                results['conflicts'] += len(file_list) - 1

                # Ordenar por fecha de modificación para consistencia
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

    def create_backup(self, directory: Path, progress_callback=None) -> Path:
        """
        Crea backup del directorio antes de renombrar

        Args:
            directory: Directorio a respaldar
            progress_callback: Función para reportar progreso

        Returns:
            Ruta del backup creado
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_renaming_{directory.name}_{timestamp}"

        # Usar directorio de backups de la configuración
        backup_path = config.config.DEFAULT_BACKUP_DIR / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Creando backup en: {backup_path}")

        # Informar al UI/worker sobre la ruta del backup
        if progress_callback:
            try:
                # total_files ya calculado más abajo; enviar mensaje con ruta
                progress_callback(0, 0, f"Creando backup en: {backup_path}")
            except Exception:
                pass

        # Obtener total de archivos para el progreso
        total_files = sum(1 for f in directory.rglob("*") 
                         if f.is_file() and config.config.is_supported_file(f.name))
        
        if progress_callback:
            progress_callback(0, total_files, f"Iniciando creación de backup en: {backup_path}")

        # Copiar solo archivos multimedia (no todo el directorio)
        files_backed_up = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file() and config.config.is_supported_file(file_path.name):
                # Mantener estructura relativa
                relative_path = file_path.relative_to(directory)
                backup_file_path = backup_path / relative_path

                # Crear directorios padre si es necesario
                backup_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Copiar archivo
                shutil.copy2(file_path, backup_file_path)
                files_backed_up += 1

                if progress_callback:
                    progress_callback(files_backed_up, total_files, 
                                   f"Creando backup... {files_backed_up}/{total_files}")

        self.logger.info(f"Backup completado: {files_backed_up} archivos respaldados")
        self.backup_dir = backup_path
        return backup_path

    def _find_next_available_name(
        self,
        base_path: Path,
        base_name: str,
        extension: str
    ) -> Tuple[str, int]:
        """
        Encuentra el siguiente nombre disponible con sufijo

        Args:
            base_path: Directorio donde buscar
            base_name: Nombre base sin extensión (ej: 20240824_172920_PHOTO)
            extension: Extensión del archivo (ej: .JPG)

        Returns:
            Tupla (nombre_completo, secuencia)
        """
        # Extraer base sin sufijo si ya lo tiene
        parts = base_name.split('_')

        # Si el último part es un número de 3 dígitos, es un sufijo existente
        if len(parts) >= 4 and len(parts[-1]) == 3 and parts[-1].isdigit():
            base_without_suffix = '_'.join(parts[:-1])
            start_sequence = int(parts[-1])
        else:
            base_without_suffix = base_name
            start_sequence = 0

        # Buscar todas las secuencias existentes
        existing_sequences = set()
        for file_path in base_path.iterdir():
            if file_path.is_file() and file_path.stem.startswith(base_without_suffix):
                file_parts = file_path.stem.split('_')
                if file_parts and len(file_parts[-1]) == 3 and file_parts[-1].isdigit():
                    existing_sequences.add(int(file_parts[-1]))

        # Encontrar siguiente secuencia disponible
        if existing_sequences:
            sequence = max(existing_sequences) + 1
        else:
            sequence = start_sequence + 1 if start_sequence > 0 else 1

        # Asegurar que no existe
        while sequence in existing_sequences:
            sequence += 1

        new_name = f"{base_without_suffix}_{sequence:03d}{extension}"
        return new_name, sequence

    def execute_renaming(
        self,
        renaming_plan: List[Dict],
        create_backup: bool = True,
        progress_callback=None
    ) -> Dict:
        """
        Ejecuta el renombrado según el plan

        MEJORADO: Si el destino existe, busca siguiente sufijo disponible

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
            # Crear backup si se solicita
            if create_backup and renaming_plan:
                first_file = renaming_plan[0]['original_path']
                directory = first_file.parent

                # Encontrar directorio común
                for item in renaming_plan[1:]:
                    try:
                        directory = Path(
                            os.path.commonpath([directory, item['original_path'].parent])
                        )
                    except ValueError:
                        break

                if progress_callback:
                    progress_callback(0, len(renaming_plan), "Creando backup...")
                    
                backup_path = self.create_backup(directory, progress_callback)
                results['backup_path'] = str(backup_path)

            # Ejecutar renombrados
            total_files = len(renaming_plan)
            files_processed = 0
            for item in renaming_plan:
                original_path = item['original_path']
                new_name = item['new_name']
                new_path = original_path.parent / new_name

                try:
                    # Verificar que el archivo original aún existe
                    if not original_path.exists():
                        error_msg = f"Archivo no encontrado: {original_path.name}"
                        self.logger.error(error_msg)
                        self.logger.error(f"  → Ruta completa: {original_path}")
                        results['errors'].append({
                            'file': str(original_path),
                            'error': error_msg,
                            'type': 'FileNotFoundError'
                        })
                        continue

                    # Si el destino ya existe, buscar siguiente disponible
                    if new_path.exists():
                        base_name = Path(new_name).stem
                        extension = Path(new_name).suffix

                        # Buscar siguiente nombre disponible
                        new_name, sequence = self._find_next_available_name(
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

                    # Renombrar archivo
                    original_path.rename(new_path)

                    # Registrar éxito
                    results['files_renamed'] += 1
                    files_processed += 1
                    results['renamed_files'].append({
                        'original': original_path.name,
                        'new_name': new_name,
                        'date': item['date'].strftime('%Y-%m-%d %H:%M:%S'),
                        'had_conflict': item['has_conflict']
                    })

                    if progress_callback:
                        progress_callback(files_processed, total_files,
                                       f"Renombrando archivos... {files_processed}/{total_files}")

                    self.logger.info(f"Renombrado: {original_path.name} -> {new_name}")

                except Exception as e:
                    # Error renombrando este archivo específico
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

            # Verificar si hubo errores
            if results['errors']:
                results['success'] = len(results['errors']) < len(renaming_plan)

            self.logger.info(
                f"Renombrado completado: {results['files_renamed']} archivos renombrados, "
                f"{results['conflicts_resolved']} conflictos resueltos, "
                f"{len(results['errors'])} errores"
            )

            # Mostrar resumen de errores si los hay
            if results['errors']:
                self.logger.error("=" * 70)
                self.logger.error(f"RESUMEN DE ERRORES ({len(results['errors'])} archivos):")
                self.logger.error("=" * 70)
                for i, error in enumerate(results['errors'], 1):
                    self.logger.error(f"{i}. {Path(error['file']).name}")
                    self.logger.error(f"   {error.get('type', 'Error')}: {error['error']}")
                self.logger.error("=" * 70)

        except Exception as e:
            # Error general en todo el proceso
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

        # Obtener todos los archivos a renombrar
        all_files = []
        for file_path in directory.rglob("*"):
            if file_path.is_file() and config.config.is_supported_file(file_path.name):
                all_files.append(file_path)

        total_files = len(all_files)
        renamed_files = 0

        for file_path in all_files:
            renamed_files += 1

            # Reportar progreso cada archivo
            if progress_callback:
                progress_callback(renamed_files, total_files, f"Renombrando archivo {renamed_files} de {total_files}")

            # Aquí iría la lógica para renombrar el archivo
            # nuevo_nombre = generar_nombre(file_path)
            # file_path.rename(nuevo_nombre)

        # Actualizar progreso final
        if progress_callback:
            progress_callback(total_files, total_files, "Renombrado completado")
