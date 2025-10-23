"""
Funciones auxiliares reutilizables para la UI extraídas de `main_window.py`.
Cada función recibe la instancia principal `window` cuando necesita acceder a
atributos o widgets de la ventana.
"""
from pathlib import Path
import traceback

from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QTextEdit, QLineEdit, QButtonGroup,
    QRadioButton
)
from PyQt5.QtCore import Qt, QTimer

import config
from ui import styles

try:
    from ui import tabs as _tabs_module
except Exception:
    _tabs_module = None


from ui.components.progress_bar import (
    create_progress_group as create_progress_bar,
    show_progress,
    hide_progress,
)


def service_available(window, attr_name: str) -> bool:
    return hasattr(window, attr_name) and getattr(window, attr_name) is not None

def update_tab_details(window, results):
    if results.get('renaming'):
        ren = results['renaming']
        html = f"""
                <p><strong>Total archivos:</strong> {ren.get('total_files', 0):,}</p>
                <p><strong>✅ Ya renombrados:</strong> {ren.get('already_renamed', 0):,}</p>
                <p><strong>📝 A renombrar:</strong> {ren.get('need_renaming', 0):,}</p>
                <p><strong>⚠️ No procesables:</strong> {ren.get('cannot_process', 0):,}</p>
                <p><strong>🔄 Conflictos:</strong> {ren.get('conflicts', 0):,}</p>
            """
        if ren.get('need_renaming', 0) > 0:
            info_html = f"""
                    <div style='margin-top:10px; padding:10px; border-radius:8px; background:#f8f9fa; color:#6c757d;'>
                        <strong>Información:</strong>
                        <div>Al aceptar el diálogo de preview se ejecutará el renombrado automáticamente.</div>
                        <div>Marca la opción de backup en el diálogo si deseas crear una copia antes de renombrar.</div>
                    </div>
                """
            html += info_html
        window.rename_details.setHtml(html)

    if results.get('live_photos'):
        lp = results['live_photos']
        total_groups = len(lp.get('groups', []))
        total_space = sum(group.get('total_size', 0) for group in lp.get('groups', []))
        space_to_free = sum(group.get('video_size', 0) for group in lp.get('groups', []))
        html = f"""
                <p><strong>📱 Live Photos encontrados:</strong> {total_groups:,}</p>
                <p><strong>💾 Espacio total:</strong> {format_size(total_space)}</p>
                <p><strong>💾 Espacio a liberar (mantener imagen):</strong> {format_size(space_to_free)}</p>
            """
        window.lp_details.setHtml(html)

    if results.get('unification'):
        unif = results['unification']
        total_size = unif.get('total_size_to_move', 0)
        html = f"""
                <p><strong>📁 Subdirectorios:</strong> {len(unif.get('subdirectories', {})):,}</p>
                <p><strong>📄 Archivos a mover:</strong> {unif.get('total_files_to_move', 0):,}</p>
                <p><strong>💾 Tamaño total:</strong> {format_size(total_size)}</p>
                <p><strong>⚠️ Conflictos potenciales:</strong> {unif.get('potential_conflicts', 0):,}</p>
            """
        window.unif_details.setHtml(html)

    if results.get('heic'):
        heic = results['heic']
        savings_jpg = heic.get('potential_savings_keep_jpg', 0)
        savings_heic = heic.get('potential_savings_keep_heic', 0)
        html = f"""
                <p><strong>♻️ Pares detectados:</strong> {heic.get('total_duplicates', 0):,}</p>
                <p><strong>🖼️ Archivos HEIC:</strong> {heic.get('total_heic_files', 0):,}</p>
                <p><strong>📸 Archivos JPG:</strong> {heic.get('total_jpg_files', 0):,}</p>
                <p><strong>💾 Ahorro (mantener JPG):</strong> {format_size(savings_jpg)}</p>
                <p><strong>💾 Ahorro (mantener HEIC):</strong> {format_size(savings_heic)}</p>
            """
        window.heic_details.setHtml(html)



def show_results_html(window, html: str, show_generic_status: bool = False):
    try:
        if show_generic_status:
            try:
                window.logger.info('Operación completada — revisa el log para detalles')
            except Exception:
                try:
                    window.setWindowTitle(f"{config.config.APP_NAME} — Operación completada")
                except Exception:
                    pass
    except Exception:
        pass


def format_size(bytes_size):
    """Formatea un tamaño en bytes a una cadena legible.

    Soporta Bytes, KB, MB y GB. Usa potencias de 1024.
    Maneja valores None o negativos de forma segura.
    """
    try:
        if bytes_size is None:
            return "0 B"
        size = float(bytes_size)
    except Exception:
        return "0 B"

    if size < 0:
        # Mantener el signo y formatear el absoluto
        return f"-{format_size(abs(size))}"

    # Bytes
    if size < 1024:
        return f"{int(size)} B"

    # Kilobytes
    kb = size / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"

    # Megabytes
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"

    # Gigabytes and above
    gb = mb / 1024
    return f"{gb:.2f} GB"


def reset_analysis_ui(window, reinsert_analyze=True):
    window.analyze_btn.setText("🔍 Seleccionar Directorio y Analizar")
    window.analyze_btn.setEnabled(True)

    if hasattr(window, 'reanalyze_btn'):
        window.reanalyze_btn.setVisible(False)
    if hasattr(window, 'change_dir_btn'):
        window.change_dir_btn.setVisible(False)

    if reinsert_analyze:
        try:
            if window.analyze_btn.parent() is None:
                window.actions_layout.addWidget(window.analyze_btn)
            window.analyze_btn.setVisible(True)
        except Exception:
            pass

    window.summary_panel.setVisible(False)
    window.tabs_widget.setVisible(False)

    window.preview_rename_btn.setEnabled(False)
    window.exec_lp_btn.setEnabled(False)
    window.exec_unif_btn.setEnabled(False)
    window.exec_heic_btn.setEnabled(False)

    if hasattr(window, 'rename_details'):
        window.rename_details.clear()
    if hasattr(window, 'norm_details'):
        window.norm_details.clear()
    window.lp_details.clear()
    window.unif_details.clear()
    window.heic_details.clear()

    if hasattr(window, 'directory_edit') and reinsert_analyze:
        window.directory_edit.clear()
        window.directory_edit.setPlaceholderText("Selecciona un directorio para analizar...")

    try:
        if 'images' in window.stats_labels:
            window.stats_labels['images'].setText("🖼️ Imágenes: —")
        if 'videos' in window.stats_labels:
            window.stats_labels['videos'].setText("🎥 Videos: —")
        if 'total' in window.stats_labels:
            window.stats_labels['total'].setText("📊 Total: —")
    except Exception:
        pass

    window.analysis_results = None
    window.last_analyzed_directory = None

    try:
        try:
            window.logger.info("Directorio cambiado: análisis anterior limpiado")
        except Exception:
            try:
                window.setWindowTitle(f"{config.config.APP_NAME} — Análisis limpiado")
            except Exception:
                pass
    except Exception:
        try:
            window.logger.info("Directorio cambiado: análisis anterior limpiado")
        except Exception:
            pass

    window.logger.info("UI reiniciada tras cambio de directorio")
