# Plan: Professional Release Pipeline for InnerPix Lab

**TL;DR**: Set up automated release management using GitHub Actions to build native installers (MSI/Windows, DMG/macOS, AppImage+deb/Linux) from PyInstaller, hosted as GitHub Releases. A Jekyll multi-page site on GitHub Pages (safetoolhub.org / safetoolhub.com) serves as the download/docs portal. Version metadata lives in `config.py` as the single source of truth. Releasing a new version = update version in config.py → push a git tag → everything else is automatic.

---

## Steps

### 1. Enhance version metadata in `config.py`

Expand the app info section to include all release-relevant data:
- `APP_VERSION = "0.8.0"` — semver format (major.minor.patch)
- `APP_VERSION_SUFFIX = "beta"` — suffix for pre-releases (empty string for stable)
- `APP_FULL_VERSION` — computed property: `"0.8.0-beta"` or `"1.0.0"`
- `APP_AUTHOR = "SafeToolHub"`
- `APP_WEBSITE = "https://safetoolhub.org"`
- `APP_REPO = "https://github.com/safetoolhub/innerpix-lab"`
- `APP_DESCRIPTION` — one-liner for installers/package metadata

Update the 4 existing references (`main.py:58`, `main.py:99`, `about_dialog.py:132`, `about_dialog.py:489`) to use `APP_FULL_VERSION` where appropriate.

### 2. Create app icon assets

Create `assets/` directory at project root with:
- `assets/icon.png` — 512×512 PNG (placeholder: gradient square with "IP" initials using Pillow script)
- `assets/icon.ico` — Windows icon (multi-resolution: 16/32/48/64/128/256, generated from PNG)
- `assets/icon.icns` — macOS icon (generated from PNG via `iconutil` on macOS runner or `png2icns`)
- Add a simple Python script `dev-tools/generate_icons.py` that creates `.ico` from the PNG (for local dev; macOS `.icns` generated in CI)

### 3. Create PyInstaller spec file

Create `build/innerpix-lab.spec` — a shared spec file with platform-aware configuration:
- Entry point: `main.py`
- `--name`: `InnerPixLab` (Windows/macOS) / `innerpix-lab` (Linux)
- `--windowed` (no console window)
- `--icon`: platform-appropriate icon from `assets/`
- `--add-data`: `i18n/*.json` (translations are required at runtime)
- Hidden imports: `PyQt6`, `PIL`, `cv2`, `imagehash`, `qtawesome` (font files needed)
- Exclude modules: `tkinter`, `matplotlib`, `test`, `unittest`
- `--onedir` mode (needed for native installer packaging)

Remove `*.spec` from `.gitignore` (tracked spec, not auto-generated)

### 4. Create build helper script

Create `dev-tools/build.py` — cross-platform build script:
- Reads version from `Config.APP_VERSION` / `Config.APP_VERSION_SUFFIX`
- Runs PyInstaller with the spec file
- Platform-specific post-processing:
  - **Linux**: Packages into AppImage using `appimagetool`, also creates `.deb` via `fpm`
  - **Windows**: Runs Inno Setup compiler (`iscc`) with `build/installer.iss`
  - **macOS**: Creates `.app` bundle, then `.dmg` via `create-dmg`
- Output: `dist/InnerPixLab-{version}-{platform}.{ext}`

### 5. Create Inno Setup script (Windows installer)

Create `build/installer.iss`:
- App name, version, publisher from config
- Install to `{autopf}\InnerPix Lab`
- Desktop & Start Menu shortcuts
- Uninstaller included
- Icon from `assets/icon.ico`
- License display from `LICENSE`
- Output: `InnerPixLab-{version}-windows-setup.exe`

### 6. Create GitHub Actions CI workflow

Create `.github/workflows/ci.yml`:
- **Triggers**: Push to `main`/`develop`, Pull Requests
- **Matrix**: `ubuntu-latest`, `windows-latest`, `macos-latest`
- **Steps**: checkout → setup Python 3.13 → install deps via `uv` → run `pytest --ignore=tests/performance`
- Purpose: Validate every commit, gate PRs

### 7. Create GitHub Actions Release workflow

Create `.github/workflows/release.yml` — the core automation:
- **Trigger**: Push of a tag matching `v*` (e.g., `v0.8.0-beta`, `v1.0.0`)
- **Matrix build** (3 parallel jobs):

  | Platform | Runner | Installer Output |
  |---|---|---|
  | Linux | `ubuntu-22.04` | `.AppImage` + `.deb` |
  | Windows | `windows-latest` | `.exe` (Inno Setup installer) |
  | macOS | `macos-latest` | `.dmg` |

- **Each job**:
  1. Checkout code
  2. Setup Python 3.13 + `uv`
  3. Install dependencies
  4. Install platform tools (`appimagetool`/`fpm` on Linux, Inno Setup on Windows, `create-dmg` on macOS)
  5. Run PyInstaller with spec file
  6. Run platform-specific installer packaging
  7. Upload artifacts

- **Release job** (after all 3 complete):
  1. Download all artifacts
  2. Create GitHub Release (tag as pre-release if version suffix is non-empty)
  3. Upload all installers as release assets
  4. Generate release notes from commits since last tag

