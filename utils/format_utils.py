"""Utilidades para formateo reutilizables en todo el proyecto.

Contiene funciones puras: format_size, format_file_count, format_percentage,
y truncate_path. Estas funciones no dependen de la UI y pueden importarse desde
`utils.format_utils` en cualquier módulo.
"""
from typing import Optional


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
