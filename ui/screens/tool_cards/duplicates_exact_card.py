"""
Crea la card de Duplicados Exactos (Copias Exactas) para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard
from utils.format_utils import format_size


def create_duplicates_exact_card(analysis_results, on_click_callback) -> ToolCard:
    """
    Crea la card de Duplicados Exactos

    Args:
        analysis_results: Objeto con los resultados del análisis
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    # Verificar si hay análisis disponible
    has_analysis = (hasattr(analysis_results, 'duplicates') and 
                   analysis_results.duplicates is not None)
    
    card = ToolCard(
        icon_name='content-copy',
        title='Copias Exactas',
        description='Detecta archivos idénticos y ayuda a eliminar copias innecesarias. '
                   'Garantiza que no está borrando una foto "parecida", sino exactamente el mismo archivo repetido en diferentes carpetas (auqnue tenga disitnto nombre)',
        action_text='Gestionar ahora' if has_analysis else 'Analizar ahora'
    )


    # Configurar estado según datos
    if has_analysis:
        dup_data = analysis_results.duplicates
        if dup_data.total_duplicates > 0:
            size_text = f"~{format_size(dup_data.space_wasted)} desperdiciados"
            card.set_status_with_results(
                f"{dup_data.total_duplicates} archivos duplicados encontrados",
                size_text,
                badge_count=dup_data.total_duplicates
            )
        else:
            card.set_status_no_results("No se encontraron archivos duplicados")
    else:
        # Estado pendiente de análisis
        card.set_status_pending("Analizar para detectar copias exactas")

    card.clicked.connect(lambda: on_click_callback('duplicates_exact'))
    return card
