# Guía de Uso: Configuración Persistente

## 🎯 Cómo Usar la Nueva Configuración

### Acceder a la Configuración

1. **Abrir la aplicación** Pixaro Lab
2. **Clic en el menú hamburguesa** (☰) en la esquina superior derecha
3. **Seleccionar "⚙️ Configuración"**

---

## 📋 Pestañas de Configuración

### 🎯 General
Configuración básica y preferencias de seguridad:

- **💾 Backups Automáticos**
  - ✅ **Crear backup automáticamente:** Si está activado, se crea una copia de seguridad antes de:
    - Renombrar archivos
    - Eliminar Live Photos
    - Eliminar duplicados HEIC
    - Organizar directorios
  - 💡 **Muy recomendado:** Mantener activado para poder recuperar archivos

- **❓ Confirmaciones**
  - Mostrar diálogo de confirmación antes de ejecutar operaciones
  - Pedir confirmación adicional para operaciones de eliminación

- **🔔 Notificaciones**
  - Mostrar notificación al completar operaciones
  - Reproducir sonido con notificaciones *(próximamente)*

---

### 📁 Directorios
Personaliza dónde se guardan logs y backups:

- **📄 Logs y Diagnóstico**
  - Carpeta donde se guardan los archivos de log
  - Nivel de detalle (DEBUG, INFO, WARNING, ERROR)
  - Botón para abrir carpeta de logs directamente

- **💾 Directorio de Backups**
  - Ubicación donde se guardan las copias de seguridad automáticas

---

### 🔧 Avanzado
Opciones para usuarios avanzados:

- **⚡ Rendimiento**
  - **Hilos de procesamiento:** Número de tareas paralelas (1-16)
    - Más hilos = más rápido, pero mayor uso de CPU
    - Recomendado: 4

- **🧪 Modo Simulación**
  - Activar modo simulación por defecto *(próximamente)*
  - Las operaciones se analizan pero no se ejecutan

- **🐛 Depuración**
  - **Restablecer configuración:** Elimina TODA la configuración guardada
    - Vuelve a valores por defecto
    - Requiere confirmación

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Desactivar Backups por Defecto
Si quieres más control manual sobre los backups:

1. Ve a **General** → **Backups Automáticos**
2. Desmarca "✓ Crear backup automáticamente"
3. Clic en **Guardar Cambios**
4. **Resultado:** En adelante, los checkboxes de backup aparecerán desmarcados
5. Puedes activarlos manualmente en cada operación si lo deseas

---

### Ejemplo 2: Aumentar Detalle de Logs
Para diagnosticar problemas:

1. Ve a **Directorios** → **Logs y Diagnóstico**
2. Cambia nivel a **"DEBUG - Máximo detalle"**
3. Clic en **Guardar Cambios**
4. **Resultado:** Los logs mostrarán información técnica detallada
5. ⚠️ Los archivos de log serán más grandes

---

## 🔄 Restaurar Configuración

### Restaurar Valores por Defecto (sin borrar)
1. En cualquier pestaña, clic en **"🔄 Restaurar valores por defecto"**
2. Confirma la acción
3. Clic en **Guardar Cambios** para aplicar

### Borrar TODA la Configuración
1. Ve a **Avanzado** → **Depuración**
2. Clic en **"🗑️ Restablecer TODA la configuración guardada"**
3. Confirma (acción irreversible)
4. **Resultado:** Vuelve a valores de fábrica

---

## 📍 Ubicación de la Configuración

La configuración se guarda en:

**Linux:**
```
~/.config/PhotoKit/Pixaro Lab.conf
```

**Windows:**
```
C:\Users\<usuario>\AppData\Roaming\PhotoKit\Pixaro Lab.ini
```

**macOS:**
```
~/Library/Preferences/com.PhotoKit.Pixaro Lab.plist
```

💡 **Nota:** Estos archivos se gestionan automáticamente. No es necesario editarlos manualmente.

---

## ⚠️ Avisos Importantes

### Cambios que Requieren Reinicio
Algunos cambios pueden requerir reiniciar la aplicación para tener efecto completo:
- Cambio de nivel de logging (parcialmente aplicado al vuelo)
- Cambio de máximo de workers
- Cambio de directorios (parcialmente aplicado al vuelo)

### Opciones "Próximamente"
Algunas opciones están preparadas pero no implementadas aún:
- Sonidos de notificación
- Tema claro/oscuro
- Modo simulación global

Estas opciones aparecen deshabilitadas o con tooltip indicando "Funcionalidad no implementada".

---

## 🆘 Solución de Problemas

### La configuración no persiste
1. Verifica permisos de escritura en el directorio de configuración
2. Revisa los logs en búsqueda de errores
3. Intenta restablecer la configuración

### Los checkboxes de backup no respetan mi configuración
1. Verifica que guardaste los cambios en Configuración
2. Cierra y vuelve a abrir el diálogo de la operación
3. Revisa que "Auto-backup" esté configurado correctamente en **General**

---

## 📞 Soporte

Si encuentras problemas:
1. Revisa los **logs** (📂 Abrir carpeta de logs)
2. Cambia el nivel a **DEBUG** para más información
3. Intenta **restablecer la configuración**
4. Consulta la documentación en `docs/`

---

**¡Disfruta de tu configuración personalizada!** 🎉
