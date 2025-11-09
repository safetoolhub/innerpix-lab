<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# PROMPT COMPLETO: Implementación de Sistema de Re-análisis Inteligente y Gestión de "Archivos Similares" en Pixaro Lab

## Contexto del Proyecto

Pixaro Lab es una aplicación de escritorio multiplataforma desarrollada en Python con PyQt6 para gestionar colecciones de imágenes y vídeos. La aplicación tiene un Stage 3 con 6 herramientas presentadas como cards:

1. **Live Photos** (análisis rápido)
2. **HEIC/JPG Duplicados** (análisis rápido)
3. **Copias exactas** (análisis rápido) - antes "Duplicados exactos"
4. **Archivos similares** (análisis costoso, minutos) - antes "Duplicados similares"
5. **Organizar archivos** (análisis rápido)
6. **Renombrar archivos** (análisis rápido)

**Estructura del proyecto**: Ver `PROJECT_TREE.md` para estructura completa.

**Archivos principales**:

- `ui/stages/stage3window.py` - Ventana principal del Stage 3
- `ui/dialogs/similarfilesdialog.py` - Diálogo de gestión (antes similardialog.py)
- `ui/dialogs/similarfilesconfigdialog.py` - Diálogo de configuración (nuevo)
- `ui/dialogs/similarfilesprogressdialog.py` - Diálogo de progreso (nuevo)
- `ui/workers.py` - Workers para análisis en background
- `services/` - Lógica de negocio (PyQt-free)

***

## Problema a Resolver

Cuando un usuario ejecuta una herramienta que modifica archivos (elimina, mueve, renombra), los análisis de las otras herramientas quedan **obsoletos**. Hay dos casos diferentes:

### Caso 1: 5 herramientas con análisis rápido (< 5 segundos)

- Live Photos, HEIC/JPG, Copias exactas, Organizar, Renombrar
- **Solución**: Re-análisis automático tras cada modificación


### Caso 2: 1 herramienta con análisis costoso (minutos)

- Archivos similares (detección por perceptual hash)
- **Solución**: Invalidar análisis y permitir ver resultados antiguos o reanalizar

***

## Objetivo de la Implementación

Implementar un **sistema de re-análisis inteligente** que:

1. **Re-analiza automáticamente** las 5 herramientas rápidas tras cada modificación de archivos
2. **Invalida** el análisis de "Archivos similares" y permite al usuario decidir
3. **Muestra feedback visual** durante el proceso (overlay no bloqueante)
4. **Mantiene consistencia** en los datos mostrados en todas las cards
5. **Ofrece opciones** al usuario para ver resultados antiguos o reanalizar

***

## PARTE 1: Configuración y Constantes

### Archivo: `config.py` (modificar o añadir)

```python
# Clasificación de herramientas por coste de análisis
TOOL_ANALYSIS_COST = {
    "live_photos": "fast",          # < 5 segundos
    "heic_jpg": "fast",
    "exact_copies": "fast",
    "organize": "fast",
    "rename": "fast",
    "similar_files": "expensive"    # Minutos
}

# Impacto de cada herramienta en los archivos
TOOL_IMPACT_ON_FILES = {
    "live_photos": "destructive",   # Elimina vídeos de Live Photos
    "heic_jpg": "destructive",      # Elimina duplicados HEIC/JPG
    "exact_copies": "destructive",  # Elimina copias exactas
    "similar_files": "destructive", # Elimina archivos similares
    "organize": "moves",            # Mueve archivos a carpetas
    "rename": "renames"             # Renombra archivos
}

# Nombres legibles de herramientas para UI
TOOL_DISPLAY_NAMES = {
    "live_photos": "Live Photos",
    "heic_jpg": "HEIC/JPG",
    "exact_copies": "Copias exactas",
    "similar_files": "Archivos similares",
    "organize": "Organizar archivos",
    "rename": "Renombrar archivos"
}
```


***

## PARTE 2: Worker de Re-análisis Rápido

### Archivo: `ui/workers.py` (añadir nueva clase)

