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
from config import Config
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
    
    Args:
        results: dict con claves 'renaming', 'live_photos', 'organization', 'heic', 'duplicates'
                 donde cada valor es una dataclass correspondiente
    """
    
    if results.get('renaming'):
        ren = results['renaming']
        # ren es un RenameAnalysisResult (dataclass)
        
        stats = {
            'Total archivos': ren.total_files,
            'Ya renombrados': ren.already_renamed,
            'A renombrar': ren.need_renaming,
            'No procesables': ren.cannot_process,
        }
        
        html = generate_stats_html(stats)
        
        if ren.need_renaming > 0:
            extra_stats = {
                'Conflictos': ren.conflicts,
            }
            html += "\n\n---\n\n" + generate_stats_html(extra_stats)
        
        window.rename_details.setHtml(html)
    
    if results.get('live_photos'):
        lp = results['live_photos']
        
        # lp puede ser un dict (workers.py construye dicts actualmente)
        # Necesitamos manejar ambos casos durante la transición
        if isinstance(lp, dict):
            total_groups = lp.get('live_photos_found')
            if total_groups is None:
                groups_list = lp.get('groups') or lp.get('detailed_analysis', {}).get('groups') or []
                total_groups = len(groups_list) if groups_list else 0
            
            total_space = lp.get('total_space', 0)
            space_to_free = lp.get('space_to_free', 0)
            
            if total_space == 0 and 'detailed_analysis' in lp:
                analysis = lp['detailed_analysis']
                total_space = analysis.get('total_size', 0)
            
            cleanup_mode = lp.get('cleanup_mode', '')
        else:
            # Es una dataclass LivePhotoCleanupAnalysisResult
            total_groups = lp.live_photos_found
            total_space = lp.total_space
            space_to_free = lp.space_to_free
            cleanup_mode = lp.cleanup_mode
        
        stats = {
            'Live Photos encontrados': total_groups,
            'Espacio total': format_size(total_space),
            'Espacio a liberar': format_size(space_to_free),
        }
        
        if cleanup_mode:
            mode_names = {
                'keep_image': 'mantener imagen',
                'keep_video': 'mantener video',
                'keep_larger': 'mantener más grande',
                'keep_smaller': 'mantener más pequeño'
            }
            if cleanup_mode in mode_names:
                stats['Modo'] = mode_names[cleanup_mode]
        
        html = generate_stats_html(stats)
        window.lp_details.setHtml(html)
    
    if results.get('organization'):
        org = results['organization']
        # org es un OrganizationAnalysisResult (dataclass)
        
        org_type_labels = {
            'to_root': 'Mover a raíz',
            'by_month': 'Por meses (YYYY_MM)',
            'whatsapp_separate': 'Separar WhatsApp'
        }
        org_type_label = org_type_labels.get(org.organization_type, org.organization_type)
        
        stats = {
            'Tipo de organización': org_type_label,
            'Subdirectorios': len(org.subdirectories),
            'Archivos a mover': org.total_files_to_move,
            'Tamaño total': format_size(org.total_size_to_move),
            'Conflictos potenciales': org.potential_conflicts,
        }
        
        if org.folders_to_create:
            folders_list = org.folders_to_create
            stats['Carpetas a crear'] = f"{len(folders_list)} ({', '.join(folders_list[:5])}{'...' if len(folders_list) > 5 else ''})"
        
        html = generate_stats_html(stats)
        window.org_details.setHtml(html)
    
    if results.get('heic'):
        heic = results['heic']
        # heic es un HeicAnalysisResult (dataclass)
        
        stats = {
            'Pares detectados': heic.total_duplicates,
            'Archivos HEIC': heic.heic_files,
            'Archivos JPG': heic.jpg_files,
            'Ahorro (mantener JPG)': format_size(heic.potential_savings_keep_jpg),
            'Ahorro (mantener HEIC)': format_size(heic.potential_savings_keep_heic),
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
    window.analyze_btn.setText("Seleccionar Directorio y Analizar")
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
    
    # Ocultar icono de carpeta (se muestra solo tras análisis)
    if hasattr(window, 'top_bar') and hasattr(window.top_bar, 'hide_folder_icon'):
        window.top_bar.hide_folder_icon()
    
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
    
    # Ocultar botones de duplicados (prevenir mostrar resultados de directorio anterior)
    if hasattr(window, 'delete_exact_duplicates_btn'):
        window.delete_exact_duplicates_btn.setVisible(False)
    if hasattr(window, 'review_similar_btn'):
        window.review_similar_btn.setVisible(False)
    
    # Limpiar resultados de duplicados del detector
    if hasattr(window, 'duplicate_detector'):
        window.duplicate_detector.clear_last_results()
    
    # Limpiar áreas de detalles de duplicados (bloques separados)
    if hasattr(window, 'exact_details_text'):
        window.exact_details_text.clear()
        window.exact_details_text.setVisible(False)
    
    if hasattr(window, 'similar_details_text'):
        window.similar_details_text.clear()
        window.similar_details_text.setVisible(False)
    
    # Log
    window.logger.info("UI reiniciada tras cambio de directorio")