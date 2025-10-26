photokit-manager/ - Estructura del proyecto

```
photokit-manager/
├── LICENSE
├── README.md
├── PROJECT_TREE.md
├── main.py
├── config.py
├── requirements.txt
├── docs/
│   ├── prompt_dev.txt
│   └── TODO.txt
├── services/
│   ├── __init_.py
│   ├── directory_unifier.py
│   ├── duplicate_detector.py
│   ├── file_renamer.py
│   ├── heic_remover.py
│   ├── live_photo_cleaner.py
│   └── live_photo_detector.py
├── ui/
│   ├── __init__.py
│   ├── helpers.py
│   ├── main_window.py
│   ├── styles.py
│   ├── workers.py
│   ├── components/
│   │   ├── __init__.py
│   │   ├── header.py
│   │   ├── progress_bar.py
│   │   ├── search_bar.py
│   │   └── summary_panel.py
│   ├── controllers/
│   │   ├── analysis_controller.py
│   │   ├── duplicates_controller.py
│   │   ├── heic_controller.py
│   │   ├── live_photos_controller.py
│   │   ├── progress_controller.py
│   │   ├── renaming_controller.py
│   │   ├── results_controller.py
│   │   ├── tab_controller.py
│   │   └── unifier_controller.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── about_dialog.py
│   │   ├── base_dialog.py
│   │   ├── directory_dialog.py
│   │   ├── duplicates_dialogs.py
│   │   ├── heic_dialog.py
│   │   ├── live_photos_dialog.py
│   │   ├── renaming_dialog.py
│   │   └── settings_dialog.py
│   ├── managers/
│   │   ├── __init__.py
│   │   └── logging_manager.py
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── base_tab.py
│   │   ├── duplicates_tab.py
│   │   ├── heic_tab.py
│   │   ├── live_photos_tab.py
│   │   ├── renaming_tab.py
│   │   └── unifier_tab.py
│   └── validators/
│       └── directory_validator.py
├── utils/
│   ├── __init__.py
│   ├── date_utils.py
│   ├── file_utils.py
│   ├── format_utils.py
│   └── logger.py
└── .gitignore

```

