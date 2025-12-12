"""
Crea la card de Archivos Similares para el grid de herramientas.
"""

from ui.widgets.tool_card import ToolCard


def create_duplicates_similar_card(on_click_callback) -> ToolCard:
    """
    Crea la card de Archivos similares (pendiente por defecto)

    Args:
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    card = ToolCard(
        icon_name='image-search',
        title='Archivos similares',
        description='Detecta fotos y vídeos visualmente idénticos aunque tengan metadatos '
                   'diferentes (fechas, compresión, etc.). Al 100% de similitud son '
                   'prácticamente idénticos visualmente.',
        action_text='Analizar ahora'
    )

    # Por defecto está pendiente
    card.set_status_pending("Este análisis puede tardar bastante tiempo según la cantidad de archivos, por eso no se ha realizado anteriormente.")
    card.clicked.connect(lambda: on_click_callback('similar_files'))
    return card
