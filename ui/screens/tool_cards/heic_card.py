"""
Crea la card de HEIC/JPG Duplicados para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard
from ui.tools_definitions import TOOL_HEIC
from utils.format_utils import format_size


def create_heic_card(analysis_results, on_click_callback) -> ToolCard:
    """
    Crea la card de HEIC/JPG con información del análisis (si existe)

    Args:
        analysis_results: Objeto con los resultados del análisis
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    # Verificar si hay análisis disponible
    has_analysis = (hasattr(analysis_results, 'heic') and 
                   analysis_results.heic is not None)
    
    card = ToolCard(
        icon_name=TOOL_HEIC.icon_name,
        title=TOOL_HEIC.title,
        description=TOOL_HEIC.long_description,
        action_text='Gestionar ahora' if has_analysis else 'Analizar ahora'
    )
    
    if has_analysis:
        heic_data = analysis_results.heic
        if heic_data.items_count > 0:
            savings_jpg = heic_data.potential_savings_keep_jpg or 0
            savings_heic = heic_data.potential_savings_keep_heic or 0
            max_savings = max(savings_jpg, savings_heic)
            card.set_status_with_results(
                f"{heic_data.items_count} grupos de duplicados HEIC/JPG encontrados",
                f"~{format_size(max_savings)} recuperables",
                badge_count=heic_data.items_count
            )
        else:
            card.set_status_no_results("No se encontraron pares HEIC/JPG")
    else:
        # Estado pendiente de análisis
        card.set_status_pending("Analizar para detectar duplicados HEIC/JPG")

    card.clicked.connect(lambda: on_click_callback('heic'))
    return card
