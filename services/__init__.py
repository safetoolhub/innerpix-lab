"""
Servicios de lógica de negocio para Pixaro Lab.

Este módulo expone todos los servicios y tipos de datos principales
utilizados en la aplicación, incluyendo:

- Servicios principales: FileRenamer, LivePhotoService, FileOrganizer, etc.
- Servicios base: BaseService, BaseDetectorService
- Orquestador: AnalysisOrchestrator para coordinar análisis completos
- Tipos de resultado: Todas las dataclasses de resultado de operaciones
- View Models: Modelos de presentación sin dependencias de UI
- Utilidades: Funciones helper y tipos de datos auxiliares
"""

# Servicios principales
from .file_renamer_service import FileRenamer
from .live_photos_service import LivePhotoService, LivePhotoGroup, CleanupMode
from .file_organizer_service import FileOrganizer, FileMove, OrganizationType
from .heic_remover_service import HEICRemover, DuplicatePair
from .exact_copies_detector import ExactCopiesDetector
from .similar_files_detector import SimilarFilesDetector, SimilarFilesAnalysis

# Orquestador
from .analysis_orchestrator import AnalysisOrchestrator, FullAnalysisResult

# Servicios base
from .base_service import BaseService, BackupCreationError, ProgressCallback
from .base_detector_service import BaseDetectorService

# View Models
from .view_models import (
    TreeNode,
    TableRow,
    OrganizationTreeNode,
    OrganizationViewModel,
    RenameTableRow,
    RenameViewModel,
    HEICTreeNode,
    HEICViewModel,
    DuplicateTreeNode,
    DuplicatesViewModel,
)

# Tipos de resultado
from .result_types import (
    # Base
    OperationResult,
    AnalysisResult,
    DeletionResult,
    # Renaming
    RenameResult,
    RenameAnalysisResult,
    # Organization
    OrganizationResult,
    OrganizationAnalysisResult,
    # Duplicates
    DuplicateGroup,
    DuplicateAnalysisResult,
    DuplicateDeletionResult,
    # HEIC
    HeicAnalysisResult,
    HeicDeletionResult,
    # Live Photos
    LivePhotoAnalysisResult,
    LivePhotoCleanupAnalysisResult,
    LivePhotoCleanupResult,
    LivePhotoDetectionResult,
)

__all__ = [
    # Servicios
    'FileRenamer',
    'LivePhotoService',
    'FileOrganizer',
    'HEICRemover',
    'ExactCopiesDetector',
    'SimilarFilesDetector',
    'AnalysisOrchestrator',
    # Servicios base
    'BaseService',
    'BaseDetectorService',
    # Excepciones
    'BackupCreationError',
    # Type aliases
    'ProgressCallback',
    # Enums
    'CleanupMode',
    'OrganizationType',
    # Dataclasses de servicios
    'LivePhotoGroup',
    'FileMove',
    'DuplicatePair',
    'DuplicateGroup',
    'SimilarFilesAnalysis',
    # Utilidades
    'create_service_backup',
    'validate_and_get_file_info',
    'FileInfo',
    'format_file_list',
    # View Models
    'TreeNode',
    'TableRow',
    'OrganizationTreeNode',
    'OrganizationViewModel',
    'RenameTableRow',
    'RenameViewModel',
    'HEICTreeNode',
    'HEICViewModel',
    'DuplicateTreeNode',
    'DuplicatesViewModel',
]
