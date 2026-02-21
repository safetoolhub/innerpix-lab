# Guía de Despliegue (Release) de InnerPix Lab

Esta guía explica los pasos concretos para compilar y desplegar una nueva versión de la aplicación para Windows, macOS y Linux a través de GitHub Actions.

Actualmente, el proceso está configurado para ejecutarse **automáticamente** cuando se crea un **Tag** asociado a una versión (empezando por la letra `v`). Además, el release se crea como un **Draft (Borrador)** privado. Nada se publicará de cara al público hasta que lo apruebes manualmente desde la web de GitHub.

## 1. Crear y subir un nuevo Tag (Versión)

Cuando estés listo para probar o lanzar una nueva versión (por ejemplo, `v0.8.1`), debes ejecutar los siguientes comandos desde tu terminal local:

1. Asegúrate de estar en la rama principal y tener los últimos cambios:
   ```bash
   git checkout main
   git pull origin main
   ```

2. (Opcional pero recomendado) Actualiza la versión en el archivo `config.py` y haz un commit:
   ```bash
   git add config.py
   git commit -m "Upgrade version to v0.8.5"
   git push origin main
   ```

3. Crea el Tag de la versión. **Importante:** El nombre del tag debe empezar por "v":
   ```bash
   git tag v0.8.1
   ```
   *(Si es una versión en pruebas, puedes usar un sufijo, por ejemplo: `git tag v0.8.1-beta`)*

4. Sube el Tag a GitHub:
   ```bash
   git push origin v0.8.1
   ```

## 2. Esperar a la compilación en GitHub Actions

Una vez que se sube el Tag, GitHub Actions se pondrá en marcha automáticamente:

1. Ve a la página de tu repositorio en GitHub.
2. Haz clic en la pestaña **Actions**.
3. Verás un workflow llamado **Release** ejecutándose.
4. Este proceso construirá paralelamente los binarios para:
   - **Linux**: Archivos `.deb` y `.rpm`.
   - **Windows**: Instalador `.exe` de Inno Setup.
   - **macOS**: Archivo `.dmg`.

*Este proceso puede tomar varios minutos. Puedes hacer clic en el workflow para ver el progreso.*

## 3. Revisar y publicar el Release

Cuando el workflow termine con éxito, creará un Release en estado de **Borrador (Draft)**.
Como sigue siendo privado, puedes revisarlo o descargarlo para probarlo de nuevo en tus propios dispositivos.

1. Ve a la sección de **Releases** en la página principal de GitHub de tu repositorio (lado derecho).
2. Verás un nuevo lanzamiento marcado como `Draft`.
3. Haz clic en el botón **Edit** de ese release.
4. Comprueba que en la sección "Assets" al final de la página se encuentren todos los archivos:
   - `InnerPixLab-0.8.1-...-linux-amd64.deb`
   - `InnerPixLab-0.8.1-...-linux-x86_64.rpm`
   - `InnerPixLab-0.8.1-...-windows-setup.exe`
   - `InnerPixLab-0.8.1-...-macos.dmg`
5. Las notas de la versión (Release Notes) se autogenerarán basándose en los commits. Puedes editarlas o traducirlas.
6. **(Momento de Publicar)**: Si los archivos son correctos y estás listo para hacer la versión accesible para que cualquiera la descargue, desmarca la opción "Save as draft" y haz clic en el botón verde **Publish release**.

Si algo va mal y la versión no sirve, simplemente borra el "Draft Release" y elimina el tag localmente y en remoto: `git tag -d v0.8.1` y `git push --delete origin v0.8.1`, corrige el código, y vuelve a crear un nuevo Tag.
