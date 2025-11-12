"""
Utilidades para manejo seguro de callbacks de progreso.

Este módulo proporciona helpers para ejecutar callbacks de progreso
de forma segura, evitando que errores en callbacks detengan procesos críticos.
"""

from typing import Callable, Optional
from utils.logger import get_logger

logger = get_logger('callback_utils')


def safe_progress_callback(
    callback: Optional[Callable[[int, int, str], None]],
    current: int,
    total: int,
    message: str
) -> bool:
    """
    Ejecuta callback de progreso de forma segura.

    Args:
        callback: Función callback a ejecutar (current, total, message)
        current: Valor actual del progreso
        total: Valor total del progreso
        message: Mensaje descriptivo del estado actual

    Returns:
        True si el proceso debe continuar, False si debe detenerse
        (callback puede retornar False para señalar detención)

    Note:
        Si el callback falla, se registra un warning pero no se detiene el proceso.
        Esto evita que errores en la UI/callbacks rompan operaciones críticas.
    """
    if callback and callable(callback):
        try:
            result = callback(current, total, message)
            # Si el callback retorna False explícitamente, detener el proceso
            if result is False:
                return False
        except Exception as e:
            logger.warning(f"Error en progress callback: {e}")
    
    # Por defecto, continuar el proceso
    return True


def create_safe_callback(
    callback: Optional[Callable[[int, int, str], None]]
) -> Callable[[int, int, str], bool]:
    """
    Crea una versión segura de un callback que puede ser None.

    Args:
        callback: Callback original (puede ser None)

    Returns:
        Función que ejecuta el callback de forma segura o no hace nada si callback es None
        Retorna True para continuar, False para detener

    Example:
        >>> safe_cb = create_safe_callback(progress_callback)
        >>> if not safe_cb(50, 100, "Processing..."):
        >>>     break  # Detener procesamiento
    """
    def safe_wrapper(current: int, total: int, message: str) -> bool:
        return safe_progress_callback(callback, current, total, message)

    return safe_wrapper