```python
from PyQt6.QtCore import QThread, pyqtSignal
from services.livephotodetector import LivePhotoDetector
from services.heicremover import HeicRemover
from services.exactcopiesdetector import ExactCopiesDetector
from services.fileorganizer import FileOrganizer
from services.filerenamer import FileRenamer
from config import TOOL_DISPLAY_NAMES

class WorkspaceReanalysisWorker(QThread):
    """
    Worker para re-análisis automático del workspace.
    Solo ejecuta análisis rápidos (< 5 segundos cada uno).
    """
    
    # Señales
    progress_updated = pyqtSignal(str, int, int)  # (tool_display_name, current, total)
    tool_completed = pyqtSignal(str, object)      # (tool_name, results)
    analysis_completed = pyqtSignal(dict)         # {tool_name: results}
    analysis_error = pyqtSignal(str, str)         # (tool_name, error_message)
    
    def __init__(self, workspace_path: str):
        super().__init__()
        self.workspace_path = workspace_path
        self._is_cancelled = False
        
        # Lista de análisis a ejecutar (solo rápidos)
        self.tools_to_analyze = [
            ("live_photos", LivePhotoDetector),
            ("heic_jpg", HeicRemover),
            ("exact_copies", ExactCopiesDetector),
            ("organize", FileOrganizer),
            ("rename", FileRenamer)
        ]
        
    def run(self):
        """Ejecuta re-análisis de todas las herramientas rápidas."""
        results = {}
        total = len(self.tools_to_analyze)
        
        for idx, (tool_name, detector_class) in enumerate(self.tools_to_analyze, 1):
            if self._is_cancelled:
                break
            
            # Emitir progreso
            display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
            self.progress_updated.emit(display_name, idx, total)
            
            # Ejecutar análisis
            try:
                detector = detector_class()
                result = detector.analyze(self.workspace_path)
                results[tool_name] = result
                self.tool_completed.emit(tool_name, result)
                
            except Exception as e:
                error_msg = f"Error en {display_name}: {str(e)}"
                self.analysis_error.emit(tool_name, error_msg)
                results[tool_name] = {"error": str(e)}
        
        # Emitir resultados completos
        if not self._is_cancelled:
            self.analysis_completed.emit(results)
    
    def cancel(self):
        """Cancela el re-análisis en curso."""
        self._is_cancelled = True
```

**Notas**:

- Cada detector debe tener un método `analyze(workspace_path)` que retorna un objeto de resultados
- Los detectores deben ser PyQt-free (sin imports de PyQt6)
- Los resultados deben incluir: `file_count`, `groups` (si aplica), `recoverable_space` (si aplica), etc.

***

## PARTE 3: Overlay de Re-análisis

### Archivo: `ui/widgets/reanalysisoverlay.py` (crear nuevo)

