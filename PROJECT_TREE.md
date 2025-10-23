photokit-manager/ - Estructura del proyecto

```
photokit_manager/
├── main.py # Punto de entrada
├── config.py # Configuración
├── requirements.txt # Dependencias
├── LICENSE # Licencia del proyecto
├── README.md # Documentación principal
├── PROJECT_TREE.md # Este archivo: esquema ASCII del proyecto
├── docs/ # Documentación y notas de desarrollo
│   ├── prompt_dev.txt
│   └── TODO.txt
├── services/ # Lógica de negocio y procesamiento
│   ├── __init_.py
│   ├── directory_unifier.py
│   ├── duplicate_detector.py
│   ├── file_renamer.py
│   ├── heic_remover.py
│   ├── live_photo_cleaner.py
│   └── live_photo_detector.py
├── ui/ # Interfaz gráfica (PyQt5)
│   ├── __init__.py
│   ├── helpers.py
│   ├── main_window.py # Ventana principal (refactor pendiente)
│   ├── styles.py
│   ├── helpers.py
│   ├── workers.py # Hilos y tareas en background para no bloquear UI
│   ├── components/
│   │   ├── __init__.py
│   │   ├── header.py
│   │   ├── progress_bar.py
│   │   ├── search_bar.py
│   │   └── summary_panel.py
│   └── dialogs/
│       ├── __init__.py
│       ├── about_dialog.py
│       ├── base_dialog.py
│       ├── directory_dialog.py
│       ├── duplicates_dialogs.py
│       ├── heic_dialog.py
│       ├── live_photos_dialog.py
│       ├── renaming_dialog.py
│       └── settings_dialog.py
├── ui/tabs/ # Pestañas principales de la aplicación
│   ├── __init__.py
│   ├── base_tab.py
│   ├── duplicates_tab.py # Interfaz para gestionar duplicados
│   ├── heic_tab.py
│   ├── live_photos_tab.py
│   ├── renaming_tab.py
│   └── unifier_tab.py
├── utils/ # Utilidades auxiliares
│   ├── __init__.py
│   ├── date_utils.py
│   └── logger.py # Logging estructurado a archivos timestamped


```


