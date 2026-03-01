<p align="center">
  <img src="assets/icon.png" alt="InnerPix Lab" width="128" height="128">
</p>

<h1 align="center">InnerPix Lab</h1>

<p align="center">
  <strong>Privacy-first photo & video management. 100% local, no cloud.</strong>
</p>

<p align="center">
  <a href="https://github.com/safetoolhub/innerpix-lab/releases"><img src="https://img.shields.io/github/v/release/safetoolhub/innerpix-lab?include_prereleases&label=version&color=blue" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPLv3-green" alt="License GPLv3"></a>
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Platforms">
  <img src="https://img.shields.io/badge/privacy-100%25%20offline-brightgreen" alt="100% Offline">
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#build-from-source">Build from Source</a> •
  <a href="#license">License</a> •
  <a href="#español">Español</a>
</p>

---

## What is InnerPix Lab?

InnerPix Lab is a desktop application for managing, organizing, and optimizing photo and video collections with **absolute privacy**. All processing happens 100% locally on your machine — no cloud, no telemetry, no external connections. Ever.

## Features

### 🧹 Cleanup & Space

| Tool | Description |
|------|-------------|
| **Zero-byte files** | Detect and safely remove empty (0-byte) files |
| **Live Photos** | Find iPhone Live Photo pairs (image + MOV) and choose what to keep |
| **HEIC/JPG duplicates** | Identify HEIC/JPG duplicate pairs from iPhone conversions |
| **Exact copies** | Find 100% identical files using SHA256 hash comparison |

### 🔍 Visual Detection

| Tool | Description |
|------|-------------|
| **Visually identical** | Detect images that look exactly the same using perceptual hashing |
| **Similar files** | Find 70–95% similar images (edits, crops, different resolutions) with an adjustable sensitivity slider |

### 📁 Organization

| Tool | Description |
|------|-------------|
| **Smart organizer** | Reorganize files into a clean date-based folder structure |
| **Complete renamer** | Standardize filenames to `YYYYMMDD_HHMMSS_TYPE.ext` format |

### Core Principles

- **🔒 Privacy First** — All operations are offline and local. No data ever leaves your machine.
- **💾 Backup-First Policy** — Every destructive operation offers backup creation and dry-run simulation before making changes.
- **🌍 Multilingual** — Full Spanish and English interface (898+ translation keys).
- **🖥️ Cross-Platform** — Native experience on Linux, Windows, and macOS.

## Installation

Download the latest release for your platform from the [Releases page](https://github.com/safetoolhub/innerpix-lab/releases).

| Platform | Format | Notes |
|----------|--------|-------|
| **Linux** | `.deb`, `.rpm` | Ubuntu/Debian, Fedora/RHEL |
| **Windows** | `.exe` installer | Windows 10/11 |
| **macOS** | `.dmg` | macOS 12+ |

### Linux

```bash
# Debian/Ubuntu
sudo dpkg -i innerpix-lab_0.9-beta_amd64.deb

# Fedora/RHEL
sudo rpm -i innerpix-lab-0.9.beta-1.x86_64.rpm
```

### Windows

Run the installer and follow the setup wizard. A Start Menu shortcut will be created automatically.

### macOS

Open the `.dmg` file and drag InnerPix Lab to your Applications folder.

## Build from Source

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
git clone https://github.com/safetoolhub/innerpix-lab.git
cd innerpix-lab

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
uv pip install -r requirements.txt

# Run the application
python main.py
```

### Running Tests

```bash
uv pip install -r requirements-dev.txt
pytest --ignore=tests/performance
```

### Optional System Tools

Some video analysis features require external tools:

- **ffprobe** (from FFmpeg) — for video metadata extraction
- **exiftool** — for advanced EXIF reading

These are optional. The application works fully without them but will skip video metadata phases during scanning.

## Tech Stack

- **Language**: Python 3.12+
- **UI Framework**: PyQt6
- **Testing**: pytest (713+ tests)
- **Architecture**: Strict UI/logic separation — services are PyQt6-free for future portability

## Contributing

Contributions are welcome! Please read the [Contributing Guide](CONTRIBUTING.md) before submitting a pull request.

## License

InnerPix Lab is licensed under the [GNU General Public License v3.0](LICENSE) with additional attribution requirements under Section 7:

- **Attribution Required**: Any derivative work must retain visible attribution to [SafeToolHub](https://safetoolhub.org) with a clickable link.
- See [LICENSE](LICENSE) for full details.

## Links

- **Website**: [safetoolhub.org](https://safetoolhub.org)
- **Releases**: [GitHub Releases](https://github.com/safetoolhub/innerpix-lab/releases)
- **Issues**: [Report a bug](https://github.com/safetoolhub/innerpix-lab/issues)

---

## Español

### ¿Qué es InnerPix Lab?

InnerPix Lab es una aplicación de escritorio para gestionar, organizar y optimizar colecciones de fotos y vídeos con **privacidad absoluta**. Todo el procesamiento ocurre 100% en local — sin nube, sin telemetría, sin conexiones externas.

### Características

**🧹 Limpieza y espacio**
- Archivos vacíos (0 bytes), Live Photos de iPhone, duplicados HEIC/JPG, copias exactas (SHA256)

**🔍 Detección visual**
- Copias visualmente idénticas (hash perceptual), archivos similares (70–95% con slider de sensibilidad)

**📁 Organización**
- Organización inteligente por fecha, renombrado completo a formato `YYYYMMDD_HHMMSS`

### Principios clave

- **🔒 Privacidad ante todo** — Todas las operaciones son offline y locales.
- **💾 Política de backups** — Toda operación destructiva ofrece copia de seguridad y simulación previa.
- **🌍 Multilingüe** — Interfaz completa en español e inglés.
- **🖥️ Multiplataforma** — Linux, Windows y macOS.

### Instalación

Descarga la última versión desde la [página de Releases](https://github.com/safetoolhub/innerpix-lab/releases).

### Compilar desde código fuente

```bash
git clone https://github.com/safetoolhub/innerpix-lab.git
cd innerpix-lab
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py
```

### Licencia

InnerPix Lab está licenciado bajo [GPLv3](LICENSE) con requisito de atribución obligatoria a [SafeToolHub](https://safetoolhub.org) con link visible.

---

<p align="center">
  Made with ❤️ by <a href="https://safetoolhub.org">SafeToolHub</a>
</p>
