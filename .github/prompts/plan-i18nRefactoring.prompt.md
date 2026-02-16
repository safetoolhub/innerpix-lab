## Plan: i18n Refactoring with JSON-based Translation System

**TL;DR**: Create a lightweight JSON key-based i18n system (`utils/i18n.py`) with a universal `tr(key, **kwargs)` function usable everywhere (UI + services). Extract ~700 Spanish strings into `i18n/es.json`, create `i18n/en.json` with full English translation, and add a language selector in the Settings dialog (General tab → Interfaz group). Language change requires app restart; preference persists via `settings_manager`.

**Steps**

### Phase 1: Infrastructure (3 files)

1. **Create `i18n/es.json`** — Spanish base translation file with hierarchical keys organized by domain:
   - `app.*` — app name, description, version strings
   - `common.*` — shared strings: "Cancelar", "Guardar", "Error", "Éxito", "Cerrar", etc.
   - `tools.<tool_id>.title|short_description|long_description` — 8 tools × 3 fields = 24 entries
   - `categories.<cat_id>.title|description` — 3 categories × 2 fields = 6 entries
   - `stage1.*`, `stage2.*`, `stage3.*` — stage screen strings (~80 entries)
   - `settings.*` — settings dialog tab names, labels, tooltips (~100 entries)
   - `dialogs.<name>.*` — per-dialog strings (~300 entries across 10+ dialogs)
   - `services.*` — progress callback messages (~20 entries)
   - `formats.*` — format patterns with placeholders, e.g. `"formats.files_found": "{count} archivos encontrados"`

2. **Create `i18n/en.json`** — Complete English translation mirroring every key in `es.json`. Same structure, all values translated.

3. **Create `utils/i18n.py`** — Core i18n module:
   - `_translations: dict` — loaded translation data (nested dict)
   - `_fallback: dict` — Spanish fallback (always loaded)
   - `_current_lang: str` — current language code
   - `SUPPORTED_LANGUAGES = {"es": "Español", "en": "English"}`
   - `init_i18n(lang: str = "es")` — loads JSON files from `i18n/` directory, sets current language, loads fallback
   - `tr(key: str, **kwargs) -> str` — resolves dotted key (e.g., `"tools.zero_byte.title"`) against current translations, falls back to Spanish, then to key itself. Supports `str.format(**kwargs)` for interpolation: `tr("formats.files_count", count=42)` → `"42 archivos"`
   - `get_current_language() -> str`
   - `get_supported_languages() -> dict[str, str]`
   - Key resolution: split by `.`, traverse nested dict, return value or fallback
   - Thread-safe (module-level, read-only after init)

### Phase 2: Settings Integration (2 files)

4. **Modify `utils/settings_manager.py`** — Add language setting:
   - Add constant `KEY_LANGUAGE = "interface/language"`
   - Add `get_language(default: str = "es") -> str` convenience method
   - Add `set_language(lang: str)` convenience method

5. **Modify `main.py`** — Initialize i18n before UI creation:
   - After `settings_manager` import and before `QApplication` creation, read `settings_manager.get_language()` and call `init_i18n(lang)`
   - This ensures all `tr()` calls throughout the app resolve correctly from the start

### Phase 3: Refactor Core Data (1 file)

6. **Refactor `ui/tools_definitions.py`** — Remove hardcoded Spanish from `ToolDefinition` constants. Two approaches possible; recommended: keep `ToolDefinition` instances with ID-only data (drop `title`/`short_description`/`long_description` text), and make accessor functions like `get_tool_title(tool_id)`, `get_tool_short_description(tool_id)`, `get_tool_long_description(tool_id)` call `tr(f"tools.{tool_id}.title")` etc. The `ToolDefinition` dataclass keeps `id` and `icon_name` (language-independent). Category accessor `get_category()` would similarly call `tr(f"categories.{cat_id}.title")`. This ensures lazy resolution — translations are fetched at call time, not import time.

### Phase 4: Refactor UI Layer (~20 files, bulk of the work)

Replace every hardcoded Spanish string with `tr("key")` calls. Files ordered by string density (highest first):

7. **`ui/dialogs/settings_dialog.py`** (~100 strings) — Tab names, group titles, checkbox labels, tooltips, QMessageBox texts, footer buttons. Also add language selector (see Step 20).

8. **`ui/dialogs/about_dialog.py`** (~80 strings) — Welcome text, tutorial tabs, workflow descriptions, version info.

9. **`ui/dialogs/file_organizer_dialog.py`** (~60 strings) — Strategy labels, radio buttons, info labels, action buttons, messages.

10. **`ui/dialogs/duplicates_similar_dialog.py`** (~50 strings) — Sensitivity slider labels, filter options, strategy buttons, group headers.

11. **`ui/dialogs/dialog_utils.py`** (~40 strings) — File detail labels ("Nombre:", "Tamaño:"), context menu items, date format labels.

12. **`ui/screens/stage_3_window.py`** (~50 strings) — Tool grid titles, QMessageBox dialogs, progress labels, banner messages.

