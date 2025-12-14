# Innerpix Lab - Estructura del Proyecto

Aplicación PyQt6 para gestión de colecciones de fotos/videos (enfoque iOS).

**Nota:** Las carpetas `__pycache__/` y los archivos `__init__.py`, así como `tests/` y los elementos de `.gitignore` están excluidos de este árbol para mayor claridad.

```
.
├── dev-tools
│   └── test_custom_spinbox.py
├── fixtures
│   └── cache_test
├── scripts
│   ├── verify_refactor_smoke.py
│   └── verify_ui_imports.py
├── services
│   ├── analysis_orchestrator.py
│   ├── base_service.py
│   ├── directory_scanner.py
│   ├── duplicates_base_service.py
│   ├── duplicates_exact_service.py
│   ├── duplicates_similar_service.py
│   ├── file_info_repository.py      # Cache singleton con persistencia opcional
│   ├── file_metadata.py             # Modelo de datos para metadatos de archivo
│   ├── file_organizer_service.py
│   ├── file_renamer_service.py
│   ├── heic_service.py
│   ├── live_photos_service.py
│   ├── result_types.py
│   └── zero_byte_service.py
├── ui
│   ├── dialogs
│   │   ├── about_dialog.py
│   │   ├── base_dialog.py
│   │   ├── dialog_utils.py
│   │   ├── duplicates_exact_similar_dialog.py
│   │   ├── file_organizer_dialog.py
│   │   ├── file_renamer_dialog.py
│   │   ├── heic_dialog.py
│   │   ├── live_photos_dialog.py
│   │   ├── settings_dialog.py
│   │   ├── duplicates_similar_dialog.py
│   │   ├── duplicates_similar_progress_dialog.py
│   │   └── zero_byte_dialog.py
│   ├── screens
│   │   ├── analysis_phase_widget.py
│   │   ├── base_stage.py
│   │   ├── custom_spinbox.py
│   │   ├── dropzone_widget.py
│   │   ├── main_window.py
│   │   ├── progress_card.py
│   │   ├── stage_1_window.py
│   │   ├── stage_2_window.py
│   │   ├── stage_3_window.py
│   │   ├── summary_card.py
│   │   └── tool_card.py
│   ├── styles
│   │   ├── design_system.py
│   │   └── icons.py
│   ├── workers
│   │   ├── analysis_workers.py
│   │   ├── base_worker.py
│   │   └── execution_workers.py
├── utils
│   ├── callback_utils.py
│   ├── date_utils.py
│   ├── file_utils.py
│   ├── format_utils.py
│   ├── image_loader.py
│   ├── logger.py
│   ├── platform_utils.py
│   ├── screen_utils.py
│   ├── settings_manager.py
│   ├── storage.py
│   └── video_thumbnail.py
├── AGENTS.md
├── config.py
├── LICENSE
├── main.py
├── pytest.ini
├── requirements-dev.txt
└── requirements.txt

13 directories, 63 files
```

## Detalles de módulos clave

### services/file_info_repository.py
**Sistema de cache singleton con gestión inteligente LRU y persistencia opcional**

- **Patrón Singleton**: Acceso único vía `FileInfoRepository.get_instance()`
- **Thread-safe**: Usa `threading.RLock` para acceso concurrente
- **Estrategias de población**:
  - `BASIC`: Solo metadata del filesystem (rápido)
  - `WITH_HASH`: + SHA256 hashes (para duplicados exactos)
  - `WITH_EXIF_IMAGES`: + EXIF solo para imágenes (moderado)
  - `WITH_EXIF_VIDEOS`: + EXIF solo para videos (muy costoso)
  - `WITH_EXIF_ALL`: + EXIF para imágenes y videos
  - `FULL`: Hash + EXIF completo (extremadamente costoso)

- **Gestión de cache LRU**:
  - Scoring basado en costo: EXIF video=20, EXIF imagen=12, hash=5
  - Penalización por edad en el scoring
  - `set_max_entries(max)`: Ajuste dinámico con eviction automático
  - `remove_file(path)`, `remove_files(paths)`: Limpieza tras operaciones destructivas

- **Persistencia opcional** (nuevo en v1.0):
  - `save_to_disk(path)`: Serializa cache completo a JSON con metadata
  - `load_from_disk(path, validate=True)`: Deserializa cache, opcionalmente valida existencia de archivos
  - Formato JSON versionado (version=1) para compatibilidad futura
  - Incluye estadísticas del repositorio en el archivo guardado
  - Thread-safe con manejo de errores robusto

- **Auto-fetch**: `get_file_metadata(path, auto_fetch=True)`, `get_hash(path, auto_fetch=True)`
- **Estadísticas**: `get_stats()` → `RepositoryStats` con hit_rate, cache_misses, etc.
- **Magic methods**: `len(repo)`, `path in repo`, `repo[path]`

### services/file_metadata.py
**Modelo de datos inmutable para metadatos de archivo**

- Dataclass con atributos: path, size, mtime, hash, exif, access_count, last_access
- Serialización: `to_dict()` / `from_dict(data)` para persistencia
- Propiedades helper: `is_image`, `is_video`, `file_type`

### services/duplicates_similar_service.py
**Sistema de análisis de similitud con dos fases**

- **Fase 1**: `analyze_initial()` - Cálculo costoso de perceptual hash (~5 min para 40k archivos)
- **Fase 2**: `get_groups(sensitivity)` - Clustering rápido con sensibilidad ajustable (<1 seg)
- **SimilarFilesAnalysis**: Container para hashes pre-calculados, permite re-clustering en tiempo real
- **Persistencia**: `save_to_file()` / `load_from_file()` para recarga instantánea de cache
- **Hamming distance**: Comparación de hash perceptual de 64 bits
- **Escala de sensibilidad**: 30-100% (30=permisivo, 100=solo idénticos, 85=recomendado)

### ui/dialogs/duplicates_similar_dialog.py
**Dialog con ajuste dinámico de sensibilidad**

- Slider de sensibilidad con re-clustering en tiempo real
- Vista previa de imágenes en grupos
- Paginación para grandes conjuntos de duplicados
- Estrategias de eliminación: mantener más nueva, más vieja, mejor calidad