```python
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QMovie
from utils.icons import icon_manager

class ReanalysisOverlay(QFrame):
    """
    Overlay semi-transparente que muestra el progreso del re-análisis.
    No modal: permite ver las cards pero no interactuar temporalmente.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("reanalysis_overlay")
        self._setup_ui()
        self._apply_styles()
        
    def _setup_ui(self):
        """Configura la interfaz del overlay."""
        # Layout principal centrado
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Card de progreso
        self.progress_card = QFrame()
        self.progress_card.setObjectName("progress_card")
        self.progress_card.setFixedSize(420, 140)
        
        card_layout = QVBoxLayout(self.progress_card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(24, 20, 24, 20)
        
        # --- Header: Icono + Título ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Spinner animado
        self.spinner_label = QLabel()
        icon_manager.set_label_icon(self.spinner_label, "sync", color="#1976D2", size=24)
        # Aplicar animación de rotación
        self._start_spinner_animation()
        
        self.title_label = QLabel("Actualizando análisis...")
        self.title_label.setObjectName("progress_title")
        
        header_layout.addWidget(self.spinner_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # --- Barra de progreso ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        
        # --- Texto de estado ---
        self.status_label = QLabel("Preparando análisis...")
        self.status_label.setObjectName("progress_status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Agregar elementos al layout
        card_layout.addLayout(header_layout)
        card_layout.addWidget(self.progress_bar)
        card_layout.addWidget(self.status_label)
        
        main_layout.addWidget(self.progress_card)
    
    def _start_spinner_animation(self):
        """Inicia animación de rotación del spinner."""
        self.rotation_animation = QPropertyAnimation(self.spinner_label, b"rotation")
        self.rotation_animation.setDuration(1000)  # 1 segundo por rotación
        self.rotation_animation.setStartValue(0)
        self.rotation_animation.setEndValue(360)
        self.rotation_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.rotation_animation.setLoopCount(-1)  # Infinito
        self.rotation_animation.start()
    
    def update_progress(self, tool_name: str, current: int, total: int):
        """
        Actualiza el progreso mostrado.
        
        Args:
            tool_name: Nombre legible de la herramienta siendo analizada
            current: Herramienta actual (1-based)
            total: Total de herramientas
        """
        percentage = int((current / total) * 100)
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Analizando: {tool_name} ({current}/{total})")
    
    def _apply_styles(self):
        """Aplica estilos Material Design al overlay."""
        self.setStyleSheet("""
            QFrame#reanalysis_overlay {
                background-color: rgba(0, 0, 0, 0.6);
            }
            
            QFrame#progress_card {
                background-color: #FFFFFF;
                border-radius: 16px;
                border: none;
            }
            
            QLabel#progress_title {
                font-size: 16px;
                font-weight: 600;
                color: #212121;
            }
            
            QLabel#progress_status {
                font-size: 13px;
                color: #757575;
            }
            
            QProgressBar#progress_bar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
            }
            
            QProgressBar#progress_bar::chunk {
                background-color: #1976D2;
                border-radius: 4px;
            }
        """)
    
    def show_overlay(self):
        """Muestra el overlay con fade-in."""
        self.show()
        self.raise_()
        
        # Animación de fade-in (opcional)
        self.setWindowOpacity(0)
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.start()
    
    def hide_overlay(self):
        """Oculta el overlay con fade-out."""
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(200)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)
        fade_out.finished.connect(self.hide)
        fade_out.start()
```


***

## PARTE 4: Modificaciones en Stage3Window

### Archivo: `ui/stages/stage3window.py` (modificar)

**Añadir imports**:

```python
from datetime import datetime
from ui.widgets.reanalysisoverlay import ReanalysisOverlay
from ui.workers import WorkspaceReanalysisWorker
from config import TOOL_IMPACT_ON_FILES, TOOL_ANALYSIS_COST
from PyQt6.QtWidgets import QMessageBox
```

**Añadir atributos en `__init__`**:

```python
class Stage3Window(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # ... código existente ...
        
        # Sistema de re-análisis
        self.reanalysis_worker = None
        self.reanalysis_overlay = None
        
        # Datos de "Archivos similares"
        self.similarity_results = None
        self.similarity_analysis_timestamp = None
        self.similarity_results_snapshot = None
        self.tools_executed_after_similarity = []
        
        # ... resto de inicialización ...
```

**Añadir métodos nuevos**:

