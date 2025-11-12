"""
Tipos de resultados estandarizados para servicios de PhotoKit Manager

Define dataclasses consistentes para resultados de análisis y operaciones,
eliminando la heterogeneidad de diccionarios con keys variables.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path


@dataclass
class DuplicateGroup:
    """
    Grupo de archivos duplicados (copias exactas o similares).
    
    Usado por ExactCopiesDetector y SimilarFilesDetector.
    """
    hash_value: str  # SHA256 hash o perceptual hash
    files: List[Path]
    total_size: int
    similarity_score: float = 100.0  # Copias exactas = 100%, similares = variable


@dataclass
class OperationResult:
    """Resultado base de cualquier operación"""
    success: bool = True
    errors: List[str] = field(default_factory=list)
    message: Optional[str] = None

    def __post_init__(self):
        """Validaciones post-inicialización"""
        if self.errors is None:
            self.errors = []

    @property
    def has_errors(self) -> bool:
        """True si hay errores"""
        return len(self.errors) > 0
    
    @property
    def error(self) -> Optional[str]:
        """Primer error de la lista (para compatibilidad)"""
        return self.errors[0] if self.errors else None

    def add_error(self, error: str):
        """Añade un error a la lista"""
        self.errors.append(error)
        if self.success:
            self.success = False


@dataclass
class AnalysisResult(OperationResult):
    """Resultado base de análisis"""
    total_files: int = 0


@dataclass
class DeletionResult(OperationResult):
    """Resultado de operación de eliminación"""
    files_deleted: int = 0
    space_freed: int = 0
    backup_path: Optional[str] = None
    deleted_files: List[str] = field(default_factory=list)


@dataclass
class RenameResult(OperationResult):
    """Resultado de operación de renombrado"""
    files_renamed: int = 0
    renamed_files: List[dict] = field(default_factory=list)
    backup_path: Optional[str] = None
    conflicts_resolved: int = 0
    dry_run: bool = False


@dataclass
class RenameAnalysisResult(AnalysisResult):
    """Resultado de análisis de renombrado"""
    already_renamed: int = 0
    need_renaming: int = 0
    cannot_process: int = 0
    conflicts: int = 0
    files_by_year: Dict = field(default_factory=dict)
    renaming_plan: List[Dict] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


@dataclass
class OrganizationResult(OperationResult):
    """Resultado de operación de organización"""
    files_moved: int = 0
    empty_directories_removed: int = 0
    moved_files: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    folders_created: List[str] = field(default_factory=list)
    dry_run: bool = False


@dataclass
class OrganizationAnalysisResult(AnalysisResult):
    """Resultado de análisis de organización de archivos"""
    root_directory: str = ''
    organization_type: str = 'to_root'
    subdirectories: Dict = field(default_factory=dict)
    root_files: List = field(default_factory=list)
    total_files_to_move: int = 0
    total_size_to_move: int = 0
    potential_conflicts: int = 0
    files_by_type: Dict = field(default_factory=dict)
    move_plan: List = field(default_factory=list)
    folders_to_create: List[str] = field(default_factory=list)


@dataclass
class DuplicateAnalysisResult(AnalysisResult):
    """Resultado de análisis de duplicados (exactos o similares)"""
    mode: str = 'exact'  # 'exact' o 'perceptual'
    groups: List = field(default_factory=list)  # List[DuplicateGroup]
    total_groups: int = 0
    total_duplicates: int = 0  # Para exactos
    total_similar: int = 0  # Para similares
    space_wasted: int = 0  # Para exactos
    space_potential: int = 0  # Para similares
    sensitivity: Optional[int] = None  # Solo para similares
    min_similarity: Optional[float] = None  # Solo para similares
    max_similarity: Optional[float] = None  # Solo para similares

    def __post_init__(self):
        """Post-init validation"""
        super().__post_init__()
        # Normalizar campos según modo
        if self.mode == 'exact':
            self.total_similar = 0
            self.space_potential = 0
        elif self.mode == 'perceptual':
            self.total_duplicates = 0
            self.space_wasted = 0


@dataclass
class DuplicateDeletionResult(DeletionResult):
    """Resultado de eliminación de duplicados"""
    files_kept: int = 0
    keep_strategy: Optional[str] = None
    dry_run: bool = False
    simulated_files_deleted: int = 0
    simulated_space_freed: int = 0


@dataclass
class HeicAnalysisResult(AnalysisResult):
    """Resultado de análisis de duplicados HEIC"""
    duplicate_pairs: List = field(default_factory=list)  # List[DuplicatePair]
    total_pairs: int = 0
    heic_files: int = 0
    jpg_files: int = 0
    total_size: int = 0
    potential_savings_keep_jpg: int = 0
    potential_savings_keep_heic: int = 0
    orphan_heic: List = field(default_factory=list)
    orphan_jpg: List = field(default_factory=list)
    compression_stats: Dict = field(default_factory=dict)
    by_directory: Dict = field(default_factory=dict)
    
    @property
    def total_duplicates(self) -> int:
        """Alias para compatibilidad"""
        return self.total_pairs


@dataclass
class HeicDeletionResult(DeletionResult):
    """Resultado de eliminación de HEIC"""
    format_kept: Optional[str] = None
    dry_run: bool = False
    simulated_files_deleted: int = 0
    simulated_space_freed: int = 0
    
    @property
    def kept_format(self) -> Optional[str]:
        """Alias para compatibilidad"""
        return self.format_kept


@dataclass
class LivePhotoAnalysisResult(AnalysisResult):
    """Resultado de análisis de Live Photos"""
    total_groups: int = 0
    total_images: int = 0
    total_videos: int = 0
    total_size: int = 0
    avg_time_diff: float = 0.0


@dataclass
class LivePhotoCleanupAnalysisResult(AnalysisResult):
    """Resultado de análisis de limpieza de Live Photos"""
    live_photos_found: int = 0
    files_to_delete: List[dict] = field(default_factory=list)
    files_to_keep: List[dict] = field(default_factory=list)
    space_to_free: int = 0
    total_space: int = 0
    cleanup_mode: str = 'keep_image'


@dataclass
class LivePhotoCleanupResult(DeletionResult):
    """Resultado de limpieza de Live Photos"""
    dry_run: bool = False
    simulated_files_deleted: int = 0
    simulated_space_freed: int = 0


@dataclass
class LivePhotoDetectionResult(AnalysisResult):
    """Resultado de detección de Live Photos (usado por AnalysisOrchestrator)"""
    groups: List = field(default_factory=list)  # List[LivePhotoGroup] - evitar import circular
    live_photos_found: int = 0
    total_space: int = 0
    space_to_free: int = 0  # Video space que se liberaría
    
    def __post_init__(self):
        super().__post_init__()
        # Calcular automáticamente desde groups si no se proporciona
        if self.groups:
            self.live_photos_found = len(self.groups)
            if hasattr(self.groups[0], 'total_size'):
                self.total_space = sum(g.total_size for g in self.groups)
                self.space_to_free = sum(g.video_size for g in self.groups)