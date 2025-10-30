# Pixaro Lab - Estructura del Proyecto

Aplicación PyQt6 para gestión de colecciones de fotos/videos (enfoque iOS).

```
pixaro-lab/
├── LICENSE                          # Licencia del proyecto
├── README.md                        # Documentación principal
├── PROJECT_TREE.md                  # Este archivo - estructura del proyecto
├── main.py                          # Punto de entrada de la aplicación
├── config.py                        # Configuración centralizada (rutas, extensiones, constantes)
├── requirements.txt                 # Dependencias Python
├── run_tests.py                     # Script para ejecutar tests
│
├── .github/
│   └── copilot-instructions.md      # Instrucciones para GitHub Copilot
│
├── docs/                            # Documentación técnica
│   ├── COLORS_REFERENCE.md          # Referencia de colores de la UI
│   ├── GUIA_CONFIGURACION.md        # Guía de configuración para usuarios
│   ├── LOGGING_CONVENTIONS.md       # Convenciones de logging
│   ├── MAX_WORKERS_IMPLEMENTATION.md # Implementación de workers paralelos
│   ├── REFACTOR_SETTINGS_SUMMARY.md # Resumen de refactorización de settings
│   └── TODO.txt                     # Tareas pendientes
│
├── services/                        # Lógica de negocio (sin dependencias UI)
│   ├── __init__.py
│   ├── duplicate_detector.py        # Detección de duplicados por hash
│   ├── file_organizer.py            # Organización por fecha/tipo
│   ├── file_renamer.py              # Renombrado según patrón fecha
│   ├── heic_remover.py              # Eliminación de duplicados HEIC/JPG
│   ├── live_photo_cleaner.py        # Limpieza de Live Photos
│   ├── live_photo_detector.py       # Detección de Live Photos
│   └── result_types.py              # Dataclasses de resultados
│
├── tests/                           # Tests unitarios
│   ├── __init__.py
│   ├── README.md
│   └── test_file_renamer.py
│
├── ui/                              # Interfaz gráfica PyQt6
│   ├── __init__.py
│   ├── helpers.py                   # Funciones auxiliares de UI
│   ├── main_window.py               # Ventana principal
│   ├── styles.py                    # Estilos CSS para widgets
│   ├── workers.py                   # QThread workers para operaciones async
│   │
│   ├── components/                  # Componentes reutilizables de UI
│   │   ├── __init__.py
│   │   ├── action_buttons.py        # Botones de acción (analizar, cambiar dir)
│   │   ├── header.py                # Encabezado de la aplicación
│   │   ├── search_bar.py            # Barra de búsqueda en tabs
│   │   └── summary_panel.py         # Panel de resumen de análisis
│   │
│   ├── controllers/                 # Controladores (puente UI ↔ Services)
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
│   │   ├── directory_dialog.py      # Selección de directorio
│   │   ├── duplicates_dialogs.py    # Diálogos de duplicados
│   │   ├── heic_dialog.py           # Diálogo de HEIC
│   │   ├── live_photos_dialog.py    # Diálogo de Live Photos
│   │   ├── renaming_dialog.py       # Diálogo de renombrado
│   │   └── settings_dialog.py       # Diálogo de configuración
│   │
│   ├── managers/                    # Gestores de recursos
│   │   ├── __init__.py
│   │   └── logging_manager.py       # Gestión de archivos de log
│   │
│   ├── tabs/                        # Pestañas de la aplicación
│   │   ├── __init__.py
│   │   ├── base_tab.py              # Clase base para tabs
│   │   ├── duplicates_tab.py        # Tab de duplicados
│   │   ├── heic_tab.py              # Tab de HEIC
│   │   ├── live_photos_tab.py       # Tab de Live Photos
│   │   ├── organizer_tab.py         # Tab de organización
│   │   └── renaming_tab.py          # Tab de renombrado
│   │
│   └── validators/                  # Validadores de entrada
│       └── directory_validator.py   # Validación de directorios
│
└── utils/                           # Utilidades compartidas
    ├── __init__.py
    ├── callback_utils.py            # Utilidades para callbacks de progreso
    ├── date_utils.py                # Manipulación de fechas
    ├── file_utils.py                # Operaciones con archivos (hash, backup, paths)
    ├── format_utils.py              # Formateo de tamaños, números, etc.
    ├── logger.py                    # Sistema de logging centralizado
    └── settings_manager.py          # Gestión de configuración persistente (QSettings)
```

## Arquitectura

**Patrón de 3 capas:**
- **Services**: Lógica de negocio pura, sin dependencias de UI
- **Controllers**: Coordinan entre UI y Services, manejan workers
- **UI**: Componentes visuales PyQt6 (tabs, dialogs, widgets)

**Flujo típico:** Analizar → Preview → Confirmar → Ejecutar (con backup opcional)

