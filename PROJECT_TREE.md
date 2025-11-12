# Pixaro Lab - Estructura del Proyecto

Aplicación PyQt6 para gestión de colecciones de fotos/videos (enfoque iOS).

```
pixaro-lab/
├── LICENSE                          # Licencia del proyecto
├── README.md                        # Documentación principal
├── PROJECT_TREE.md                  # Este archivo - estructura del proyecto
├── CHANGELOG.md                     # Registro de cambios del proyecto
├── FASE_2_IMPLEMENTADA.md           # Documentación de implementación Fase 2
├── FASE_2_REFACTORIZADA.md          # Documentación de refactorización Fase 2
├── FASE_3_IMPLEMENTADA.md           # Documentación de implementación Fase 3
├── FASE_4_IMPLEMENTADA.md           # Documentación de implementación Fase 4
├── Funcionalidades.txt              # Lista de funcionalidades implementadas
├── PROMPT _MVP2.md                  # Documentación del MVP2
├── TODO.txt                         # Lista de tareas pendientes
├── TOOLTIPS.md                      # Documentación de tooltips de UI
├── main.py                          # Punto de entrada de la aplicación
├── config.py                        # Configuración centralizada (rutas, extensiones, constantes)
├── requirements.txt                 # Dependencias Python
├── requirements-dev.txt             # Dependencias para desarrollo y testing
├── pytest.ini                       # Configuración de pytest
├── run_tests.sh                     # Script para ejecutar tests
│
├── .github/
│   └── copilot-instructions.md      # Instrucciones para GitHub Copilot
│
├── .vscode/
│   ├── keybindings.json             # Atajos de teclado personalizados
│   ├── launch.json                  # Configuración de debug
│   ├── settings.json                # Configuración del workspace
│   └── tasks.json                   # Tareas personalizadas
│
<!-- Nota: La carpeta `docs/` contiene notas técnicas y personales del autor y no se incluye en este árbol simplificado. -->
├── services/                        # Lógica de negocio (sin dependencias UI)
│   ├── __init__.py
│   ├── analysis_orchestrator.py     # Coordinador de análisis completo (100% PyQt6-free)
│   ├── base_service.py              # ✅ Clase base: logging, backup, progress, format
│   ├── base_detector_service.py     # ✅ Clase base detectores: execute() unificado
│   ├── exact_copies_detector.py     # ✅ Detección copias exactas (SHA256)
│   ├── similar_files_detector.py    # Detección archivos similares (perceptual hash)
│   ├── file_organizer_service.py    # ✅ Organización por fecha/tipo
│   ├── file_renamer_service.py      # ✅ Renombrado según patrón fecha
│   ├── heic_remover_service.py      # ✅ Eliminación duplicados HEIC/JPG
│   ├── live_photo_service.py        # ✅ Servicio unificado Live Photos
│   ├── result_types.py              # ✅ Dataclasses 100% tipados (NO raw dicts)
│   ├── service_utils.py             # Utilidades compartidas entre servicios
│   └── view_models.py               # View Models para separación UI/Lógica
│   
├── ui/                              # Interfaz gráfica PyQt6
│   ├── __init__.py
│   ├── helpers.py                   # Funciones auxiliares de UI
│   ├── main_window.py               # Ventana principal (3 stages)
│   ├── workers.py                   # QThread workers para operaciones async
│   │
│   ├── stages/                      # Arquitectura de stages (State pattern)
│   │   ├── __init__.py
│   │   ├── base_stage.py            # Clase base para todos los stages
│   │   ├── stage_1_window.py        # Stage 1: Selector de carpeta y bienvenida
│   │   ├── stage_2_window.py        # Stage 2: Análisis con progreso
│   │   └── stage_3_window.py        # Stage 3: Grid de herramientas
│   │
│   ├── components/                  # Componentes reutilizables de UI (reservado)
│   │   └── __init__.py
│   │
│   ├── dialogs/                     # Diálogos modales
│   │   ├── __init__.py
│   │   ├── about_dialog.py          # Diálogo "Acerca de"
│   │   ├── base_dialog.py           # Clase base para diálogos con backup
│   │   ├── dialog_utils.py          # Utilidades compartidas (open_file, open_folder, show_file_details_dialog)
│   │   ├── exact_copies_dialog.py   # Diálogo de copias exactas (SHA256-based)
│   │   ├── heic_dialog.py           # Diálogo de HEIC con vista de detalles
│   │   ├── live_photos_dialog.py    # Diálogo de Live Photos
│   │   ├── organization_dialog.py   # Diálogo de organización (3 modos: raíz/mes/WhatsApp)
│   │   ├── renaming_dialog.py       # Diálogo de renombrado con vista de detalles
│   │   ├── settings_dialog.py       # Diálogo de configuración
│   │   ├── similar_files_dialog.py  # Diálogo de archivos similares (perceptual hash)
│   │   └── similar_files_progress_dialog.py  # Diálogo de progreso para análisis de similares
│   │
│   ├── managers/                    # Gestores de recursos
│   │   ├── __init__.py
│   │   └── logging_manager.py       # Gestión de archivos de log
│   │
│   ├── styles/                      # Sistema de diseño centralizado
│   │   ├── __init__.py
│   │   └── design_system.py         # Design System con tokens CSS + constantes legacy migradas
│   │
│   ├── tabs/                        # Componentes de pestañas (reservado)
│   │   └── __init__.py
│   │
│   ├── validators/                  # Validadores de entrada
│   │   └── directory_validator.py   # Validación de directorios
│   │
│   └── widgets/                     # Widgets individuales reutilizables
│       ├── __init__.py
│       ├── analysis_phase_widget.py # Widget de fases de análisis
│       ├── dropzone_widget.py       # Área para arrastrar y soltar carpetas
│       ├── progress_card.py         # Card de progreso con barra
│       ├── summary_card.py          # Card de resumen de análisis
│       └── tool_card.py             # Cards clicables para herramientas
│
├── utils/                           # Utilidades compartidas
│   ├── __init__.py
│   ├── callback_utils.py            # Utilidades para callbacks de progreso
│   ├── date_utils.py                # Manipulación de fechas
│   ├── decorators.py                # Decoradores (@deprecated, etc.)
│   ├── file_utils.py                # Operaciones con archivos (hash, backup, paths)
│   ├── format_utils.py              # Formateo de tamaños, números, etc.
│   ├── icons.py                     # Gestión de iconos (qtawesome)
│   ├── logger.py                    # ✅ Logging thread-safe (RLock, log_block)
│   ├── platform_utils.py            # Utilidades específicas de plataforma
│   ├── screen_utils.py              # Detección multiplataforma de resolución de pantalla
│   ├── settings_manager.py          # Gestión de configuración persistente (QSettings/JSON)
│   └── storage.py                   # Abstracción de almacenamiento (QSettings/JSON)
│
└── tests/                           # Suite de tests automatizados
    ├── __init__.py
    └── test_window_size.py          # Tests para lógica de tamaño de ventana
```


