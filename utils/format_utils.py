"""Utilidades para formateo reutilizables en todo el proyecto.

Contiene funciones puras: format_size, format_file_count, format_percentage,
y truncate_path. Estas funciones no dependen de la UI y pueden importarse desde
`utils.format_utils` en cualquier módulo.
"""
from pathlib import Path
from typing import Optional
import re
import html


def format_size(bytes_size: Optional[float]) -> str:
    """Formatea un tamaño en bytes a una cadena legible.

    Soporta B, KB, MB, GB usando potencias de 1024.
    Maneja None y valores inválidos devolviendo '0 B'. Mantiene el signo para
    valores negativos.
    """
    if bytes_size is None:
        return "0 B"
    
    try:
        size = float(bytes_size)
    except (TypeError, ValueError):
        return "0 B"

    if size < 0:
        return f"-{format_size(abs(size))}"

    if size < 1024:
        return f"{int(size)} B"

    kb = size / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"

    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"

    gb = mb / 1024
    return f"{gb:.2f} GB"


def format_number(number: Optional[int]) -> str:
    """Formatea un número con abreviaciones para miles (K, M).
    
    Ejemplos:
    - 0-999: "123"
    - 1000-9999: "1.2K"
    - 10000-999999: "12K"
    - 1000000+: "1.2M"
    
    Args:
        number: Número entero a formatear
    
    Returns:
        String con el número formateado profesionalmente
    """
    if number is None:
        return "0"
    
    try:
        num = int(number)
    except (TypeError, ValueError):
        return "0"
    
    if num < 0:
        return f"-{format_number(abs(num))}"
    
    if num < 1000:
        return str(num)
    elif num < 10000:
        return f"{num / 1000:.1f}K"
    elif num < 1000000:
        return f"{num // 1000}K"
    else:
        return f"{num / 1000000:.1f}M"


def format_file_count(count: Optional[int]) -> str:
    """Formatea un recuento de archivos con separador de miles.

    - Si count es None o inválido devuelve '0'.
    - Mantiene formateo con coma como separador de miles.
    """
    if count is None:
        return "0"
    
    try:
        return f"{int(count):,}"
    except (TypeError, ValueError):
        return "0"


def format_percentage(numerator: float, denominator: float) -> str:
    """Devuelve un porcentaje formateado 'xx.x%'.

    - Si denominator es 0 devuelve '0%'.
    - Maneja entradas inválidas devolviendo '0%'.
    """
    if denominator == 0:
        return "0%"
    
    try:
        pct = (float(numerator) / float(denominator)) * 100
        return f"{pct:.1f}%"
    except (TypeError, ValueError, ZeroDivisionError):
        return "0%"


def truncate_path(path: str, max_length: int = 40) -> str:
    """Trunca rutas largas insertando '...' en el centro para ajustarse a max_length.

    - Si la longitud de la ruta es menor o igual a max_length devuelve la ruta tal cual.
    - Intenta preservar el inicio y el final de la ruta.
    """
    if path is None:
        return ""
    
    s = str(path)
    if len(s) <= max_length:
        return s
    if max_length <= 6:
        return s[:max_length]

    part = (max_length - 3) // 2
    return f"{s[:part]}...{s[-part:]}"

def generate_stats_html(stats: dict, icon_prefix: str = "") -> str:
    """
    Genera HTML con formato consistente para mostrar estadísticas.
    
    Args:
        stats: Diccionario con pares clave-valor de estadísticas
               Formato: {'label': valor} o {'label': (valor, formato)}
        icon_prefix: Emoji/icono opcional al inicio de cada línea
        
    Returns:
        str: HTML formateado con las estadísticas
        
    Examples:
        >>> stats = {
        ...     'Total archivos': 150,
        ...     'A renombrar': (25, 'highlight'),
        ...     'Espacio': format_size(1024000)
        ... }
        >>> html = generate_stats_html(stats)
    """
    if not stats:
        return ""

    parts = []
    for label, value in stats.items():
        # Normalizar display_value como string ya formateado
        display_value = ""
        if isinstance(value, tuple):
            display_value = value[0]
        else:
            display_value = value

        # Escape de contenido
        lbl = html.escape(str(icon_prefix + label))
        val = html.escape(str(display_value))

        # Aplicar formatos sencillos si vienen en la tupla
        if isinstance(value, tuple) and len(value) > 1 and value[1] == 'highlight':
            val_html = f"<strong style=\"color:#28a745;\">{val}</strong>"
        else:
            val_html = val

        parts.append(f"<div style='margin-bottom:6px;'><strong>{lbl}:</strong> {val_html}</div>")

    return "".join(parts)