```python
    # ==========================================
    # SISTEMA DE RE-ANÁLISIS AUTOMÁTICO
    # ==========================================
    
    def _on_tool_action_completed(self, tool_name: str, actions_executed: bool):
        """
        Callback cuando una herramienta completa acciones.
        
        Args:
            tool_name: Nombre de la herramienta ejecutada
            actions_executed: True si se ejecutaron acciones que modificaron archivos
        """
        if not actions_executed:
            return
        
        # Registrar herramienta ejecutada
        if tool_name != "similar_files":
            self.tools_executed_after_similarity.append({
                "tool": tool_name,
                "timestamp": datetime.now(),
                "impact": TOOL_IMPACT_ON_FILES.get(tool_name, "unknown")
            })
        
        # Invalidar análisis de "Archivos similares" si está activo
        if self.similarity_results:
            self._invalidate_similarity_analysis()
        
        # Iniciar re-análisis automático de herramientas rápidas
        self._trigger_automatic_reanalysis()
    
    def _trigger_automatic_reanalysis(self):
        """Inicia re-análisis automático de herramientas rápidas."""
        # Mostrar overlay
        self._show_reanalysis_overlay()
        
        # Crear worker
        self.reanalysis_worker = WorkspaceReanalysisWorker(self.current_workspace_path)
        
        # Conectar señales
        self.reanalysis_worker.progress_updated.connect(
            self._on_reanalysis_progress_updated
        )
        self.reanalysis_worker.analysis_completed.connect(
            self._on_reanalysis_completed
        )
        self.reanalysis_worker.analysis_error.connect(
            self._on_reanalysis_error
        )
        
        # Iniciar worker
        self.reanalysis_worker.start()
    
    def _show_reanalysis_overlay(self):
        """Muestra el overlay de re-análisis."""
        if not self.reanalysis_overlay:
            self.reanalysis_overlay = ReanalysisOverlay(self)
            self.reanalysis_overlay.setGeometry(self.rect())
        
        self.reanalysis_overlay.show_overlay()
    
    def _on_reanalysis_progress_updated(self, tool_name: str, current: int, total: int):
        """Actualiza el progreso del re-análisis."""
        if self.reanalysis_overlay:
            self.reanalysis_overlay.update_progress(tool_name, current, total)
    
    def _on_reanalysis_completed(self, results: dict):
        """Maneja la finalización del re-análisis."""
        # Ocultar overlay
        if self.reanalysis_overlay:
            self.reanalysis_overlay.hide_overlay()
        
        # Actualizar todas las cards con nuevos resultados
        self._update_all_cards_with_results(results)
        
        # Calcular tiempo total
        # (Opcional: registrar tiempo para mostrarlo en toast)
        
        # Mostrar notificación de éxito
        self._show_success_toast("✓ Análisis actualizado")
    
    def _on_reanalysis_error(self, tool_name: str, error_message: str):
        """Maneja errores durante el re-análisis."""
        print(f"Error en re-análisis de {tool_name}: {error_message}")
        # Opcional: Log o mostrar advertencia discreta
    
    def _update_all_cards_with_results(self, results: dict):
        """
        Actualiza todas las cards con los nuevos resultados.
        
        Args:
            results: Dict con {tool_name: analysis_results}
        """
        for tool_name, result in results.items():
            if "error" in result:
                continue
            
            # Actualizar card correspondiente
            card = self.tool_cards.get(tool_name)
            if card:
                self._update_card_with_result(card, tool_name, result)
    
    def _update_card_with_result(self, card, tool_name: str, result):
        """Actualiza una card individual con nuevos resultados."""
        # Implementación específica según cada herramienta
        # Ejemplo para "exact_copies":
        if tool_name == "exact_copies":
            card.set_info_lines([
                (f"✓ {result.group_count} grupos detectados", "check-circle", "#4CAF50"),
                (f"💾 {self._format_size(result.recoverable_space)} recuperables", "harddisk", "#757575")
            ])
        
        # Repetir para cada herramienta...
    
    # ==========================================
    # GESTIÓN DE "ARCHIVOS SIMILARES" OBSOLETOS
    # ==========================================
    
    def _invalidate_similarity_analysis(self):
        """Invalida el análisis de archivos similares."""
        if not self.similarity_results:
            return
        
        # Guardar snapshot de resultados antiguos
        self.similarity_results_snapshot = {
            "timestamp": self.similarity_analysis_timestamp,
            "results": self.similarity_results.copy() if hasattr(self.similarity_results, 'copy') else self.similarity_results,
            "reason": "Archivos modificados por otras herramientas",
            "tools_executed": [t["tool"] for t in self.tools_executed_after_similarity]
        }
        
        # Marcar como obsoleto
        if hasattr(self.similarity_results, 'is_stale'):
            self.similarity_results.is_stale = True
        
        # Actualizar UI de la card
        self._update_similar_files_card_stale()
    
    def _update_similar_files_card_stale(self):
        """Actualiza la card de "Archivos similares" al estado obsoleto."""
        card = self.tool_cards.get("similar_files")
        if not card:
            return
        
        # Cambiar estado visual a "obsoleto"
        tools_list = ", ".join(self.similarity_results_snapshot["tools_executed"][:3])
        if len(self.similarity_results_snapshot["tools_executed"]) > 3:
            tools_list += "..."
        
        # Calcular tiempo transcurrido
        elapsed = datetime.now() - self.similarity_results_snapshot["timestamp"]
        elapsed_minutes = int(elapsed.total_seconds() / 60)
        
        # Actualizar card
        card.set_state_stale(
            message=f"Se ejecutaron: {tools_list}",
            timestamp=f"hace {elapsed_minutes} min",
            old_results=self.similarity_results_snapshot["results"]
        )
    
    def _open_similarity_dialog(self, results):
        """Abre el diálogo de archivos similares con validación."""
        # Verificar si el análisis está obsoleto
        if hasattr(results, 'is_stale') and results.is_stale:
            # Mostrar opciones al usuario
            reply = self._show_stale_results_dialog()
            
            if reply == "reanalyze":
                # Reanalizar
                self._on_similar_files_clicked()
                return
            elif reply == "cancel":
                return
            # Si reply == "view", continuar abajo
        
        # Validación rápida de archivos
        is_valid, reason = self._validate_similarity_analysis_quick(results)
        
        if not is_valid:
            reply = self._show_invalid_analysis_dialog(reason)
            
            if reply == "reanalyze":
                self._on_similar_files_clicked()
                return
            elif reply == "cancel":
                return
        
        # Abrir diálogo normalmente
        from ui.dialogs.similarfilesdialog import SimilarFilesDialog
        
        dialog = SimilarFilesDialog(
            self,
            results,
            is_stale=hasattr(results, 'is_stale') and results.is_stale
        )
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Se ejecutaron acciones, re-analizar
            self._on_tool_action_completed("similar_files", True)
    
    def _show_stale_results_dialog(self) -> str:
        """
        Muestra diálogo cuando el análisis está obsoleto.
        
        Returns:
            "view", "reanalyze" o "cancel"
        """
        tools_list = "\n• ".join(self.similarity_results_snapshot["tools_executed"])
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Análisis obsoleto")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(
            "⚠️ Los resultados de \"Archivos similares\" pueden estar desactualizados."
        )
        msg_box.setInformativeText(
            f"Herramientas ejecutadas desde el último análisis:\n\n"
            f"• {tools_list}\n\n"
            f"Realizado: {self.similarity_results_snapshot['timestamp'].strftime('%H:%M')}\n\n"
            "¿Deseas ver los resultados antiguos o reanalizar?"
        )
        
        view_btn = msg_box.addButton("Ver resultados antiguos", QMessageBox.ButtonRole.YesRole)
        reanalyze_btn = msg_box.addButton("Reanalizar ahora (recomendado)", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == view_btn:
            return "view"
        elif msg_box.clickedButton() == reanalyze_btn:
            return "reanalyze"
        else:
            return "cancel"
    
    def _show_invalid_analysis_dialog(self, reason: str) -> str:
        """Muestra diálogo cuando se detectan cambios críticos."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Análisis desactualizado")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(f"⚠️ {reason}")
        msg_box.setInformativeText(
            "Se recomienda reanalizar para obtener resultados precisos.\n\n"
            "¿Deseas reanalizar ahora?"
        )
        
        reanalyze_btn = msg_box.addButton("Reanalizar ahora", QMessageBox.ButtonRole.AcceptRole)
        cancel_btn = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == reanalyze_btn:
            return "reanalyze"
        else:
            return "cancel"
    
    def _validate_similarity_analysis_quick(self, results) -> tuple[bool, str]:
        """
        Validación rápida del análisis (< 1 segundo).
        Verifica una muestra aleatoria de archivos.
        
        Returns:
            (is_valid, reason): Tupla con validez y razón si no es válido
        """
        import random
        from pathlib import Path
        
        if not hasattr(results, 'all_files') or not results.all_files:
            return (True, "")
        
        # Muestreo aleatorio de 50 archivos
        sample_size = min(50, len(results.all_files))
        sample = random.sample(results.all_files, sample_size)
        
        missing = sum(1 for f in sample if not Path(f).exists())
        missing_pct = (missing / sample_size) * 100
        
        if missing_pct > 15:
            return (False, f"Se eliminaron aproximadamente {missing_pct:.0f}% de los archivos analizados")
        
        return (True, "")
    
    def _show_success_toast(self, message: str):
        """Muestra notificación toast de éxito."""
        # Implementar toast notification (opcional)
        # Puede usar QLabel flotante con timer o librería externa
        print(message)  # Placeholder
    
    def _format_size(self, bytes_size: int) -> str:
        """Formatea tamaño de bytes a formato legible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} TB"
```

