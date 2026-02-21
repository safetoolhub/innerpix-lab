# Changelog

All notable changes to InnerPix Lab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.0-beta] - 2026-02-17

### Added
- **8 analysis tools** organized in 3 categories:
  - **Cleanup & Space**: Zero-byte files, Live Photos, HEIC/JPG duplicates, Exact copies (SHA256)
  - **Visual Detection**: Visually identical copies (perceptual hash), Similar files (70-95% similarity slider)
  - **Organization**: Smart file organizer (date-based structure), Complete file renamer (YYYYMMDD_HHMMSS)
- **Multi-phase scanner** with 6 incremental stages (file classification, filesystem metadata, SHA256 hashing, image EXIF, video EXIF, best date calculation)
- **FileMetadata singleton cache** with LRU eviction, thread-safe access, and optional disk persistence
- **3-stage UI workflow**: Folder selection → Analysis progress → Tools grid
- **Internationalization**: Full Spanish and English support (898 translation keys each) with runtime language switching
- **Cross-platform support**: Linux, Windows, macOS with platform-specific file operations
- **Privacy-first architecture**: 100% local processing, no cloud, no telemetry
- **Backup-first policy**: All destructive operations offer backup creation and dry-run simulation
- **Settings system**: Configurable analysis options, log levels, language, worker threads
- **Adaptive performance**: Dynamic worker allocation based on CPU cores and available RAM
- **Perceptual hash engine**: phash/dhash/ahash algorithms with configurable hash size and real-time re-clustering
- **Professional logging**: Dual-log system (main + warnings-only), grep-friendly FILE_DELETED tracking

### Technical
- PyQt6 desktop application with strict UI/logic separation
- 713+ passing tests (unit, integration, performance)
- Python 3.12+ with comprehensive type hints
- Automated release pipeline with GitHub Actions (Linux .deb/.rpm, Windows installer, macOS DMG)

[Unreleased]: https://github.com/safetoolhub/innerpix-lab/compare/v0.8.0-beta...HEAD
[0.8.0-beta]: https://github.com/safetoolhub/innerpix-lab/releases/tag/v0.8.0-beta
