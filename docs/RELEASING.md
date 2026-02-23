# Releasing InnerPix Lab

This document describes how to create a new release of InnerPix Lab. The process is automated via GitHub Actions — you only need to update the version and push a tag.

> **Privacy note:** All releases are created as **drafts**. Nothing is published until you manually review and publish the release on GitHub.

## Quick Release Checklist

```bash
# 1. Update version in config.py
#    - APP_VERSION = "0.9.0"
#    - APP_VERSION_SUFFIX = "" (or "beta", "rc1", etc.)

# 2. Update CHANGELOG.md
#    - Add new section under [Unreleased]
#    - Update comparison links at bottom

# 3. Commit
git add -A
git commit -m "Release v0.9.0"

# 4. Tag (must match the version in config.py)
git tag v0.9.0

# 5. Push
git push origin main --tags
```

That's it. GitHub Actions will automatically:
1. Build binaries on 3 platforms (Linux, Windows, macOS)
2. Create native installers (.deb, .rpm, Inno Setup .exe, .dmg)
3. Create a **draft** GitHub Release with all artifacts

When you're ready to go public:
4. Review the draft release on GitHub → **Publish**
5. Update the website if needed (separate repo: [safetoolhub.github.io](https://github.com/safetoolhub/safetoolhub.github.io))

## Version Numbering

We use [Semantic Versioning](https://semver.org/):

| Field | When to increment |
|---|---|
| **Major** (X.0.0) | Breaking changes, major UI redesign |
| **Minor** (0.X.0) | New features, new tools |
| **Patch** (0.0.X) | Bug fixes, performance improvements |

### Version Suffix

| Suffix | Meaning |
|---|---|
| `""` (empty) | Stable release |
| `"beta"` | Beta — feature complete, may have bugs |
| `"rc1"`, `"rc2"` | Release candidate — nearly ready |
| `"alpha"` | Alpha — early/incomplete |

### Examples

| `APP_VERSION` | `APP_VERSION_SUFFIX` | Git Tag | Full Version |
|---|---|---|---|
| `"0.8.0"` | `"beta"` | `v0.8.0-beta` | `0.8.0-beta` |
| `"1.0.0"` | `""` | `v1.0.0` | `1.0.0` |
| `"1.1.0"` | `"rc1"` | `v1.1.0-rc1` | `1.1.0-rc1` |

## Where Version Is Used

All version references flow from `config.py`:

| Location | Usage |
|---|---|
| `config.py` | Single source of truth (`APP_VERSION`, `APP_VERSION_SUFFIX`) |
| `config.py` | `get_full_version()` → computed `"0.8.0-beta"` |
| `main.py` | Startup log + QApplication metadata |
| `about_dialog.py` | About dialog version display |
| `build/innerpix-lab.spec` | Binary metadata |
| `build/installer.iss` | Windows installer version |
| `CHANGELOG.md` | Manual — must match |
| Git tag | Manual — must match (`v` prefix + full version) |

## What the Release Workflow Does

When you push a tag matching `v*`, GitHub Actions builds on 3 platforms and creates a **draft release** (not public until you manually publish it).

### 1. Linux Build (`ubuntu-22.04`)
- PyInstaller → `dist/innerpix-lab/` directory
- `dpkg-deb` → `InnerPixLab-{version}-linux-amd64.deb` (native, no extra dependencies)
- `rpmbuild` → `InnerPixLab-{version}-linux-x86_64.rpm`

### 2. Windows Build (`windows-latest`)
- PyInstaller → `dist/InnerPixLab/` directory
- Inno Setup (`iscc`) → `InnerPixLab-{version}-windows-setup.exe`

### 3. macOS Build (`macos-latest`)
- Icon generation: PNG → `.icns` via `iconutil`
- PyInstaller → `dist/InnerPixLab.app` bundle
- `create-dmg` → `InnerPixLab-{version}-macos.dmg`

### 4. Draft Release
- Creates a **draft** GitHub Release (not visible to public)
- Pre-release flag set if suffix is alpha/beta/rc
- Attaches all artifacts (up to 6 files: .deb, .rpm, .exe, .dmg)
- Auto-generates release notes from commits since last tag
- **You must manually publish** from the GitHub Releases page

## Website

The SafeToolHub website is maintained in a separate repository:
[safetoolhub/safetoolhub.github.io](https://github.com/safetoolhub/safetoolhub.github.io)

It deploys automatically to [safetoolhub.org](https://safetoolhub.org) via GitHub Pages when changes are pushed to `main`.

## Local Build (for testing)

```bash
# Full build with installer packaging
python dev-tools/build.py

# PyInstaller only (no installer packaging)
python dev-tools/build.py --skip-installer
```

### Linux Build Dependencies

```bash
# .deb — dpkg-deb is included in dpkg (pre-installed on Debian/Ubuntu)
dpkg-deb --version

# .rpm — install rpmbuild if needed
sudo apt install rpm            # Debian/Ubuntu
sudo dnf install rpm-build      # Fedora
```

No additional tools needed (no AppImage, no fpm, no gem).

### Windows Build Dependencies

```bash
# Inno Setup (installed automatically in CI via choco)
choco install innosetup
```

### macOS Build Dependencies

```bash
# create-dmg (installed automatically in CI via brew)
brew install create-dmg
```

## Troubleshooting

**PyInstaller fails with import errors**
→ Check `build/innerpix-lab.spec` hiddenimports list. Add any missing modules.

**Windows installer shows wrong version**
→ Verify `APP_VERSION` / `APP_FULL_VERSION` environment variables are set in the workflow.

**macOS DMG creation fails**
→ `create-dmg` exits with code 2 if there's no code signing identity. This is expected; the script handles it.

**GitHub Release has no artifacts**
→ Check each platform build job for errors. Artifacts upload uses `if-no-files-found: warn`.

**Draft release not visible**
→ Draft releases are only visible to repository collaborators. Go to Releases → filter by "Draft".

## DNS Configuration (when ready to go public)

For the safetoolhub.org custom domain:

```
# A records (GitHub Pages IPs)
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153

# CNAME for www
www.safetoolhub.org → safetoolhub.github.io

# safetoolhub.com → redirect to safetoolhub.org (at registrar level)
```

DNS is configured for the website repository ([safetoolhub.github.io](https://github.com/safetoolhub/safetoolhub.github.io)).
After configuring DNS, enable "Enforce HTTPS" in GitHub → Settings → Pages after DNS propagation.
