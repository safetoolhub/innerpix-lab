## PhotoKit Manager - AI coding assistant instructions

This file contains concise, actionable guidance for an AI coding agent working on the
PhotoKit Manager repository. Keep suggestions and edits aligned with the project's
patterns (workers + services + UI) and avoid changing user-visible behaviour without tests.

- Entry point & runtime
  - Launch: `python main.py` (creates a PyQt5 QApplication and instantiates `ui.main_window.MainWindow`).
  - Config values live in `config.py` (class `Config`). Note: some modules reference `config.Config` and others `config.config` (a module-level instance). Check both when making changes.

- High-level architecture
  - `ui/` holds GUI components, dialogs, controllers and `ui/workers.py` (QThread-based workers). UI must only be manipulated from the main thread; workers communicate via signals: `progress_update(int,int,str)`, `finished(dict)`, and `error(str)`.
  - `services/` contains business logic (e.g. `directory_unifier.py`, `duplicate_detector.py`, `live_photo_cleaner.py`). Services generally expose `analyze_*` and `execute_*` methods and accept an optional `progress_callback` callable.
  - `utils/` contains helper functions used across services and UI (e.g. `utils.file_utils.launch_backup_creation`, `utils.file_utils.calculate_file_hash`, `utils.logger.get_logger`). Prefer using these helpers rather than duplicating file/IO logic.

- Important patterns & conventions (examples)
  - Workers: use `BaseWorker._create_progress_callback()` in `ui/workers.py` so emitted progress messages match UI expectations. The UI often expects progress signals with `(0,0,message)` and uses `counts_in_message` or `emit_numbers` only when appropriate.
  - Backup-first: many destructive operations (unification, duplicate deletion, renaming) accept `create_backup=True`. Preserve that behaviour and prefer creating backups via `utils.file_utils.launch_backup_creation` when changing execute flows (see `services/directory_unifier.py`).
 
- Developer workflow (what to run locally)
  - Create virtualenv: `python -m venv .venv && source .venv/bin/activate`
  - Install deps: `pip install -r requirements.txt` (note some packages require system libraries like `libheif` for `pillow-heif`).
  - Run app: `python main.py` (GUI). Use the logger and logs directory set in `config.Config.DEFAULT_LOG_DIR` for debugging.

- When editing code
  - Preserve signal names and payload shapes (progress: int,int,str; finished: dict; error: str). Tests and UI wiring assume these shapes.
  - If updating a `service` API (e.g. change return dict keys), update callers in `ui/workers.py`, `ui/*` components, and `ui/tabs/*` which read analysis results.
  - For changes touching file operations, keep `create_backup` flows and metadata writing (see `unification_metadata.txt` usage in `directory_unifier.py`).
- Do not implement legacy callbacks, as there is only one author for theis project
- Do not add useless try/catch methods that only pass
- Be strict with PEP 8


- Files & locations to inspect for context
  - `main.py` — app entry
  - `config.py` — feature flags, paths, thresholds
  - `ui/main_window.py` — orchestrates UI, workers and services
  - `ui/workers.py` — worker patterns and expected signals
  - `services/*` — business logic (look at `directory_unifier.py`, `duplicate_detector.py` for representative patterns)
  - `utils/file_utils.py` — backup and file helpers (used widely)
  - `utils/logger.py` and `ui/managers/logging_manager.py` — logging setup and file logging

- Quick safety checklist for PRs
  1. Run static checks and fix obvious linting errors (PEP8, type hints where present).
  2. Run the app locally and exercise the relevant UI path (start analysis, preview and execution) if code touches UI or services that operate on files.
  3. Preserve `create_backup` defaults unless explicitly requested by the user.
  4. Update callers if you rename keys in result dictionaries (search for `.get('unification')`, `.get('heic')`, etc.).

