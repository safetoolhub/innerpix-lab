"""
Crea la card de Renombrar para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard


def create_file_renamer_card(on_click_callback) -> ToolCard:
    """
    Crea la card de Renombrar

    Args:
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    card = ToolCard(
        icon_name='rename-box',
        title='Renombrado masivo',
        description='Renombra todos tus archivos con fechas de captura en formato legible. '
                   'Convierte nombres crípticos como `IMG_8823.JPG` en nombres descriptivos como `20241231_112300_PHOTO.jpg`',
        action_text='Renombrar ahora'
    )

    # Esta herramienta no requiere análisis previo
    card.set_status_ready("Listo para renombrar archivos")
    card.clicked.connect(lambda: on_click_callback('file_renamer'))
    return card
