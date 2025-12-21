"""
Crea la card de Live Photos para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard
from utils.format_utils import format_size


def create_live_photos_card(analysis_results, on_click_callback) -> ToolCard:
    """
    Crea la card de Live Photos

    Args:
        analysis_results: Objeto con los resultados del análisis
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    # Verificar si hay análisis disponible
    has_analysis = (hasattr(analysis_results, 'live_photos') and 
                   analysis_results.live_photos is not None)
    
    card = ToolCard(
        icon_name='camera-burst',
        title='Live Photos',
        description='Las Live Photos de iPhone combinan imagen y vídeo corto. '
                   'Libera espacio eliminando el componente de vídeo, '
                   'mientras conservas la esencia de tus recuerdos.',
        action_text='Gestionar ahora' if has_analysis else 'Analizar ahora'
    )

    # Configurar estado según datos
    if has_analysis:
        live_photo_data = analysis_results.live_photos
        if live_photo_data.items_count > 0:
            size_text = f"~{format_size(live_photo_data.potential_savings)} recuperables"
            card.set_status_with_results(
                f"{live_photo_data.items_count} Grupos de Live Photos detectados",
                size_text
            )
        else:
            card.set_status_no_results("No se encontraron Live Photos")
    else:
        # Estado pendiente de análisis
        card.set_status_pending("Analizar para detectar Live Photos")

    card.clicked.connect(lambda: on_click_callback('live_photos'))
    return card
