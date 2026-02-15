"""
Crea la card de Archivos Similares para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard
from ui.tools_definitions import TOOL_DUPLICATES_SIMILAR
from utils.format_utils import format_size


def create_duplicates_similar_card(analysis_results, on_click_callback) -> ToolCard:
    """
    Crea la card de Archivos similares

    Args:
        analysis_results: Objeto con los resultados del análisis
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    # Verificar si hay análisis disponible
    has_analysis = (hasattr(analysis_results, 'duplicates_similar') and 
                   analysis_results.duplicates_similar is not None)
    
    card = ToolCard(
        icon_name=TOOL_DUPLICATES_SIMILAR.icon_name,
        title=TOOL_DUPLICATES_SIMILAR.title,
        description=TOOL_DUPLICATES_SIMILAR.long_description,
        action_text='Gestionar ahora' if has_analysis else 'Analizar ahora'
    )

    # Configurar estado según datos
    if has_analysis:
        similar_data = analysis_results.duplicates_similar
        if hasattr(similar_data, 'perceptual_hashes'):
            if len(similar_data.perceptual_hashes) > 0:
                # Intentar usar resultado cacheado para no bloquear la UI.
                # get_groups() con BK-Tree puede tardar ~50s para 50K+ archivos,
                # así que NUNCA lo llamamos desde el hilo principal de la UI.
                cached_result = (
                    similar_data.get_last_groups_result() 
                    if hasattr(similar_data, 'get_last_groups_result') 
                    else None
                )
                if cached_result and cached_result.total_similar > 0:
                    size_text = f"~{format_size(cached_result.space_recoverable)} desperdiciados"
                    card.set_status_with_results(
                        f"{cached_result.total_groups} grupos de archivos similares encontrados",
                        size_text,
                        badge_count=cached_result.total_similar
                    )
                elif cached_result and cached_result.total_similar == 0:
                    card.set_status_no_results("No se encontraron archivos similares")
                else:
                    # Hay hashes pero no se ha hecho clustering aún (o no hay cache)
                    # Mostrar info ligera sin bloquear la UI
                    from utils.format_utils import format_file_count
                    card.set_status_pending(
                        f"{format_file_count(len(similar_data.perceptual_hashes))} analizados · Clic para agrupar"
                    )
            else:
                card.set_status_no_results("No se encontraron archivos para analizar")
        else:
            card.set_status_no_results("No se encontraron archivos similares")
    else:
        # Estado pendiente de análisis
        card.set_status_pending("Analizar para detectar archivos similares")

    card.clicked.connect(lambda: on_click_callback('duplicates_similar'))
    return card
