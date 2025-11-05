# Pixaro Lab - Estructura del Proyecto

Aplicación PyQt6 para gestión de colecciones de fotos/videos (enfoque iOS).

```
pixaro-lab/
├── LICENSE                          # Licencia del proyecto
├── README.md                        # Documentación principal
├── PROJECT_TREE.md                  # Este archivo - estructura del proyecto
├── CHANGELOG.md                     # Registro de cambios del proyecto
├── FASE_2_IMPLEMENTADA.md           # Documentación de implementación Fase 2
├── FASE_3_IMPLEMENTADA.md           # Documentación de implementación Fase 3
├── main.py                          # Punto de entrada de la aplicación
├── config.py                        # Configuración centralizada (rutas, extensiones, constantes)
├── requirements.txt                 # Dependencias Python
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
│   ├── analysis_orchestrator.py     # Coordinador de análisis completo
│   ├── duplicate_detector.py        # Detección de duplicados por hash
│   ├── file_organizer.py            # Organización por fecha/tipo
│   ├── file_renamer.py              # Renombrado según patrón fecha
│   ├── heic_remover.py              # Eliminación de duplicados HEIC/JPG
│   ├── live_photo_cleaner.py        # Limpieza de Live Photos
│   ├── live_photo_detector.py       # Detección de Live Photos
│   └── result_types.py              # Dataclasses de resultados
│
├── ui/                              # Interfaz gráfica PyQt6
│   ├── __init__.py
│   ├── helpers.py                   # Funciones auxiliares de UI
│   ├── main_window.py               # Ventana principal (3 estados)
│   ├── ui_styles.py                 # Estilos CSS legacy (migrado de styles.py)
│   ├── workers.py                   # QThread workers para operaciones async
│   │
│   ├── components/                  # Componentes reutilizables de UI
│   │   └── __init__.py
│   │
│   ├── controllers/                 # Controladores (puente UI ↔ Services)
│   │   ├── __init__.py
│   │   ├── analysis_controller.py   # Control de análisis completo
│   │   ├── duplicates_controller.py # Control de duplicados
│   │   ├── heic_controller.py       # Control de HEIC
│   │   ├── live_photos_controller.py # Control de Live Photos
│   │   ├── organizer_controller.py  # Control de organización
│   │   ├── progress_controller.py   # Control de barra de progreso
│   │   ├── renaming_controller.py   # Control de renombrado
│   │   ├── results_controller.py    # Control de resultados
│   │   └── tab_controller.py        # Control de tabs
│   │
│   ├── dialogs/                     # Diálogos modales
│   │   ├── __init__.py
│   │   ├── about_dialog.py          # Diálogo "Acerca de"
│   │   ├── base_dialog.py           # Clase base para diálogos con backup
│   │   ├── dialog_utils.py          # Utilidades compartidas (open_file, open_folder, show_file_details_dialog)
│   │   ├── exact_duplicates_dialog.py    # Diálogo de duplicados exactos (hash-based)
│   │   ├── similar_duplicates_dialog.py  # Diálogo de duplicados similares (perceptual)
│   │   ├── heic_dialog.py           # Diálogo de HEIC con vista de detalles
│   │   ├── live_photos_dialog.py    # Diálogo de Live Photos
│   │   ├── organization_dialog.py   # Diálogo de organización (3 modos: raíz/mes/WhatsApp)
│   │   ├── renaming_dialog.py       # Diálogo de renombrado con vista de detalles
│   │   └── settings_dialog.py       # Diálogo de configuración
│   │
│   ├── managers/                    # Gestores de recursos
│   │   ├── __init__.py
│   │   └── logging_manager.py       # Gestión de archivos de log
│   │
│   ├── styles/                      # Sistema de diseño centralizado
│   │   ├── __init__.py
│   │   └── design_system.py         # Design System con tokens CSS
│   │
│   ├── tabs/                        # Componentes de pestañas
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
└── utils/                           # Utilidades compartidas
    ├── __init__.py
    ├── callback_utils.py            # Utilidades para callbacks de progreso
    ├── date_utils.py                # Manipulación de fechas
    ├── file_utils.py                # Operaciones con archivos (hash, backup, paths)
    ├── format_utils.py              # Formateo de tamaños, números, etc.
    ├── icons.py                     # Gestión de iconos (qtawesome)
    ├── logger.py                    # Sistema de logging centralizado
    ├── platform_utils.py            # Utilidades específicas de plataforma
    ├── settings_manager.py          # Gestión de configuración persistente (QSettings/JSON)
    └── storage.py                   # Abstracción de almacenamiento (QSettings/JSON)
```

## Arquitectura

**Patrón de 3 capas:**
- **Services**: Lógica de negocio pura, sin dependencias de UI
- **Controllers**: Coordinan entre UI y Services, manejan workers
- **UI**: Componentes visuales PyQt6 (widgets, dialogs, cards)

**Flujo típico:** Analizar → Preview → Confirmar → Ejecutar (con backup opcional)

**Estados de la aplicación:**
1. **Estado 1**: Selector de carpeta y bienvenida
2. **Estado 2**: Análisis con progreso visual (fases con timers)
3. **Estado 3**: Grid de herramientas con cards clicables

**Características técnicas:**
- **Timers de feedback visual**: Cada fase de análisis se muestra por al menos 1 segundo
- **Design System**: Sistema centralizado de estilos CSS con tokens
- **Dataclasses**: Resultados tipados y validados
- **QThread workers**: Operaciones asíncronas sin bloquear UI
- **Backup-first**: Todas las operaciones destructivas incluyen opción de backup

