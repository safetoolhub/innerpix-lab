"""
Metadata Cache Service (Pure File System Info)

Stores ONLY file system attributes and metadata. 
No service-specific logic (e.g., no "duplicate" flags, no "renaming" plans).
"""
import os
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
import threading

@dataclass
class FileMetadata:
    """
    Pure file metadata.
    """
    path: Path
    size: int
    ctime: float # Creation time (timestamp)
    mtime: float # Modification time (timestamp)
    atime: float # Access time (timestamp)
    
    # Extended Metadata (Lazy loaded or populated during scan)
    exif_data: Dict[str, Any] = field(default_factory=dict)
    
    # Hash (Lazy loaded)
    sha256: Optional[str] = None
    
    @property
    def extension(self) -> str:
        return self.path.suffix.lower()

    @property
    def exif_date_time_original(self) -> Optional[str]:
        return self.exif_data.get('DateTimeOriginal')

    @property
    def exif_create_date(self) -> Optional[str]:
        return self.exif_data.get('CreateDate')
        
    @property
    def exif_date_digitized(self) -> Optional[str]:
        return self.exif_data.get('DateTimeDigitized')

    @property
    def sha256_hash(self) -> Optional[str]:
        return self.sha256



class FileMetadataCache:
    """
    Central repository for file metadata.
    Thread-safe.
    """
    def __init__(self):
        self._cache: Dict[Path, FileMetadata] = {}
        self._lock = threading.RLock()
        self._max_entries = 100000 
        self._enabled = True
        self._hits = 0
        self._misses = 0

    
    def add_file(self, path: Path) -> FileMetadata:
        """
        Adds a file to the cache, reading basic stats from disk.
        """
        try:
            stat = path.stat()
            meta = FileMetadata(
                path=path,
                size=stat.st_size,
                ctime=stat.st_ctime,
                mtime=stat.st_mtime,
                atime=stat.st_atime
            )
            with self._lock:
                self._cache[path] = meta
            return meta
        except Exception as e:
            # If file doesn't exist or permission error, we might want to log or skip
            # For now, we propagate or return None? 
            # Better to raise so caller knows it failed.
            raise e

    def get_metadata(self, path: Path) -> Optional[FileMetadata]:
        with self._lock:
            if path in self._cache:
                self._hits += 1
                return self._cache[path]
            self._misses += 1
            return None

    def set_basic_metadata(self, path: Path, size: int, ctime: float, mtime: float, atime: float, file_type: str = "OTHER"):
        """Sets basic metadata directly (used by orchestrator scan)"""
        meta = FileMetadata(
            path=path,
            size=size,
            ctime=ctime,
            mtime=mtime,
            atime=atime
        )
        # We can store file_type in exif_data or ignore it if not in dataclass
        # FileMetadata currently doesn't have file_type field, so we ignore it or add it if needed.

        with self._lock:
            self._cache[path] = meta

    def get_hash(self, path: Path) -> str:
        """
        Returns cached hash or calculates it.
        """
        meta = self.get_metadata(path)
        if not meta:
            meta = self.add_file(path)
        
        if meta.sha256:
            return meta.sha256
        
        # Calculate hash
        sha256 = self._calculate_sha256(path)
        with self._lock:
            meta.sha256 = sha256
        return sha256

    def set_hash(self, path: Path, hash_val: str):
        """Sets the hash for a file directly."""
        meta = self.get_metadata(path)
        if meta:
            with self._lock:
                meta.sha256 = hash_val

    def _calculate_sha256(self, path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def set_exif(self, path: Path, exif_data: Dict[str, Any]):
        meta = self.get_metadata(path)
        if meta:
            with self._lock:
                meta.exif_data = exif_data

    def get_files_by_size(self) -> Dict[int, list[FileMetadata]]:
        """Helper to group files by size (useful for duplicate detection)."""
        by_size = {}
        with self._lock:
            for meta in self._cache.values():
                if meta.size not in by_size:
                    by_size[meta.size] = []
                by_size[meta.size].append(meta)
        return by_size
    
    def get_all_files(self) -> list[FileMetadata]:
        with self._lock:
            return list(self._cache.values())

    def update_max_entries(self, total_files: int):
        """Updates internal max entries limit based on file count (placeholder for now)"""
        # In a real implementation this might trigger cleanup if limit exceeded
        self._max_entries = max(self._max_entries, total_files + 1000)

    def set_all_dates(self, path: Path, all_dates: Dict[str, Any]):
        """Sets all extracted dates (including EXIF) for a file"""
        # Mapping from date_utils keys to what we expect in exif_data if needed
        # But FileMetadata stores exif_data dict directly.
        # Let's populate exif_data with what we found
        meta = self.get_metadata(path)
        if meta:
            with self._lock:
                # We can store the whole dict
                meta.exif_data = all_dates.copy() 

    def get_all_dates(self, path: Path) -> Dict[str, Any]:
        """Returns all cached dates (including EXIF) for a file"""
        meta = self.get_metadata(path)
        if meta and meta.exif_data:
            return meta.exif_data.copy()
        return {} 


    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_access = self._hits + self._misses
            hit_rate = (self._hits / total_access * 100) if total_access > 0 else 0.0
            return {
                'size': len(self._cache),
                'max_entries': self._max_entries,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate
            }

    def log_stats(self):
        """Logs current cache statistics"""
        stats = self.get_stats()
        # We need a logger. We can accept one or use print/standard logging if not injected.
        # But this class doesn't have a logger.
        # Let's just print to logging info if possible or accept a logger?
        # Or better, just print formatted stats to a logger if we can import it.
        # Ideally Orchestrator should log stats from get_stats, but to fix the error quickly:
        import logging
        logger = logging.getLogger("FileMetadataCache")
        logger.info(f"Cache Stats: Size={stats['size']}, Max={stats['max_entries']}, "
                    f"Hits={stats['hits']}, Misses={stats['misses']}, Rate={stats['hit_rate']:.1f}%")

    def clear(self):
        with self._lock:
            self._cache.clear()

# Alias for backward compatibility
MetadataCache = FileMetadataCache
