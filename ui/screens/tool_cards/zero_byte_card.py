"""
Crea la card de Archivos vacíos para el grid de herramientas.
"""

from ui.widgets.tool_card import ToolCard


def create_zero_byte_card(analysis_results, on_click_callback) -> ToolCard:
    """
    Crea la card de Archivos vacíos

    Args:
        analysis_results: Objeto con los resultados del análisis
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    # Verificar si hay análisis disponible
    has_analysis = (hasattr(analysis_results, 'zero_byte') and 
                   analysis_results.zero_byte is not None)
    
    card = ToolCard(
        icon_name='file-x',
        title='Archivos vacíos',
        description='Detecta archivos de 0 bytes que no contienen datos útiles. '
                   'Elimínalos de forma segura para mantener tu biblioteca limpia y ordenada.',
        action_text='Gestionar ahora' if has_analysis else 'Analizar ahora'
    )

    # Configurar estado según datos
    if has_analysis:
        zero_byte_data = analysis_results.zero_byte
        if zero_byte_data.items_count > 0:
            size_text = f"{zero_byte_data.items_count} archivos"
            card.set_status_with_results(
                f"{zero_byte_data.items_count} archivos vacíos detectados",
                size_text
            )
        else:
            card.set_status_no_results("No se encontraron archivos vacíos")
    else:
        # Estado pendiente de análisis
        card.set_status_pending("Analizar para detectar archivos vacíos")
        
    card.clicked.connect(lambda: on_click_callback('zero_byte'))
    return card
