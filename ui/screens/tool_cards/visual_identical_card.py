"""
Crea la card de Copias Visuales Idénticas para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard
from utils.format_utils import format_size


def create_visual_identical_card(analysis_results, on_click_callback) -> ToolCard:
    """
    Crea la card de Copias visuales idénticas

    Args:
        analysis_results: Objeto con los resultados del análisis
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    # Verificar si hay análisis disponible
    has_analysis = (hasattr(analysis_results, 'visual_identical') and 
                   analysis_results.visual_identical is not None)
    
    card = ToolCard(
        icon_name='image-multiple',
        title='Copias visualmente idénticas',
        description='Detecta fotos visualmente idénticas aunque tengan diferente '
                   'resolución o metadatos. Ideal para eliminar copias de WhatsApp, '
                   'screenshots repetidos o imágenes redimensionadas.',
        action_text='Gestionar ahora' if has_analysis else 'Analizar ahora'
    )
    
    # Configurar estado según datos
    if has_analysis:
        vi_data = analysis_results.visual_identical
        if vi_data.total_groups > 0:
            size_text = f"~{format_size(vi_data.space_recoverable)} recuperables"
            card.set_status_with_results(
                f"{vi_data.total_groups} grupos detectados",
                size_text,
                badge_count=vi_data.total_duplicates
            )
        else:
            card.set_status_no_results("No se encontraron copias visuales idénticas")
    else:
        # Estado pendiente de análisis
        card.set_status_pending("Analizar para detectar copias visuales idénticas")
    
    card.clicked.connect(lambda: on_click_callback('visual_identical'))
    return card
