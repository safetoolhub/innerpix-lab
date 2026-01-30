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
        # DuplicatesSimilarAnalysis contiene perceptual_hashes, necesitamos get_groups()
        # para obtener estadísticas. Usar sensibilidad por defecto (85) para la card.
        if hasattr(similar_data, 'perceptual_hashes'):
            # Es DuplicatesSimilarAnalysis - calcular grupos con sensibilidad default
            if len(similar_data.perceptual_hashes) > 0:
                # Obtener grupos con sensibilidad por defecto para mostrar estadísticas
                groups_result = similar_data.get_groups(sensitivity=85)
                if groups_result.total_duplicates > 0:
                    size_text = f"~{format_size(groups_result.space_wasted)} desperdiciados"
                    card.set_status_with_results(
                        f"{groups_result.total_groups} grupos de archivos similares encontrados",
                        size_text,
                        badge_count=groups_result.total_duplicates
                    )
                else:
                    card.set_status_no_results("No se encontraron archivos similares")
            else:
                card.set_status_no_results("No se encontraron archivos para analizar")
        elif hasattr(similar_data, 'total_duplicates'):
            # Es DuplicateAnalysisResult - usar directamente
            if similar_data.total_duplicates > 0:
                size_text = f"~{format_size(similar_data.space_wasted)} desperdiciados"
                card.set_status_with_results(
                    f"{similar_data.total_groups} grupos de archivos similares encontrados",
                    size_text,
                    badge_count=similar_data.total_duplicates
                )
            else:
                card.set_status_no_results("No se encontraron archivos similares")
        else:
            card.set_status_no_results("No se encontraron archivos similares")
    else:
        # Estado pendiente de análisis
        card.set_status_pending("Analizar para detectar archivos similares")

    card.clicked.connect(lambda: on_click_callback('duplicates_similar'))
    return card
