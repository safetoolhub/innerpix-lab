"""
Tipos de resultados estandarizados para servicios de Innerpix Lab

Centraliza TODAS las dataclasses de resultados.
Define dataclasses consistentes para resultados de análisis y operaciones.

Jerarquía de clases:
    - BaseResult: Clase base con campos universales (success, errors, message)
    - BackupMixin: Para operaciones que crean backup
    - DryRunMixin: Para modo simulación básico
    - DryRunStatsMixin: Extiende DryRunMixin con estadísticas de simulación
    - FileListMixin: Para operaciones que rastrean archivos eliminados
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime, timedelta


# === Base Classes and Mixins ===
@dataclass
class BaseResult:
    """
    Clase base para todos los resultados.
    
    Proporciona campos universales y métodos comunes para manejo de errores.
    """
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
        """Añade un error a la lista y marca success=False"""
        self.errors.append(error)
        if self.success:
            self.success = False


@dataclass
class BackupMixin:
    """Mixin para operaciones que soportan creación de backup"""
    backup_path: Optional[str] = None


@dataclass
class DryRunMixin:
    """Mixin para operaciones que soportan modo simulación"""
    dry_run: bool = False


@dataclass
class DryRunStatsMixin(DryRunMixin):
    """
    Mixin para operaciones con estadísticas de simulación.
    
    Extiende DryRunMixin añadiendo campos para rastrear operaciones simuladas.
    """
    simulated_files_deleted: int = 0
    simulated_space_freed: int = 0


@dataclass
class FileListMixin:
    """Mixin para operaciones que rastrean lista de archivos eliminados"""
    deleted_files: List[str] = field(default_factory=list)


# === Specialized Base Classes ===
@dataclass
class AnalysisResult(BaseResult):
    """Resultado base de análisis"""
    total_files: int = 0


@dataclass
class DeletionResult(BaseResult, BackupMixin, FileListMixin):
    """Resultado de operación de eliminación con backup y tracking de archivos"""
    files_deleted: int = 0
    space_freed: int = 0


# === File Renamer Service ===
@dataclass
class RenameDeletionResult(BaseResult, BackupMixin, DryRunMixin):
    """Resultado de operación de renombrado"""
    files_renamed: int = 0
    renamed_files: List[dict] = field(default_factory=list)
    conflicts_resolved: int = 0


@dataclass
class RenameAnalysisResult(AnalysisResult):
    """Resultado de análisis de renombrado"""
    already_renamed: int = 0
    cannot_process: int = 0
    conflicts: int = 0
    files_by_year: Dict = field(default_factory=dict)
    renaming_plan: List[Dict] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)

    @property
    def need_renaming(self) -> int:
        """Número de archivos que necesitan ser renombrados (calculado)"""
        return len(self.renaming_plan)


# === File Organizer Service ===
@dataclass
class OrganizationDeletionResult(BaseResult, BackupMixin, DryRunMixin):
    """Resultado de operación de organización"""
    files_moved: int = 0
    empty_directories_removed: int = 0
    moved_files: List[str] = field(default_factory=list)
    folders_created: List[str] = field(default_factory=list)


@dataclass
class OrganizationAnalysisResult(AnalysisResult):
    """Resultado de análisis de organización de archivos"""
    root_directory: str = ''
    organization_type: str = 'to_root'
    subdirectories: Dict = field(default_factory=dict)
    root_files: List = field(default_factory=list)
    total_size_to_move: int = 0
    potential_conflicts: int = 0
    files_by_type: Dict = field(default_factory=dict)
    move_plan: List = field(default_factory=list)
    folders_to_create: List[str] = field(default_factory=list)
    group_by_source: bool = False
    group_by_type: bool = False
    date_grouping_type: Optional[str] = None

    @property
    def total_files_to_move(self) -> int:
        """Número total de archivos a mover (calculado desde move_plan)"""
        return len(self.move_plan)


# === Duplicates Services (Exact & Similar) ===
@dataclass
class DuplicateGroup:
    """
    Grupo de archivos duplicados (exactos o similares).
    
    Usado por DuplicatesExactService y DuplicatesSimilarService.
    """
    hash_value: str  # SHA256 hash o perceptual hash
    files: List[Path]
    total_size: int
    similarity_score: float = 100.0  # Copias exactas = 100%, similares = variable


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
class DuplicateDeletionResult(DeletionResult, DryRunStatsMixin):
    """Resultado de eliminación de duplicados"""
    files_kept: int = 0
    keep_strategy: Optional[str] = None


# === HEIC Service ===
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
    def time_difference(self) -> Optional[timedelta]:
        """Diferencia de tiempo entre archivos"""
        if self.heic_date and self.jpg_date:
            return abs(self.heic_date - self.jpg_date)
        return None


@dataclass
class HeicAnalysisResult(AnalysisResult):
    """Resultado de análisis de duplicados HEIC"""
    duplicate_pairs: List = field(default_factory=list)  # List[DuplicatePair]
    heic_files: int = 0
    jpg_files: int = 0
    total_size: int = 0
    potential_savings_keep_jpg: int = 0
    potential_savings_keep_heic: int = 0
    orphan_heic: List = field(default_factory=list)
    orphan_jpg: List = field(default_factory=list)
    by_directory: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Calcular total_files desde heic_files + jpg_files si no se proporcionó"""
        super().__post_init__()
        if self.total_files == 0 and (self.heic_files > 0 or self.jpg_files > 0):
            object.__setattr__(self, 'total_files', self.heic_files + self.jpg_files)
    
    @property
    def total_pairs(self) -> int:
        """Número total de pares duplicados (calculado)"""
        return len(self.duplicate_pairs)
    
    @property
    def total_duplicates(self) -> int:
        """Alias para compatibilidad con otros servicios"""
        return self.total_pairs


