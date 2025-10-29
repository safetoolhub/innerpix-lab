"""
Funciones auxiliares reutilizables para la UI extraídas de `main_window.py`.
"""
from pathlib import Path
import traceback
from PyQt6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QTextEdit, QLineEdit, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, QTimer
import config
from ui import styles
from ui import tabs as _tabs_module

from utils.format_utils import format_size, generate_stats_html


def service_available(window, attr_name: str) -> bool:
    """Determina si una característica o pestaña debe considerarse disponible.

    Consulta el TabController centralizado en window.tab_controller y
    su tab_availability. Si no existe el controlador o el diccionario,
    se asume que la característica está disponible (True).

    Args:
        window: instancia principal de la app (MainWindow)
        attr_name: nombre lógico de la característica/pestaña (p.ej. 'heic_remover')

    Returns:
        bool: True si la característica está disponible, False en caso contrario.
    """
    tc = getattr(window, 'tab_controller', None)
    availability = None
    if tc is not None:
        availability = getattr(tc, 'tab_availability', None)
    if availability is None:
        return True
    return bool(availability.get(attr_name, True))


def update_tab_details(window, results):
    """
    Actualiza los detalles de cada pestaña con los resultados del análisis.
    """
    
    if results.get('renaming'):
        ren = results['renaming']
        
        stats = {
            '📊 Total archivos': ren.get('total_files', 0),
            '✅ Ya renombrados': ren.get('already_renamed', 0),
            '📝 A renombrar': ren.get('need_renaming', 0),
            '⚠️ No procesables': ren.get('cannot_process', 0),
        }
        
        html = generate_stats_html(stats)
        
        if ren.get('need_renaming', 0) > 0:
            extra_stats = {
                '🔄 Conflictos': ren.get('conflicts', 0),
            }
            html += "\n\n---\n\n" + generate_stats_html(extra_stats)
        
        window.rename_details.setHtml(html)
    
    if results.get('live_photos'):
        lp = results['live_photos']
        
        total_groups = lp.get('live_photos_found')
        if total_groups is None:
            groups_list = lp.get('groups') or lp.get('detailed_analysis', {}).get('groups') or []
            total_groups = len(groups_list) if groups_list else 0
        
        total_space = lp.get('total_space', 0)
        space_to_free = lp.get('space_to_free', 0)
        
        if total_space == 0 and 'detailed_analysis' in lp:
            analysis = lp['detailed_analysis']
            total_space = analysis.get('total_size', 0)
        
        stats = {
            '📱 Live Photos encontrados': total_groups,
            '💾 Espacio total': format_size(total_space),
            '💾 Espacio a liberar': format_size(space_to_free),
        }
        
        if 'cleanup_mode' in lp:
            mode_names = {
                'keep_image': 'mantener imagen',
                'keep_video': 'mantener video',
                'keep_larger': 'mantener más grande',
                'keep_smaller': 'mantener más pequeño'
            }
            mode = lp.get('cleanup_mode', '')
            if mode in mode_names:
                stats['🔧 Modo'] = mode_names[mode]
        
        html = generate_stats_html(stats)
        window.lp_details.setHtml(html)
    
    if results.get('organization'):
        org = results['organization']
        total_size = org.get('total_size_to_move', 0)
        
        org_type_labels = {
            'to_root': 'Mover a raíz',
            'by_month': 'Por meses (YYYY_MM)',
            'whatsapp_separate': 'Separar WhatsApp'
        }
        org_type = org.get('organization_type', 'to_root')
        org_type_label = org_type_labels.get(org_type, org_type)
        
        stats = {
            '🔧 Tipo de organización': org_type_label,
            '📁 Subdirectorios': len(org.get('subdirectories', {})),
            '📄 Archivos a mover': org.get('total_files_to_move', 0),
            '💾 Tamaño total': format_size(total_size),
            '⚠️ Conflictos potenciales': org.get('potential_conflicts', 0),
        }
        
        folders_to_create = org.get('folders_to_create', [])
        if folders_to_create:
            stats['📂 Carpetas a crear'] = f"{len(folders_to_create)} ({', '.join(folders_to_create[:5])}{'...' if len(folders_to_create) > 5 else ''})"
        
        html = generate_stats_html(stats)
        window.org_details.setHtml(html)
    
    if results.get('heic'):
        heic = results['heic']
        # heic es un HeicAnalysisResult (dataclass)
        savings_jpg = heic.potential_savings_keep_jpg
        savings_heic = heic.potential_savings_keep_heic
        
        stats = {
            '♻️ Pares detectados': heic.total_duplicates,
            '🖼️ Archivos HEIC': heic.heic_files,
            '📸 Archivos JPG': heic.jpg_files,
            '💾 Ahorro (mantener JPG)': format_size(savings_jpg),
            '💾 Ahorro (mantener HEIC)': format_size(savings_heic),
        }
        
        html = generate_stats_html(stats)
        window.heic_details.setHtml(html)

    if results.get('duplicates'):
        # No actualizar duplicates_details aquí - se maneja en show_initial_results_if_available
        # para mantener el formato rico de ResultsController
        pass


def show_results_html(window, html: str, show_generic_status: bool = False):
    """Muestra resultados HTML en el diálogo apropiado"""
    if show_generic_status and hasattr(window, 'logger'):
        window.logger.info('Operación completada — revisa el log para detalles')


def reset_analysis_ui(window, reinsert_analyze=True):
    """
    Resetea toda la interfaz al estado inicial.
    """
    # Resetear botón de análisis
    window.analyze_btn.setText("🔍 Seleccionar Directorio y Analizar")
    window.analyze_btn.setEnabled(True)
    
    # Ocultar botones adicionales
    if hasattr(window, 'reanalyze_btn'):
        window.reanalyze_btn.setVisible(False)
    if hasattr(window, 'change_dir_btn'):
        window.change_dir_btn.setVisible(False)
    
    if reinsert_analyze and window.analyze_btn.parent() is None:
        window.actions_layout.addWidget(window.analyze_btn)
        window.analyze_btn.setVisible(True)
    
    window.summary_panel.setVisible(False)
    window.tabs_widget.setVisible(False)
    
    # Deshabilitar botones de ejecución
    window.preview_rename_btn.setEnabled(False)
    window.exec_lp_btn.setEnabled(False)
    window.exec_org_btn.setEnabled(False)
    window.exec_heic_btn.setEnabled(False)
    
    if hasattr(window, 'rename_details'):
        window.rename_details.clear()
    if hasattr(window, 'norm_details'):
        window.norm_details.clear()
    
    window.lp_details.clear()
    window.org_details.clear()
    window.heic_details.clear()
    
    if hasattr(window, 'directory_edit') and reinsert_analyze:
        window.directory_edit.clear()
        window.directory_edit.setPlaceholderText("Selecciona un directorio para analizar...")
    
    # Resetear labels de estadísticas
    if 'images' in window.stats_labels:
        window.stats_labels['images'].setText("🖼️ Imágenes: —")
    if 'videos' in window.stats_labels:
        window.stats_labels['videos'].setText("🎥 Videos: —")
    if 'total' in window.stats_labels:
        window.stats_labels['total'].setText("📊 Total: —")
    
    # Limpiar datos de análisis
    window.analysis_results = None
    window.last_analyzed_directory = None
    
    # Log
    window.logger.info("UI reiniciada tras cambio de directorio")