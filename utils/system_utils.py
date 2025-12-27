"""
System utilities for hardware information and resource detection.
"""
import os
import psutil
from typing import Dict, Any, Optional

def get_cpu_count() -> int:
    """
    Obtiene el número de CPUs/cores del sistema.
    
    Returns:
        Número de cores, o 4 si no se puede detectar
    """
    return os.cpu_count() or 4

def get_system_ram_gb() -> float:
    """
    Obtiene la RAM total del sistema en GB.
    
    Returns:
        RAM en GB, o 8.0 si no se puede detectar
    """
    try:
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        # psutil no disponible, asumir 8GB por defecto
        return 8.0

def get_system_info(
    max_cache_entries_func: Optional[Any] = None,
    large_dataset_threshold_func: Optional[Any] = None,
    auto_open_threshold_func: Optional[Any] = None,
    io_workers_func: Optional[Any] = None,
    cpu_workers_func: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Obtiene información completa del sistema para logging.
    Acepta funciones opcionales para obtener valores de configuración que dependen del sistema.
    
    Returns:
        Dict con ram_gb, ram_available_gb, cpu_count, etc.
    """
    ram_gb = get_system_ram_gb()
    
    try:
        ram_available_gb = psutil.virtual_memory().available / (1024 ** 3)
        psutil_available = True
    except ImportError:
        ram_available_gb = None
        psutil_available = False
    
    info = {
        'ram_total_gb': ram_gb,
        'ram_available_gb': ram_available_gb,
        'psutil_available': psutil_available,
        'cpu_count': get_cpu_count(),
    }

    # Add optional config-dependent values if functions are provided
    if max_cache_entries_func:
        info['max_cache_entries'] = max_cache_entries_func()
    if large_dataset_threshold_func:
        info['large_dataset_threshold'] = large_dataset_threshold_func()
    if auto_open_threshold_func:
        info['auto_open_threshold'] = auto_open_threshold_func()
    if io_workers_func:
        info['io_workers'] = io_workers_func()
    if cpu_workers_func:
        info['cpu_workers'] = cpu_workers_func()
        
    return info
