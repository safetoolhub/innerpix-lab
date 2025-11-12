"""
Renombrador de nombres de archivos multimedia - VERSIÓN FINAL
Con logs detallados y resolución inteligente de conflictos
"""
import shutil
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger
from utils.settings_manager import settings_manager
from services.result_types import RenameResult, RenameAnalysisResult
from services.base_service import BaseService, ProgressCallback
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
from utils.decorators import deprecated

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
        progress_callback: Optional[ProgressCallback] = None
    ) -> RenameAnalysisResult:
        """
        Analiza un directorio para renombrado (método unificado).
        
        Este es el método recomendado. Alias de analyze_directory().
        
        Args:
            directory: Directorio a analizar
            progress_callback: Función callback(current, total, message)
            
        Returns:
            RenameAnalysisResult con análisis detallado
        """
        return self.analyze_directory(directory, progress_callback)
    
    def execute(
        self,
        renaming_plan: List[Dict],
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[ProgressCallback] = None
    ) -> RenameResult:
        """
        Ejecuta el renombrado según el plan (método unificado).
        
        Este es el método recomendado. Alias de execute_renaming().
        
        Args:
            renaming_plan: Plan de renombrado del análisis
            create_backup: Si crear backup antes de proceder
            dry_run: Si True, simula la operación
            progress_callback: Callback para reportar progreso
            
        Returns:
            RenameResult con resultados de la operación
        """
        return self.execute_renaming(
            renaming_plan, 
            create_backup, 
            dry_run, 
            progress_callback
        )
    
    # ========================================================================
    # UTILIDADES
    # ========================================================================

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
