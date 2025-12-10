# Pixaro Lab - Estructura del Proyecto

Aplicación PyQt6 para gestión de colecciones de fotos/videos (enfoque iOS).

**Nota:** Las carpetas `__pycache__/` y los archivos `__init__.py` están excluidos de este árbol para mayor claridad (ignorados por .gitignore en el caso de `__pycache__/`).

```
pixaro-lab/
├── .github/copilot-instructions.md  # Instrucciones para GitHub Copilot
├── .gitignore                       # Archivos ignorados por Git
├── LICENSE                          # Licencia del proyecto
├── config.py                        # Configuración centralizada (rutas, extensiones, constantes)
├── main.py                          # Punto de entrada de la aplicación
├── pytest.ini                       # Configuración de pytest
├── requirements-dev.txt             # Dependencias para desarrollo y testing
├── requirements.txt                 # Dependencias Python
│
├── dev-tools/                       # Herramientas de desarrollo
│   └── test_custom_spinbox.py       # Script de prueba para CustomSpinBox
│
├── docs/                            # Documentación
│   ├── Funcionalidades.md           # Descripción de funcionalidades
│   ├── PROJECT_TREE.md              # Este archivo - estructura del proyecto
│   └── TODO.txt                     # Lista de tareas pendientes
│
├── services/                        # Lógica de negocio (sin dependencias UI)
│   ├── analysis_orchestrator.py     # Coordinador de análisis completo (100% PyQt6-free)
│   ├── base_detector_service.py     # Clase base detectores: execute() unificado
│   ├── base_service.py              # Clase base: logging, backup, progress, format
│   ├── exact_copies_detector.py     # Detección copias exactas (SHA256)
│   ├── file_organizer_service.py    # Organización por fecha/tipo
│   ├── file_renamer_service.py      # Renombrado según patrón fecha
│   ├── heic_remover_service.py      # Eliminación duplicados HEIC/JPG
│   ├── live_photos_service.py       # Servicio unificado Live Photos
│   ├── metadata_cache.py            # Caché thread-safe de metadatos (hashes SHA256, EXIF, stats)
│   ├── result_types.py              # Dataclasses 100% tipados (NO raw dicts)
│   ├── similar_files_detector.py    # Detección archivos similares (perceptual hash)
│   ├── view_models.py               # View Models para separación UI/Lógica
│   └── zero_byte_service.py         # Servicio para archivos de 0 bytes
│   
├── ui/                              # Interfaz gráfica PyQt6
│   ├── main_window.py               # Ventana principal (3 stages)
│   ├── workers.py                   # QThread workers para operaciones async
│   │
│   ├── dialogs/                     # Diálogos modales
│   │   ├── about_dialog.py          # Diálogo "Acerca de"
│   │   ├── base_dialog.py           # Clase base para diálogos con backup
│   │   ├── dialog_utils.py          # Utilidades compartidas (open_file, open_folder, show_file_details_dialog)
│   │   ├── exact_copies_dialog.py   # Diálogo de copias exactas (SHA256-based)
│   │   ├── file_organizer_dialog.py # Diálogo de organización (3 modos: raíz/mes/WhatsApp)
│   │   ├── file_renaming_dialog.py  # Diálogo de renombrado con vista de detalles
│   │   ├── heic_remover_dialog.py   # Diálogo de HEIC con vista de detalles
│   │   ├── live_photos_dialog.py    # Diálogo de Live Photos
│   │   ├── settings_dialog.py       # Diálogo de configuración
│   │   ├── similar_files_dialog.py  # Diálogo de archivos similares (perceptual hash)
│   │   ├── similar_files_progress_dialog.py  # Diálogo de progreso para análisis de similares
│   │   └── zero_byte_dialog.py      # Diálogo para archivos de 0 bytes
│   │
│   ├── stages/                      # Arquitectura de stages (State pattern)
│   │   ├── base_stage.py            # Clase base para todos los stages
│   │   ├── stage_1_window.py        # Stage 1: Selector de carpeta y bienvenida
│   │   ├── stage_2_window.py        # Stage 2: Análisis con progreso
│   │   └── stage_3_window.py        # Stage 3: Grid de herramientas
│   │
│   ├── styles/                      # Sistema de diseño centralizado
│   │   └── design_system.py         # Design System con tokens CSS + constantes legacy migradas
│   │
│   └── widgets/                     # Widgets individuales reutilizables
│       ├── analysis_phase_widget.py # Widget de fases de análisis
│       ├── custom_spinbox.py        # Widget personalizado para spinbox
│       ├── dropzone_widget.py       # Área para arrastrar y soltar carpetas
│       ├── progress_card.py         # Card de progreso con barra
│       ├── summary_card.py          # Card de resumen de análisis
│       └── tool_card.py             # Cards clicables para herramientas
│
├── utils/                           # Utilidades compartidas
│   ├── callback_utils.py            # Utilidades para callbacks de progreso
│   ├── date_utils.py                # Manipulación de fechas con priorización inteligente (EXIF → Filename → Video → FS)
│   ├── file_utils.py                # Operaciones con archivos (hash, backup, paths)
│   ├── format_utils.py              # Formateo de tamaños, números, etc.
│   ├── icons.py                     # Gestión de iconos (qtawesome)
│   ├── image_loader.py              # Carga de imágenes
│   ├── logger.py                    # Logging thread-safe con dual logging opcional (FILE_DELETED:)
│   ├── platform_utils.py            # Utilidades específicas de plataforma
│   ├── screen_utils.py              # Detección multiplataforma de resolución de pantalla
│   ├── settings_manager.py          # Gestión de configuración persistente (QSettings/JSON + dual_log_enabled)
│   ├── storage.py                   # Abstracción de almacenamiento (QSettings/JSON)
│   └── video_thumbnail.py           # Generación de miniaturas de video
│
└── tests/                           # Suite de tests automatizados
    ├── conftest.py                  # Fixtures compartidos (temp_dir, create_test_image, etc.)
    ├── README.md                    # Guía de testing con ejemplos y best practices
    ├── test_dev_cache.py
    ├── test_find_duplicates_bug.py
    ├── test_livephotos_bug_reproduction.py
    ├── test_multiple_images_one_video.py
    ├── test_window_size.py
    ├── test_zero_byte_service.py
    ├── integration/                 # Tests de integración
    ├── performance/                 # Tests de rendimiento (datasets grandes)
    │   └── test_large_dataset.py
    ├── ui/                          # Tests de UI (mínimos, requieren PyQt6)
    │   └── test_file_organizer_dialog.py
    └── unit/                        # Tests unitarios
        ├── README_DYNAMIC_CONFIG_TESTS.md
        ├── test_dynamic_config.py
        ├── test_live_photo_video_size_warning.py
        ├── test_similar_files_incremental.py
        ├── services/                # Tests de servicios
        │   ├── README_ORCHESTRATOR_TESTS.md
        │   ├── test_analysis_orchestrator.py
        │   ├── test_base_detector_missing_files.py
        │   ├── test_base_service_backup.py
        │   ├── test_exact_copies_detector.py
        │   ├── test_file_organizer_combined.py
        │   ├── test_file_organizer_service.py
        │   ├── test_heic_remover_missing_files.py
        │   ├── test_heic_remover_service.py
        │   ├── test_live_photos_deduplication.py
        │   ├── test_live_photos_missing_files.py
        │   ├── test_live_photos_multiple_formats.py
        │   ├── test_live_photos_multiple_images.py
        │   ├── test_live_photos_service.py
        │   ├── test_metadata_cache.py
        │   └── test_similar_files_detector.py
        ├── ui/
        │   ├── test_live_photos_deduplication.py
        │   └── test_live_photos_dialog_counts.py
        └── utils/                   # Tests de utilidades
            ├── test_callback_utils.py
            ├── test_date_utils.py
            ├── test_file_utils.py
            ├── test_format_utils.py
            ├── test_log_rotation_production.py
            ├── test_log_rotation.py
            ├── test_platform_utils.py
            ├── test_screen_utils.py
            └── test_storage.py
```
