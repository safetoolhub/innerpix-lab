from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from pathlib import Path
from datetime import datetime
from services.file_metadata_repository_cache import FileInfoRepositoryCache

# ============================================================================
# GENERIC BASE CLASSES (The Core of the Refactor)
# ============================================================================

@dataclass
class BaseResult:
    """Base class for all results (Analysis and Execution)."""
    success: bool = True
    errors: List[str] = field(default_factory=list)
    message: Optional[str] = None
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.success = False

@dataclass
class AnalysisResult(BaseResult):
    """
    Generic result for the Analysis phase.
    Services should populate `data` with specific findings if `items` is not enough.
    """
    items_count: int = 0          # Number of items found/analyzed
    bytes_total: int = 0          # Total size in bytes of relevance
    data: Any = None              # Payload specific to the service (e.g. list of duplicates)

@dataclass
class ExecutionResult(BaseResult):
    """
    Generic result for the Execution phase.
    All execution operations support dry_run mode and backup creation.
    """
    items_processed: int = 0
    bytes_processed: int = 0      # Bytes freed, moved, or renamed
    files_affected: List[Path] = field(default_factory=list) # List of files modified
    backup_path: Optional[Path] = None # If backup was created
    dry_run: bool = False         # Whether this was a dry-run (simulation)


# --- Zero Byte ---
@dataclass
class ZeroByteAnalysisResult(AnalysisResult):
    """Result for zero-byte files detection."""
    files: List[Path] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.items_count and self.files:
            self.items_count = len(self.files)

@dataclass
class ZeroByteExecutionResult(ExecutionResult):
    """Result for zero-byte files deletion."""
    pass

# --- HEIC Service ---
@dataclass
class HEICDuplicatePair:
    """Represents a pair of HEIC + JPG files."""
    heic_path: Path
    jpg_path: Path
    base_name: str
    heic_size: int
    jpg_size: int
    directory: Path
    heic_date: Optional[datetime] = None
    jpg_date: Optional[datetime] = None
    date_source: Optional[str] = None
    date_difference: Optional[float] = None
    
    @property
    def total_size(self) -> int:
        return self.heic_size + self.jpg_size

@dataclass
class HeicAnalysisResult(AnalysisResult):
    """Result for HEIC/JPG duplicate analysis."""
    duplicate_pairs: List[HEICDuplicatePair] = field(default_factory=list)
    rejected_pairs: List[HEICDuplicatePair] = field(default_factory=list)
    heic_files: int = 0
    jpg_files: int = 0
    potential_savings_keep_jpg: int = 0
    potential_savings_keep_heic: int = 0
    
    def __post_init__(self):
        if not self.items_count and self.duplicate_pairs:
            self.items_count = len(self.duplicate_pairs)
        if not self.bytes_total and self.duplicate_pairs:
            self.bytes_total = sum(p.total_size for p in self.duplicate_pairs)

@dataclass
class HeicExecutionResult(ExecutionResult):
    """Result for HEIC/JPG duplicate execution."""
    format_kept: Optional[str] = None  # 'heic' or 'jpg'


# --- Live Photos ---
@dataclass
class LivePhotosAnalysisResult(AnalysisResult):
    """Result for Live Photos detection analysis."""
    groups: List[Any] = field(default_factory=list)  # List of LivePhotoGroup objects
    space_to_free: int = 0  # Space that would be freed by removing videos
    total_space: int = 0  # Total space used by Live Photos (images + videos)
    
    def __post_init__(self):
        if not self.items_count and self.groups:
            self.items_count = len(self.groups)
        if not self.bytes_total and self.total_space:
            self.bytes_total = self.total_space

@dataclass
class LivePhotosExecutionResult(ExecutionResult):
    """Result for Live Photos execution."""
    pass

# --- Rename Service ---
@dataclass
class RenameAnalysisResult(AnalysisResult):
    """Result for file renaming analysis."""
    renaming_plan: List[Dict] = field(default_factory=list)  # List of dicts with 'original_path', 'new_name', etc.
    already_renamed: int = 0
    cannot_process: int = 0
    conflicts: int = 0
    
    def __post_init__(self):
        if not self.items_count and self.renaming_plan:
            self.items_count = len(self.renaming_plan)

@dataclass
class RenameExecutionResult(ExecutionResult):
    """Result for file renaming execution."""
    renamed_files: List[dict] = field(default_factory=list)
    conflicts_resolved: int = 0

# --- Organization Service ---
@dataclass
class OrganizationAnalysisResult(AnalysisResult):
    """Result for file organization analysis."""
    move_plan: List[Any] = field(default_factory=list)  # List of FileMove objects
    root_directory: str = ''
    organization_type: str = 'to_root'  # 'to_root', 'by_month', 'whatsapp_separate'
    folders_to_create: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.items_count and self.move_plan:
            self.items_count = len(self.move_plan)
        if not self.bytes_total and self.move_plan:
             self.bytes_total = sum(m.size for m in self.move_plan)

@dataclass
class OrganizationExecutionResult(ExecutionResult):
    """Result for file organization execution."""
    empty_directories_removed: int = 0
    moved_files: List[str] = field(default_factory=list)
    folders_created: List[str] = field(default_factory=list)



# --- Duplicates (Exact & Similar) ---
@dataclass
class DuplicateGroup:
    hash_value: str
    files: List[Path]
    total_size: int
    file_sizes: List[int] = field(default_factory=list) # Size of each file
    similarity_score: float = 100.0

@dataclass
class DuplicateAnalysisResult(AnalysisResult):
    """Result for duplicate detection analysis (exact or similar)."""
    groups: List[DuplicateGroup] = field(default_factory=list)
    mode: str = 'exact'  # 'exact' or 'perceptual'
    total_duplicates: int = 0
    total_groups: int = 0
    total_files: int = 0
    space_wasted: int = 0
    
    def __post_init__(self):
        if not self.items_count and self.groups:
            self.items_count = len(self.groups)
        if not self.total_groups and self.groups:
            self.total_groups = len(self.groups)
        if not self.bytes_total and self.space_wasted:
            self.bytes_total = self.space_wasted

@dataclass
class DuplicateExecutionResult(ExecutionResult):
    """Result for duplicate deletion execution."""
    files_kept: int = 0
    keep_strategy: Optional[str] = None






# ============================================================================
# DIRECTORY SCANNER RESULT TYPES
# ============================================================================

@dataclass
class DirectoryScanResult:
    """Resultado del escaneo inicial de directorio"""
    total_files: int
    images: List[Path] = field(default_factory=list)
    videos: List[Path] = field(default_factory=list)
    others: List[Path] = field(default_factory=list)
    
   
    # Tamaño total del directorio (calculado durante finalizacion)
    total_size: int = 0
    
    # Desglose por extensiones
    image_extensions: Dict[str, int] = field(default_factory=dict)
    video_extensions: Dict[str, int] = field(default_factory=dict)
    unsupported_extensions: Dict[str, int] = field(default_factory=dict)
    unsupported_files: List[Path] = field(default_factory=list)  # Rutas completas para DEBUG
    
    @property
    def image_count(self) -> int:
        return len(self.images)
    
    @property
    def video_count(self) -> int:
        return len(self.videos)
    
    @property
    def other_count(self) -> int:
        return len(self.others)


@dataclass
class ScanSnapshot:
    """Simple snapshot of scan results for Stage 2 → Stage 3 transition."""
    directory: Path
    scan: DirectoryScanResult