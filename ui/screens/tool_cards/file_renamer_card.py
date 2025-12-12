"""
Crea la card de Renombrar para el grid de herramientas.
"""

from ui.widgets.tool_card import ToolCard


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
        title='Renombrar',
        description='Renombra tus archivos con fechas de captura en formato legible. '
                   'Convierte nombres crípticos en nombres descriptivos y fáciles de buscar.',
        action_text='Renombrar ahora'
    )

    # Esta herramienta no requiere análisis previo
    card.set_status_ready("Listo para renombrar archivos")
    card.clicked.connect(lambda: on_click_callback('rename-box'))
    return card
