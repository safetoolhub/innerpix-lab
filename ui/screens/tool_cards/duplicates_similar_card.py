"""
Crea la card de Archivos Similares para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard


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
        description='Detecta fotos y vídeos visualmente muy similares aunque tengan metadatos '
                   'diferentes (fechas, compresión, etc.). Debes analizarlo manualmente y elegir los que quieras borrar. Es la única utilidad que no permite el borrado automático.',
        action_text='Analizar ahora'
    )

    # Por defecto está pendiente
    card.set_status_pending("Este análisis puede tardar bastante tiempo según la cantidad de archivos, por eso no se ha realizado anteriormente.")
    card.clicked.connect(lambda: on_click_callback('duplicates_similar'))
    return card
