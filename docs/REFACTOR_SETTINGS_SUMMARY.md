🔴 CRÍTICO - Alta Prioridad
1. Falta de Tests Unitarios
Problema: Solo hay un test manual (test_max_workers.py). No hay suite de tests automatizados.

Impacto:

Riesgo alto de regresiones
Difícil validar cambios
No hay cobertura de código
Recomendaciones:

Tests prioritarios:

test_file_utils.py: calcular hashes, buscar nombres disponibles
test_live_photo_detector.py: detección de pares imagen/video
test_result_types.py: validación de dataclasses
Tests con directorios temporales para operaciones destructivas
2. Manejo de Excepciones Genéricas
Problema: Muchos bloques except Exception capturan todos los errores sin discriminar.

Ejemplos encontrados:

Recomendaciones:

3. Recursos No Liberados Correctamente
Problema: Workers y threads pueden no liberarse correctamente en ciertos escenarios.

Ubicaciones críticas:

ui/main_window.py:313-316: Uso de .wait() bloqueante
Controllers que mantienen referencias a workers
Recomendaciones:

🟠 IMPORTANTE - Media Prioridad
4. Sincronización de Nivel de Log
Problema: Ya identificado en TODO.txt - cambios en nivel de log no se propagan.

Solución:

5. Validación de Extensiones Case-Sensitive
Problema: Ya identificado en TODO - archivos con extensiones en mayúsculas.

Estado actual: Parcialmente implementado (.suffix.lower() en algunos lugares)

Áreas a revisar:

Recomendación: Crear función centralizada

6. Falta de Validación de Entrada del Usuario
Problema: Pocas validaciones en diálogos antes de operaciones destructivas.

Recomendaciones:

7. Dependencias No Verificadas al Inicio
Problema: Librerías opcionales (pillow-heif, imagehash, cv2) se verifican en runtime.

Recomendación: Verificación temprana

🟡 MEJORAS - Baja Prioridad
8. Logging Excesivo en Producción
Problema: Muchos logger.debug() que podrían ralentizar en producción.

Recomendación: Usar guards condicionales

9. Duplicación de Código en Controllers
Problema: Patrones repetidos en re-análisis después de operaciones.

Ejemplo: Todos los controllers tienen schedule_reanalysis() similar.

Recomendación: Extraer a BaseController

10. Falta de Documentación de Tipos
Problema: Algunos métodos carecen de type hints completos.

Recomendación: Completar type hints

11. Hardcoded Strings en UI
Problema: Mensajes en español hardcoded, dificulta internacionalización.

Recomendación futura: Preparar para i18n

12. Progress Callbacks No Cancelables
Problema: Algunos callbacks ignoran el valor de retorno del stop check.

Recomendación: Propagar señal de cancelación

🔧 ARQUITECTURA Y DISEÑO
13. Dataclasses con Compatibilidad Dict Innecesaria
Estado: Los result_types.py tienen __getitem__ para compatibilidad.

Recomendación: Eliminar gradualmente

14. Configuración Global Mutable
Problema: Config permite modificar DEFAULT_LOG_DIR en runtime.

Recomendación: Hacer inmutable

📋 PLAN DE ACCIÓN SUGERIDO
Fase 1 - Estabilidad (1-2 semanas)

✅ Añadir tests unitarios básicos (file_utils, result_types)
✅ Mejorar manejo de excepciones específicas
✅ Verificar liberación de recursos (workers, file handles)
✅ Completar validación de extensiones case-insensitive
Fase 2 - Robustez (2-3 semanas)
5. ✅ Implementar sincronización de nivel de log
6. ✅ Añadir validación de entrada en diálogos
7. ✅ Crear verificación de dependencias al inicio
8. ✅ Implementar BaseController para reducir duplicación

Fase 3 - Mejoras (1-2 semanas)
9. ✅ Completar type hints en módulos críticos
10. ✅ Optimizar logging con guards condicionales
11. ✅ Añadir tests de integración
12. ✅ Documentar APIs públicas con docstrings completos

🎯 MÉTRICAS DE CALIDAD SUGERIDAS
✨ PUNTOS FUERTES DEL PROYECTO
Arquitectura bien diseñada:

✅ Separación clara de capas (Services/Workers/Controllers)
✅ Uso de dataclasses para resultados
✅ Logging centralizado y consistente
✅ Patrón backup-first en operaciones destructivas
✅ Controllers especializados por funcionalidad
Buenas prácticas:

✅ No hay imports de PyQt6 en Services (separación UI/lógica)
✅ Config centralizado
✅ Uso de Path en lugar de strings
✅ Procesamiento paralelo con ThreadPoolExecutor