"""
Servicios de lógica de negocio para Innerpix Lab.

Este módulo expone todos los servicios y tipos de datos principales
utilizados en la aplicación, incluyendo:

- Servicios principales: FileRenamer, LivePhotoService, FileOrganizer, etc.
- Servicios base: BaseService
- Tipos de resultado: Todas las dataclasses de resultado de operaciones
- Utilidades: Funciones helper y tipos de datos auxiliares
"""

# Servicios principales
from .file_renamer_service import FileRenamerService
from .live_photos_service import LivePhotoService
from .file_organizer_service import FileOrganizerService, FileMove, OrganizationType
from .heic_service import HeicService, HEICDuplicatePair
from .duplicates_exact_service import DuplicatesExactService
from .duplicates_similar_service import DuplicatesSimilarService, DuplicatesSimilarAnalysis
from .visual_identical_service import VisualIdenticalService
from .zero_byte_service import ZeroByteService

# Servicios base
from .base_service import BaseService, BackupCreationError, ProgressCallback

# Utilidades de file_utils
# (none currently)

# Tipos de resultado
from .result_types import (
    # Base
    BaseResult,
    AnalysisResult,
    ExecutionResult,
    # Renaming
    RenameAnalysisResult,
    RenameExecutionResult,
    # Organization
    OrganizationAnalysisResult,
    OrganizationExecutionResult,
    # Exact Duplicates (SHA256)
    ExactDuplicateGroup,
    ExactDuplicateAnalysisResult,
    ExactDuplicateExecutionResult,
    # Similar Duplicates (Perceptual Hash)
    SimilarDuplicateGroup,
    SimilarDuplicateAnalysisResult,
    SimilarDuplicateExecutionResult,
    # HEIC
    HEICDuplicatePair,
    HeicAnalysisResult,
    HeicExecutionResult,
    # Live Photos
    LivePhotoImageInfo,
    LivePhotoGroup,
    LivePhotosAnalysisResult,
    LivePhotosExecutionResult,
    # Visual Identical
    VisualIdenticalGroup,
    VisualIdenticalAnalysisResult,
    VisualIdenticalExecutionResult,
    # Zero Byte
    ZeroByteAnalysisResult,
    ZeroByteExecutionResult,
)

__all__ = [
    # Servicios
    'FileRenamerService',
    'LivePhotoService',
    'FileOrganizerService',
    'HeicService',
    'DuplicatesExactService',
    'DuplicatesSimilarService',
    'VisualIdenticalService',
    'ZeroByteService',
    # Servicios base
    'BaseService',
    # Excepciones
    'BackupCreationError',
    # Type aliases
    'ProgressCallback',
    # Enums
    'OrganizationType',
    # Dataclasses de servicios
    'LivePhotoGroup',
    'LivePhotoImageInfo',
    'FileMove',
    'HEICDuplicatePair',
    'DuplicatesSimilarAnalysis',
    'VisualIdenticalGroup',
    # Exact Duplicates
    'ExactDuplicateGroup',
    'ExactDuplicateAnalysisResult',
    'ExactDuplicateExecutionResult',
    # Similar Duplicates
    'SimilarDuplicateGroup',
    'SimilarDuplicateAnalysisResult',
    'SimilarDuplicateExecutionResult',
    # Tipos de resultado base
    'BaseResult',
    'AnalysisResult',
    'ExecutionResult',
    'RenameAnalysisResult',
    'RenameExecutionResult',
    'OrganizationAnalysisResult',
    'OrganizationExecutionResult',
    'HeicAnalysisResult',
    'HeicExecutionResult',
    'LivePhotosAnalysisResult',
    'LivePhotosExecutionResult',
    'VisualIdenticalAnalysisResult',
    'VisualIdenticalExecutionResult',
    'ZeroByteAnalysisResult',
    'ZeroByteExecutionResult',
]