@dataclass
class HeicDeletionResult(DeletionResult, DryRunStatsMixin):
    """Resultado de eliminación de HEIC"""
    format_kept: Optional[str] = None


# === Live Photos Service ===
@dataclass
class LivePhotoCleanupAnalysisResult(AnalysisResult):
    """Resultado de análisis de limpieza de Live Photos"""
    files_to_delete: List[dict] = field(default_factory=list)
    files_to_keep: List[dict] = field(default_factory=list)
    space_to_free: int = 0
    total_space: int = 0
    cleanup_mode: str = 'keep_image'
    groups: List = field(default_factory=list)  # Lista de LivePhotoGroup para compatibilidad con UI

    @property
    def live_photos_found(self) -> int:
        """Número de Live Photos encontradas (calculado desde groups)"""
        return len(self.groups)


@dataclass
class LivePhotoCleanupDeletionResult(DeletionResult, DryRunStatsMixin):
    """Resultado de limpieza de Live Photos"""
    pass


@dataclass
class LivePhotoDetectionResult(AnalysisResult):
    """Resultado de detección de Live Photos (usado por AnalysisOrchestrator)"""
    groups: List = field(default_factory=list)  # List[LivePhotoGroup] - evitar import circular
    
    @property
    def live_photos_found(self) -> int:
        """Número de Live Photos encontradas (calculado)"""
        return len(self.groups)
    
    @property
    def total_space(self) -> int:
        """Espacio total ocupado por Live Photos (calculado)"""
        if not self.groups or not hasattr(self.groups[0], 'total_size'):
            return 0
        return sum(g.total_size for g in self.groups)
    
    @property
    def space_to_free(self) -> int:
        """Espacio que se liberaría eliminando videos (calculado)"""
        if not self.groups or not hasattr(self.groups[0], 'video_size'):
            return 0
        return sum(g.video_size for g in self.groups)


# === Zero Byte Service ===
@dataclass
class ZeroByteAnalysisResult(AnalysisResult):
    """Resultado de análisis de archivos de 0 bytes"""
    files: List[Path] = field(default_factory=list)
    
    @property
    def zero_byte_files_found(self) -> int:
        """Número de archivos de 0 bytes encontrados (calculado)"""
        return len(self.files)


@dataclass
class ZeroByteDeletionResult(DeletionResult, DryRunStatsMixin):
    """Resultado de eliminación de archivos de 0 bytes"""
    pass