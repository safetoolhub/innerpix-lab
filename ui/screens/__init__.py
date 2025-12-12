"""
Módulos de screens de la interfaz de usuario de Innerpix Lab.
Cada screen representa una etapa diferente de la aplicación.
"""

from .base_stage import BaseStage
from .stage_1_window import Stage1Window
from .stage_2_window import Stage2Window
from .stage_3_window import Stage3Window

__all__ = ['BaseStage', 'Stage1Window', 'Stage2Window', 'Stage3Window']