- **Naming convention**:
  - `InnerPixLab-0.8.0-beta-linux-x86_64.AppImage`
  - `InnerPixLab-0.8.0-beta-linux-amd64.deb`
  - `InnerPixLab-0.8.0-beta-windows-setup.exe`
  - `InnerPixLab-0.8.0-beta-macos.dmg`

### 8. Create CHANGELOG.md

Create `CHANGELOG.md` at project root following [Keep a Changelog](https://keepachangelog.com/) format:
- Section for `[0.8.0-beta] - 2026-02-17` with initial feature list
- Template for future releases
- Link to GitHub compare URLs for diffs between tags

### 9. Set up GitHub Pages site

Create `website/` directory (separate from `docs/` which has project docs):

**Structure**:
```
website/
├── _config.yml          # Jekyll config
├── CNAME                # safetoolhub.org
├── index.md             # Landing page (hero + features + download CTA)
├── download.md          # Download page (auto-linked to latest GitHub Release)
├── docs.md              # Documentation (features, requirements, FAQ)
├── changelog.md         # Links to CHANGELOG.md content
├── _layouts/
│   └── default.html     # Base layout with nav + footer
├── assets/
│   ├── css/style.css    # Custom styles
│   └── img/             # Screenshots, logo
└── _includes/
    └── download-buttons.html  # Platform-aware download buttons
```

**Key features**:
- Jekyll with `minima` or a clean custom theme
- Download page with buttons for each platform, linking to latest GitHub Release assets
- JavaScript snippet to fetch latest release from GitHub API and auto-update download links
- Responsive design (desktop + mobile)
- SEO meta tags, Open Graph tags

### 10. Create GitHub Actions Pages deployment workflow

Create `.github/workflows/pages.yml`:
- **Trigger**: Push to `main` (changes in `website/` or `CHANGELOG.md`)
- Build Jekyll site from `website/` directory
- Deploy to GitHub Pages
- Also triggered after release workflow completes (to update download links)

### 11. Configure custom domain

- Create `website/CNAME` with `safetoolhub.org`
- Configure DNS:
  - `safetoolhub.org` → A records pointing to GitHub Pages IPs (185.199.108-111.153)
  - `www.safetoolhub.org` → CNAME to `safetoolhub.github.io`
  - `safetoolhub.com` → redirect to `safetoolhub.org` (at DNS/registrar level)
- Enable HTTPS in GitHub Pages settings (auto Let's Encrypt)

### 12. Create release process documentation

Create `docs/RELEASING.md` documenting the simple release flow:

```
1. Update Config.APP_VERSION / APP_VERSION_SUFFIX in config.py
2. Update CHANGELOG.md with new version section
3. Commit: "Release v0.9.0"
4. Tag: git tag v0.9.0
5. Push: git push origin main --tags
6. → GitHub Actions automatically:
   - Builds binaries for 3 platforms
   - Creates native installers
   - Publishes GitHub Release with assets
   - Updates download page on website
```

### 13. Handle external tool dependencies (ffprobe/exiftool)

Document in the download/docs page:
- **ffprobe** (FFmpeg): Required for video metadata. Not bundled (licensing).
- **exiftool**: Required for advanced EXIF. Not bundled.
- The app already gracefully handles missing tools (shows warnings via `check_ffprobe()`/`check_exiftool()` in `utils/platform_utils.py`)
- Include installation instructions per platform on the docs page

### 14. Update .gitignore

- Remove `*.spec` line (we're tracking our spec file)
- Add `website/_site/` (Jekyll build output)
- Keep `dist/`, `build/output/` excluded

---

## Verification

1. **Local build test**: Run `python dev-tools/build.py` on Linux to verify PyInstaller packaging works
2. **CI check**: Push to a branch, verify `ci.yml` runs tests on all 3 platforms
3. **Release test**: Create tag `v0.8.0-beta`, push it, verify:
   - All 3 platform builds succeed
   - GitHub Release is created with all 6 assets (AppImage, deb, exe, dmg)
   - Release notes are auto-generated
4. **Pages test**: Verify `safetoolhub.org` serves the Jekyll site with working download links
5. **Installer test**: Download and run each installer on its respective platform

## Design Decisions

- **Inno Setup over MSI/NSIS**: Inno Setup is free, well-supported in CI (via `jrsoftware/iscc` action), produces professional-looking Windows installers
- **AppImage + .deb over Snap/Flatpak**: AppImage is universal (no store needed), .deb covers Debian/Ubuntu. Both buildable in CI without special infrastructure
- **`website/` over `docs/`**: Keeps the GitHub Pages site separate from internal project documentation in `docs/`
- **Jekyll over Hugo/static HTML**: Native GitHub Pages support, no extra build step needed (though we'll use Actions for more control), easy Markdown authoring
- **`--onedir` over `--onefile`**: Required for native installer packaging (Inno Setup/AppImage wrap the directory). End users never see the directory — they see only the installer
- **Tag-triggered releases**: Clean, auditable, standard — version in code matches git tag matches release