13. **`ui/screens/stage_1_window.py`** (~30 strings) — Tips, buttons, validation messages, dropzone text.

14. **`ui/screens/stage_2_window.py`** (~20 strings) — Cancel confirmation, error messages, phase descriptions.

15. **`ui/dialogs/base_dialog.py`** (~20 strings) — "Cancelar", confirm dialogs, "Sin cambios", backup/dry-run checkbox labels.

16. **Remaining dialogs** — Each with ~15-30 strings:
    - `ui/dialogs/visual_identical_dialog.py`
    - `ui/dialogs/duplicates_exact_dialog.py`
    - `ui/dialogs/heic_dialog.py`
    - `ui/dialogs/live_photos_dialog.py`
    - `ui/dialogs/zero_byte_dialog.py`
    - `ui/dialogs/file_renamer_dialog.py`
    - `ui/dialogs/image_preview_dialog.py`

17. **Remaining screens** — Each with ~3-10 strings:
    - `ui/screens/progress_card.py` — "Analizando", "Cancelar"
    - `ui/screens/summary_card.py` — "Carpeta:", "Cambiar", "Reanalizar"
    - `ui/screens/analysis_phase_widget.py` — 6 phase descriptions
    - `ui/screens/dropzone_widget.py` — "Arrastra una carpeta aquí"
    - `ui/screens/base_stage.py` — Tooltips: "Configuración", "Acerca de"
    - `ui/screens/main_window.py` — Window title
    - Tool card files in `ui/screens/tool_cards/` — Status messages

### Phase 5: Refactor Services (~6 files)

18. **Service progress messages** — Replace Spanish progress callback strings with `tr()` in:
    - `services/file_organizer_service.py` — "Analizando fechas", "Analizando tipos"
    - `services/file_renamer_service.py` — "Analizando nombres de archivos"
    - `services/visual_identical_service.py` — "Procesando:"
    - `services/initial_scanner.py` — 6 phase description strings
    - `services/zero_byte_service.py` — Error messages
    - `services/duplicates_exact_service.py` — Error messages
    - Note: `import` of `tr` from `utils.i18n` does NOT introduce PyQt6 dependency — `utils/i18n.py` is pure Python
    - Log-only messages (logger.info/debug) remain in Spanish — they are developer-facing, not user-facing

19. **`config.py`** — Change `APP_DESCRIPTION` to use `tr("app.description")`, or remove the hardcoded Spanish and let the UI read from translations directly.

### Phase 6: Language Selector UI (1 file)

20. **Add language selector in `ui/dialogs/settings_dialog.py`** — In `_create_general_tab()`, add a new item at the top of the "Interfaz" group (before the existing path checkbox):
    - `QLabel(tr("settings.language_label"))` + `QComboBox` with `SUPPORTED_LANGUAGES` items
    - Current language pre-selected from `settings_manager.get_language()`
    - On save: if language changed, call `settings_manager.set_language(new_lang)` and show `QMessageBox.information()` saying restart is required (the message itself uses `tr()`)
    - Combo shows native language names: "Español", "English"

### Phase 7: Validation & Testing

21. **Create `dev-tools/validate_translations.py`** — Script that:
    - Loads all JSON files from `i18n/`
    - Compares key sets: reports keys missing in `en.json` vs `es.json` and vice versa
    - Reports keys with empty values
    - Reports keys with mismatched placeholder counts (e.g., `{count}` in Spanish but missing in English)
    - Can be run: `python dev-tools/validate_translations.py`

22. **Update existing tests** — Tests that mock or check Spanish text in assertions will need updates. Primarily:
    - Tests that assert specific Spanish strings in results → use `tr()` or match against keys
    - Tests for `settings_manager` → add test for `get_language()`/`set_language()`
    - Add a new test file `tests/unit/utils/test_i18n.py`: test `tr()` resolution, fallback, interpolation, missing keys

23. **Manual smoke test** — Run the app in both languages (`es` and `en`), navigate all 3 stages, open all 8 tool dialogs, open settings, and verify no untranslated strings remain.

---

### Verification Checklist

- Run `python dev-tools/validate_translations.py` — should report 0 missing keys
- Run `pytest` — all 590+ tests should pass
- Launch app with Spanish: verify identical to current behavior
- Launch app with English: verify complete translation
- Change language in Settings → verify restart message → restart → verify new language

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| i18n mechanism | JSON key-based (`tr()`) | Works in PyQt6-free services, easy to review/diff JSON files |
| Language change | Restart required | Dramatically simpler, avoids re-rendering every widget |
| Services strings | Universal `tr()` | Keeps services clean (no PyQt6), just one pure-Python import |
| Log messages | They will be translated to English always | Developer-facing, not user-facing |
| Fallback language | Spanish (`es.json`) | Guarantees no empty UI even if English has missing keys |
| `ToolDefinition` refactor | Drop text fields, use `tr()` in accessors | Avoids import-time evaluation problem |