**Modificar método de cierre de diálogos**:

Cuando cada diálogo se cierra tras ejecutar acciones, debe llamar a `_on_tool_action_completed`:

```python
def _on_live_photos_dialog_closed(self, result):
    """Callback cuando se cierra el diálogo de Live Photos."""
    if result == QDialog.DialogCode.Accepted:
        # El usuario ejecutó acciones
        self._on_tool_action_completed("live_photos", actions_executed=True)

def _on_exact_copies_dialog_closed(self, result):
    """Callback cuando se cierra el diálogo de Copias exactas."""
    if result == QDialog.DialogCode.Accepted:
        self._on_tool_action_completed("exact_copies", actions_executed=True)

# ... Repetir para cada herramienta ...
```


***

## PARTE 5: Modificaciones en ToolCard

### Archivo: `ui/widgets/toolcard.py` (modificar)

**Añadir método para estado "obsoleto"**:

```python
class ToolCard(QFrame):
    # ... código existente ...
    
    def set_state_stale(self, message: str, timestamp: str, old_results):
        """
        Marca la card como obsoleta.
        
        Args:
            message: Mensaje explicativo (ej: "Se ejecutaron: Copias exactas...")
            timestamp: Tiempo transcurrido (ej: "hace 12 min")
            old_results: Resultados antiguos para mostrar
        """
        # Cambiar icono de estado
        self.status_icon.setPixmap(
            icon_manager.get_icon("alert", 16, "#FF9800").pixmap(16, 16)
        )
        
        # Actualizar texto de estado
        self.status_label.setText("⚠️ Análisis obsoleto")
        self.status_label.setStyleSheet("color: #FF9800; font-weight: 600;")
        
        # Mostrar mensaje explicativo
        self.info_label.setText(
            f"{message}\n\n"
            f"Último análisis: {timestamp}"
        )
        
        # Cambiar botón a dos opciones
        self.clear_buttons()
        
        view_btn = QPushButton("Ver resultados")
        view_btn.setObjectName("secondary_button")
        view_btn.clicked.connect(lambda: self._on_view_stale_clicked(old_results))
        
        reanalyze_btn = QPushButton("Reanalizar")
        reanalyze_btn.setObjectName("primary_button")
        reanalyze_btn.clicked.connect(self._on_reanalyze_clicked)
        
        self.button_layout.addWidget(view_btn)
        self.button_layout.addWidget(reanalyze_btn)
    
    def clear_buttons(self):
        """Elimina todos los botones actuales."""
        while self.button_layout.count():
            item = self.button_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
```


