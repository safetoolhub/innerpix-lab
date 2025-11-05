# Changelog

## [MVP2 - Fase 4] - 2025-11-05

### ✨ Añadido

**Persistencia de Datos:**
- Sistema de guardado automático de última carpeta analizada
- Widget visual para acceso rápido a última carpeta en Estado 1
- Botón "Usar esta carpeta" para re-analizar con un clic
- Guardado de resumen de análisis (estadísticas por herramienta)
- Validación de existencia de carpeta antes de mostrar/usar

**Animaciones y Transiciones:**
- Sistema centralizado de animaciones con `_fade_out_widget()` y `_fade_in_widget()`
- Transiciones suaves Estado 1 → Estado 2 con fade in/out (250-350ms)
- Transiciones suaves Estado 2 → Estado 3 con fade in/out escalonado
- Delays estratégicos para visualización de animaciones (150-300ms)
- Curvas de easing: OutCubic para fade out, InCubic para fade in
- Animación de vuelta a Estado 1 en caso de error

**Manejo de Errores Mejorado:**
- Validación exhaustiva de carpeta seleccionada (4 niveles):
  1. Verificación de existencia
  2. Verificación de tipo (directorio vs archivo)
  3. Verificación de permisos de lectura
  4. Advertencia de carpeta vacía con confirmación
- Diálogo de error en análisis con 3 opciones de recuperación:
  - Reintentar análisis con misma carpeta
  - Cambiar carpeta (volver a Estado 1)
  - Cerrar diálogo
- Limpieza automática de estado en errores (timers, fases, etc.)
- Mensajes de error claros, informativos y accionables

**Configuración:**
- Activado diálogo de configuración (SettingsDialog)
- Acceso desde icono en welcome card del Estado 1

### 🔧 Modificado

- `ui/main_window.py`:
  - Añadidos imports: `os` para validación de permisos
  - `settings_manager` para persistencia
  - Añadidos atributos: `last_folder`, `last_folder_widget`
  - Nuevos métodos para animaciones (2)
  - Nuevos métodos para persistencia (3)
  - Nuevos métodos para manejo de errores (3)
  - Mejoras en transiciones entre estados
  - Validaciones exhaustivas en selección de carpeta

### 📚 Documentación

- Creado `FASE_4_IMPLEMENTADA.md` con documentación completa
- Actualizado `CHANGELOG.md` con nuevas características
- Actualizado `.github/copilot-instructions.md` con Fase 4

### 🎯 Criterios de Éxito Completados

- [x] Usuario recurrente puede continuar con última carpeta en 1 clic
- [x] Transiciones suaves entre estados
- [x] Mensajes de error claros y accionables
- [x] Animaciones fluidas y profesionales
- [x] Recuperación de errores sin bloquear al usuario

---

## [MVP1] - 2025-11-04

### Resumen

Versión inicial congelada del proyecto. Incluye las últimas mejoras y refactors de la UI (top bar, styles), correcciones menores y limpieza de componentes.

Commits recientes (últimos 50 en `develop` en el momento de crear la rama MVP1):

- 18648fc Merge pull request #42 from Novacode-labs/new1 (Novacode-labs)
- b5ed83b minotr tweaks (Carlos)
- dac9aa1 Merge pull request #41 from Novacode-labs/new1 (Novacode-labs)
- 4d2ca39 refactorizados estilos de top_bar a styles.py (Carlos)
- cb780f6 Merge pull request #40 from Novacode-labs/new1 (Novacode-labs)
- 186826d arreglado el borde inferior de stats bar (Carlos)
- 44cd41e borrar ficheros sobrantes de antes (Carlos)
- 166fec7 Merge pull request #39 from Novacode-labs/revert-last-5-prs (Novacode-labs)
- de7fffa Refactorizar top_bar para que ocupe menos nates de hacer el cambio del control bar (segunda ronda) (Carlos)
- 782fe11 Revert "Merge pull request #36 from Novacode-labs/27" (Carlos)
- 786e287 Revert "Merge pull request #37 from Novacode-labs/27" (Carlos)
- 6cc20b8 Revert "Merge pull request #38 from Novacode-labs/27" (Carlos)
- 39e2297 Merge pull request #38 from Novacode-labs/27 (Novacode-labs)
- 8ba5a4b refactor para mejorar botones (Carlos)
- adcf75f Merge pull request #37 from Novacode-labs/27 (Novacode-labs)
- 7018d20 sigue mal (Carlos)
- 39378ee Merge pull request #36 from Novacode-labs/27 (Novacode-labs)
- d9e1a4b botones no funcionan correctamente. (Carlos)
- 8ab77e1 Merge pull request #35 from Novacode-labs/27 (Novacode-labs)
- 7802673 seguimos (Carlos)
- e26db68 run debug (Carlos)
- fe730c4 Merge pull request #34 from Novacode-labs/27 (Novacode-labs)
- 1261f12 arreglado icons en stats (Carlos)
- b8093fd Merge pull request #33 from Novacode-labs/27 (Novacode-labs)
- bb4b8a7 improve copilot instructions (Carlos)
- fef16e0 Merge pull request #32 from Novacode-labs/27 (Novacode-labs)
- d5b3547 arreglos (Carlos)
- 3cbc263 Merge pull request #31 from Novacode-labs/27 (Novacode-labs)
- 0aea493 mejorar con qtawesome (Carlos)
- d333d28 Merge pull request #30 from Novacode-labs/27 (Novacode-labs)
- d8afe85 cambio en copilot file y tree importantes. AÑadir iconos (Carlos)
- c893351 Merge pull request #29 from Novacode-labs/27 (Novacode-labs)
- 9a524a5 siguen falando emojis (Carlos)
- 53f0443 Merge pull request #28 from Novacode-labs/27 (Novacode-labs)
- ab15254 fin elminacion summary_panel (Carlos)
- 385832f Merge pull request #27 from Novacode-labs/27 (Novacode-labs)
- 03f2073 eliminado sumamry_panel (Carlos)
- 3e0827d Merge pull request #26 from Novacode-labs/27 (Novacode-labs)
- b6322fd nuevo estilo todo arriba (Carlos)
- 5e23d8c Merge pull request #25 from Novacode-labs/26 (Novacode-labs)
- 159c607 more changes in top bar (Carlos)
- b336dad Merge pull request #24 from Novacode-labs/26 (Novacode-labs)
- d6d7fcd creada top_bar y cambiado todo headerf (Carlos)
- 2ca8184 Merge pull request #23 from Novacode-labs/26 (Novacode-labs)
- beeefc5 directorio entero y configuraicon (Carlos)
- f47ed2f Merge pull request #22 from Novacode-labs/26 (Novacode-labs)
- d3f2579 refactor para aaislar UI (Carlos)
- 9c3aad4 Merge pull request #21 from Novacode-labs/26 (Novacode-labs)
- 61cc957  Prioridad 2 - Platform Utils Funciones de sistema extraídas de UI Scripts CLI habilitados Logging + validación robusta (Carlos)
- 8f9f09f Merge pull request #20 from Novacode-labs/26 (Novacode-labs)

---

Notas:
- Este changelog es ligero y generado automáticamente. Si quieres que lo refine (separar features / fixes / docs, vincular PRs o autores con más detalle), lo puedo mejorar.
