## PhotoKit Manager - AI coding assistant instructions

This file contains concise, actionable guidance for an AI coding agent working on the
PhotoKit Manager repository. Keep suggestions and edits aligned with the project's
patterns (workers + services + UI) and avoid changing user-visible behaviour without tests.

- Entry point & runtime
  - Launch: `python main.py` (creates a PyQt6 QApplication and instantiates `ui.main_window.MainWindow`).
  - Config values live in `config.py` (class `Config`). Note: some modules reference `config.Config` and others `config.config` (a module-level instance). Check both when making changes.

- Platforms
  - Primary: Windows 
  - Secondary: Mac and Linux supported but not primary targets

- Project structure
  - Always updated in PROJECT_TREE.md file 

- Important patterns & conventions (examples)
  - Backup-first: many destructive operations (live photos, organization, duplicate deletion, renaming, etc) accept `create_backup=True`. Preserve that behaviour and prefer creating backups via `utils.file_utils.launch_backup_creation` when changing execute flows (see `services/directory_unifier.py`).
 
- Developer workflow (what to run locally)
  - Create virtualenv: `python -m venv .venv && source .venv/bin/activate`
  - Install deps: `pip install -r requirements.txt` (note some packages require system libraries like `libheif` for `pillow-heif`).
  - Run app: `python main.py` (GUI). Use the logger and logs directory set in `config.Config.DEFAULT_LOG_DIR` for debugging.

- When editing code
  - For changes touching file operations, keep `create_backup` flows and metadata writing (see `unification_metadata.txt` usage in `directory_unifier.py`).
- Do not implement legacy callbacks, as there is only one author for this project
- Do not add useless try/catch methods that only pass
- Be strict with PEP 8

- Quick safety checklist for PRs
  1. Run static checks and fix obvious linting errors (PEP8, type hints where present).
  2. Run the app locally and exercise the relevant UI path (start analysis, preview and execution) if code touches UI or services that operate on files.
  3. Preserve `create_backup` defaults unless explicitly requested by the user.