***

## PARTE 6: Diálogo de Archivos Similares con Estado Obsoleto

### Archivo: `ui/dialogs/similarfilesdialog.py` (modificar)

**Añadir parámetro `is_stale` al constructor**:

```python
class SimilarFilesDialog(QDialog):
    def __init__(self, parent=None, results=None, is_stale: bool = False):
        self.is_stale = is_stale
        super().__init__(parent)
        self.results = results
        self._setup_ui()
        
        if is_stale:
            self._show_stale_banner()
    
    def _show_stale_banner(self):
        """Muestra banner de advertencia en la parte superior del diálogo."""
        banner = QFrame()
        banner.setObjectName("stale_banner")
        banner.setFixedHeight(60)
        
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(20, 12, 20, 12)
        
        # Icono de advertencia
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, "alert-circle", color="#FF9800", size=24)
        
        # Texto
        text_label = QLabel(
            "⚠️ ADVERTENCIA: Resultados de análisis obsoleto\n"
            "Algunos archivos pueden haber sido eliminados o movidos."
        )
        text_label.setObjectName("stale_banner_text")
        
        # Botón reanalizar
        reanalyze_btn = QPushButton("Reanalizar")
        reanalyze_btn.setObjectName("reanalyze_button")
        reanalyze_btn.clicked.connect(self._on_reanalyze_from_dialog)
        
        banner_layout.addWidget(icon_label)
        banner_layout.addWidget(text_label)
        banner_layout.addStretch()
        banner_layout.addWidget(reanalyze_btn)
        
        # Insertar al inicio del layout principal
        self.main_layout.insertWidget(0, banner)
        
        # Estilos
        banner.setStyleSheet("""
            QFrame#stale_banner {
                background-color: rgba(255, 152, 0, 0.1);
                border: 1px solid rgba(255, 152, 0, 0.3);
                border-radius: 8px;
            }
            QLabel#stale_banner_text {
                font-size: 13px;
                color: #757575;
                line-height: 1.4;
            }
            QPushButton#reanalyze_button {
                background-color: #FF9800;
                color: #FFFFFF;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton#reanalyze_button:hover {
                background-color: #F57C00;
            }
        """)
    
    def _on_reanalyze_from_dialog(self):
        """Cierra el diálogo y activa re-análisis."""
        self.reject()
        # Emitir señal para que Stage3Window inicie re-análisis
        # (O llamar directamente al método del parent si está disponible)
```

