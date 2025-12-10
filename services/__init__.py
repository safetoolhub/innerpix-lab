"""
Servicios de lógica de negocio para Pixaro Lab.

Este módulo expone todos los servicios y tipos de datos principales
utilizados en la aplicación, incluyendo:

- Servicios principales: FileRenamer, LivePhotoService, FileOrganizer, etc.
- Servicios base: BaseService, DuplicatesBaseService
- Orquestador: AnalysisOrchestrator para coordinar análisis completos
- Tipos de resultado: Todas las dataclasses de resultado de operaciones
- View Models: Modelos de presentación sin dependencias de UI
- Utilidades: Funciones helper y tipos de datos auxiliares
"""

# Servicios principales
from .file_renamer_service import FileRenamer
from .live_photos_service import LivePhotoService, LivePhotoGroup, CleanupMode
from .file_organizer_service import FileOrganizer, FileMove, OrganizationType
from .heic_service import HeicService, DuplicatePair
from .duplicates_exact_service import DuplicatesExactService
from .duplicates_similar_service import DuplicatesSimilarService, DuplicatesSimilarAnalysis

# Orquestador
from .analysis_orchestrator import AnalysisOrchestrator, FullAnalysisResult

# Servicios base
from .base_service import BaseService, BackupCreationError, ProgressCallback
from .duplicates_base_service import DuplicatesBaseService

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

# Utilidades de file_utils
from utils.file_utils import (
    create_service_backup,
    validate_and_get_file_info,
    FileInfo,
    format_file_list,
)

# Tipos de resultado
from .result_types import (
    # Base
    OperationResult,
    AnalysisResult,
    DeletionResult,
    # Renaming
    RenameDeletionResult,
    RenameAnalysisResult,
    # Organization
    OrganizationDeletionResult,
    OrganizationAnalysisResult,
    # Duplicates
    DuplicateGroup,
    DuplicatePair,
    DuplicateAnalysisResult,
    DuplicateDeletionResult,
    # HEIC
    HeicAnalysisResult,
    HeicDeletionResult,
    # Live Photos
    LivePhotoCleanupAnalysisResult,
    LivePhotoCleanupDeletionResult,
    LivePhotoDetectionResult,
)

__all__ = [
    # Servicios
    'FileRenamer',
    'LivePhotoService',
    'FileOrganizer',
    'HEICRemover',
    'DuplicatesExactService',
    'DuplicatesSimilarService',
    'AnalysisOrchestrator',
    # Servicios base
    'BaseService',
    'DuplicatesBaseService',
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
    # Utilidades de file_utils
    'create_service_backup',
    'validate_and_get_file_info',
    'FileInfo',
    'format_file_list',
    # Orquestador results
    'FullAnalysisResult',
    # Tipos de resultado base
    'OperationResult',
    'AnalysisResult',
    'DeletionResult',
    'RenameDeletionResult',
    'RenameAnalysisResult',
    'OrganizationDeletionResult',
    'OrganizationAnalysisResult',
    'DuplicateAnalysisResult',
    'DuplicateDeletionResult',
    'HeicAnalysisResult',
    'HeicDeletionResult',
    'LivePhotoCleanupAnalysisResult',
    'LivePhotoCleanupDeletionResult',
    'LivePhotoDetectionResult',
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