## Arquitectura

**Patrón de 3 capas (simplificado):**
- **Services**: Lógica de negocio pura, sin dependencias de UI
- **UI**: Componentes visuales PyQt6 (widgets, dialogs, cards) con workers para operaciones async
- **Utils**: Utilidades compartidas, incluyendo detección multiplataforma de pantalla

**Flujo típico:** Analizar → Preview → Confirmar → Ejecutar (con backup opcional)

**Stages de la aplicación:**
1. **Stage 1**: Selector de carpeta y bienvenida
2. **Stage 2**: Análisis con progreso visual (etapas con timers)
3. **Stage 3**: Grid de herramientas con cards clicables

**Características técnicas:**
- **Timers de feedback visual**: Cada fase de análisis se muestra por al menos 1 segundo
- **Design System**: Sistema centralizado de estilos CSS con tokens + constantes legacy migradas
- **Dataclasses**: Resultados tipados y validados
- **QThread workers**: Operaciones asíncronas sin bloquear UI
- **Backup-first**: Todas las operaciones destructivas incluyen opción de backup
- **Multiplataforma**: Detección de resolución nativa para Windows/Linux/macOS
- **Testing básico**: Suite inicial de tests con pytest

## Testing

**Herramientas de calidad:**
- **pytest**: Framework de testing con parametrización
- **black**: Formateo automático de código (planeado)
- **isort**: Ordenamiento de imports (planeado)
- **flake8**: Linting de código (planeado)

**Ejecución de tests:**
```bash
./run_tests.sh              # Ejecutar todos los tests
pytest                      # Ejecutar con pytest directamente
```