**Marcar archivos no disponibles**:

En la lista de archivos similares, verificar existencia:

```python
def _populate_file_list(self, group):
    """Puebla la lista con archivos del grupo."""
    for file_path in group.files:
        item = QListWidgetItem()
        
        # Verificar si el archivo existe
        if not Path(file_path).exists():
            item.setText(f"✗ {Path(file_path).name} - Archivo no encontrado")
            item.setForeground(QColor("#F44336"))  # Rojo
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)  # Deshabilitar
        else:
            item.setText(f"✓ {Path(file_path).name}")
        
        self.file_list.addItem(item)
```


***

## PARTE 7: Integración Completa

### Flujo de Ejecución Completo

**Escenario: Usuario elimina copias exactas**

1. Usuario abre "Copias exactas" → `ExactCopiesDialog`
2. Usuario selecciona y elimina 50 archivos → Click "Confirmar"
3. Dialog ejecuta eliminación y se cierra con `QDialog.Accepted`
4. **Trigger**: `_on_exact_copies_dialog_closed(QDialog.Accepted)`
5. **Llamada**: `_on_tool_action_completed("exact_copies", actions_executed=True)`
6. **Acciones automáticas**:
    - Registra herramienta ejecutada
    - Invalida análisis de "Archivos similares" (si existe)
    - Llama a `_trigger_automatic_reanalysis()`
7. **Re-análisis automático**:
    - Crea `WorkspaceReanalysisWorker`
    - Muestra `ReanalysisOverlay` (no bloqueante)
    - Ejecuta análisis de 5 herramientas rápidas en background
    - Actualiza progreso: "Analizando: Live Photos (1/5)"
    - Continúa con todas las herramientas
8. **Finalización**:
    - Oculta overlay
    - Actualiza todas las cards con nuevos resultados
    - Muestra toast: "✓ Análisis actualizado (2.8s)"
9. **Card de "Archivos similares"**:
    - Cambia a estado "obsoleto" ⚠️
    - Muestra: "Se ejecutaron: Copias exactas (hace 1 min)"
    - Botones: [Ver resultados] [Reanalizar]

**Escenario: Usuario intenta abrir "Archivos similares" obsoleto**

1. Usuario hace clic en card de "Archivos similares" (obsoleta)
2. **Validación rápida**: Muestra aleatoria de 50 archivos
3. **Si cambios críticos** (>15% eliminados):
    - Muestra diálogo: "⚠️ Se eliminaron ~20% de archivos"
    - Opciones: [Reanalizar ahora] [Cancelar]
4. **Si solo obsoleto** (sin cambios críticos):
    - Muestra diálogo: "Herramientas ejecutadas: Copias exactas..."
    - Opciones: [Ver resultados antiguos] [Reanalizar ahora] [Cancelar]
5. **Si elige "Ver resultados antiguos"**:
    - Abre `SimilarFilesDialog` con banner de advertencia
    - Archivos eliminados marcados en rojo
6. **Si elige "Reanalizar ahora"**:
    - Abre `SimilarFilesConfigDialog`
    - Ejecuta análisis completo (bloqueante)
    - Actualiza card al finalizar

***

## PARTE 8: Testing y Validación

### Checklist de Validación

Después de implementar, verificar:

- [ ] Re-análisis se ejecuta automáticamente tras acciones destructivas
- [ ] Overlay aparece y muestra progreso correcto
- [ ] Overlay no bloquea visualización de cards
- [ ] Cards se actualizan con nuevos resultados
- [ ] Card de "Archivos similares" se marca como obsoleta correctamente
- [ ] Toast de éxito aparece al finalizar
- [ ] Validación rápida detecta archivos eliminados
- [ ] Diálogo de advertencia funciona correctamente
- [ ] Opción "Ver resultados antiguos" funciona
- [ ] Banner de advertencia aparece en diálogo
- [ ] Archivos eliminados se marcan en rojo
- [ ] Opción "Reanalizar" funciona desde card y desde diálogo
- [ ] No hay memory leaks (workers se limpian correctamente)
- [ ] Animaciones son suaves (overlay, spinner)
- [ ] Tiempos de re-análisis son aceptables (< 5 segundos)