def generate_section_html(title: str, stats: dict, icon: str = "") -> str:
    """
    Genera una sección HTML completa con título y estadísticas.
    
    Args:
        title: Título de la sección
        stats: Diccionario de estadísticas
        icon: Emoji/icono para el título
        
    Returns:
        str: HTML de la sección completa
    """
    title_html = f"<h3>{html.escape(icon + ' ' + title)}</h3>" if title else ""
    stats_html = generate_stats_html(stats)

    return title_html + stats_html


def markdown_like_to_html(text: str) -> str:
    """Convierte un texto con marcado ligero (**bold**, listas con • o -) a HTML.

    - **bold** -> <strong>
    - Líneas que empiezan con •, - o * se agrupan en <ul><li>
    - Saltos de línea simples se convierten en <br>, dobles en separación de párrafos
    """
    if not text:
        return ""

    # Normalizar entradas numéricas
    text = str(text)

    # Procesar por líneas para detectar listas
    lines = text.splitlines()
    out = []
    in_list = False

    def render_inline(s: str) -> str:
        # Reemplazar **bold** por placeholder-safe handling
        parts = re.split(r'(\*\*.*?\*\*)', s)
        rendered = []
        for p in parts:
            if p.startswith('**') and p.endswith('**') and len(p) >= 4:
                inner = p[2:-2]
                rendered.append(f"<strong>{html.escape(inner)}</strong>")
            else:
                rendered.append(html.escape(p))
        return ''.join(rendered).replace('\n', '<br/>')

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(('• ', '- ', '* ')):
            if not in_list:
                out.append('<ul>')
                in_list = True
            item_text = stripped[2:]
            out.append(f"<li>{render_inline(item_text)}</li>")
        else:
            if in_list:
                out.append('</ul>')
                in_list = False
            if stripped == '':
                out.append('<p></p>')
            else:
                out.append(f"<p>{render_inline(stripped)}</p>")

    if in_list:
        out.append('</ul>')

    return ''.join(out)


def format_file_operation_summary(
    total: int,
    processed: int,
    errors: int = 0,
    action_verb: str = "procesado"
) -> str:
    """
    Formatea un resumen de operación sobre archivos.
    
    Args:
        total: Total de archivos
        processed: Archivos procesados exitosamente
        errors: Archivos con error
        action_verb: Verbo que describe la acción (ej: "renombrado", "eliminado")
        
    Returns:
        str: Texto formateado del resumen
        
    Example:
        >>> format_file_operation_summary(100, 95, 5, "renombrado")
        '✅ 95/100 archivos renombrados correctamente (5 errores)'
    """
    if errors > 0:
        return f"✅ {processed}/{total} archivos {action_verb}s correctamente ({errors} errores)"
    else:
        return f"✅ {processed}/{total} archivos {action_verb}s correctamente"


def format_markdown_list(items: list, ordered: bool = False) -> str:
    """
    Convierte una lista Python en una lista Markdown.
    
    Args:
        items: Lista de strings o tuplas (emoji, texto)
        ordered: Si es True, crea lista numerada
        
    Returns:
        str: Lista en formato Markdown
    """
    if not items:
        return ""
    
    formatted_items = []
    
    for i, item in enumerate(items, 1):
        if isinstance(item, tuple):
            emoji, text = item
            line = f"{emoji} {text}"
        else:
            line = str(item)
        
        if ordered:
            formatted_items.append(f"{i}. {line}")
        else:
            formatted_items.append(f"- {line}")
    
    return "\n".join(formatted_items)