### Casos de Prueba

**Test 1: Re-análisis tras eliminación**

```
1. Seleccionar workspace con 1000 archivos
2. Ejecutar "Copias exactas" → Eliminar 20 archivos
3. Verificar: Overlay aparece
4. Verificar: Progreso 1/5 → 5/5
5. Verificar: Cards actualizadas
6. Verificar: Toast "✓ Análisis actualizado"
```

**Test 2: "Archivos similares" obsoleto**

```
1. Analizar archivos similares (sensibilidad 85%)
2. Ejecutar "Copias exactas" → Eliminar 50 archivos
3. Verificar: Card "Archivos similares" → ⚠️ obsoleto
4. Click en card
5. Verificar: Diálogo de advertencia aparece
6. Elegir "Ver resultados antiguos"
7. Verificar: Banner de advertencia en diálogo
8. Verificar: Archivos eliminados marcados en rojo
```

**Test 3: Validación rápida crítica**

```
1. Analizar archivos similares
2. Eliminar manualmente 30% de archivos del workspace
3. Click en card "Archivos similares"
4. Verificar: Diálogo "Se eliminaron ~30% de archivos"
5. Verificar: Recomendación de reanalizar
```


***

## PARTE 9: Consideraciones Técnicas

### Performance

- **Re-análisis rápido**: Debe completarse en < 5 segundos para 5000 archivos
- **Validación rápida**: Debe completarse en < 1 segundo (muestra de 50 archivos)
- **Overlay**: Animaciones a 60 FPS (usar QPropertyAnimation)
- **Threading**: Nunca bloquear el hilo principal


### Memoria

- Liberar workers tras finalización: `self.reanalysis_worker.deleteLater()`
- No mantener múltiples snapshots de resultados antiguos
- Limpiar overlay al ocultar: `self.reanalysis_overlay.deleteLater()`


### Errores

- Si un detector falla, continuar con los demás
- Loggear errores sin mostrar al usuario (a menos que sea crítico)
- Si re-análisis falla completamente, mostrar toast de error


### Escalabilidad

- Fácil añadir nuevas herramientas al sistema
- Configuración centralizada en `config.py`
- Workers desacoplados de UI

***

## PARTE 10: Resumen de Archivos a Crear/Modificar

### Archivos Nuevos

1. `ui/widgets/reanalysisoverlay.py` - Overlay de progreso
2. `ui/dialogs/similarfilesconfigdialog.py` - Diálogo de configuración (ya creado antes)
3. `ui/dialogs/similarfilesprogressdialog.py` - Diálogo de progreso (ya creado antes)

### Archivos a Modificar

1. `config.py` - Añadir constantes de clasificación
2. `ui/workers.py` - Añadir `WorkspaceReanalysisWorker`
3. `ui/stages/stage3window.py` - Añadir sistema de re-análisis
4. `ui/widgets/toolcard.py` - Añadir método `set_state_stale()`
5. `ui/dialogs/similarfilesdialog.py` - Añadir soporte para datos obsoletos

### Documentación

- Actualizar `README.md` con descripción del sistema de re-análisis
- Actualizar `CHANGELOG.md` con nueva funcionalidad

***

## Fecha de Implementación

**2025-11-08**

**Objetivo**: Sistema de re-análisis inteligente que mantiene datos actualizados sin interrumpir el flujo del usuario, con tratamiento especial para análisis costosos.
<span style="display:none">[^1][^2][^3][^4]</span>

<div align="center">⁂</div>

[^1]: https://www.youtube.com/watch?v=5a7H7y0a5yc

[^2]: https://www.youtube.com/watch?v=KsxN59pLzlc

[^3]: https://www.youtube.com/watch?v=SaBwpCIV6PQ

[^4]: https://www.youtube.com/watch?v=imL4sBSFcNc

