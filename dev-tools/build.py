#!/usr/bin/env python3
"""
Build script for InnerPix Lab.

Runs PyInstaller and then creates platform-specific installers:
  - Linux:   .deb (dpkg-deb) + .rpm (rpmbuild)
  - Windows: Inno Setup .exe installer
  - macOS:   .dmg disk image

Usage:
    python dev-tools/build.py              # Build for current platform
    python dev-tools/build.py --skip-installer  # PyInstaller only, no installer packaging

Requires:
  - PyInstaller (pip install pyinstaller)
  - Linux:   dpkg-deb (pre-installed on Debian/Ubuntu), rpmbuild (rpm package)
  - Windows: Inno Setup 6 (iscc on PATH)
  - macOS:   create-dmg (brew install create-dmg)
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

# Windows terminals may use cp1252 — force UTF-8 for Unicode box chars and emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "build" / "innerpix-lab.spec"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"

# Import version from config (add project root to path)
sys.path.insert(0, str(ROOT))


def get_version_info() -> tuple[str, str, str]:
    """Return (version, suffix, full_version) from Config."""
    from config import Config
    return Config.APP_VERSION, Config.APP_VERSION_SUFFIX, Config.get_full_version()


def run(cmd: list[str], **kwargs) -> None:
    """Run a command, printing it first."""
    print(f"  $ {' '.join(cmd)}")
    subprocess.check_call(cmd, **kwargs)


def build_pyinstaller() -> Path:
    """Run PyInstaller and return path to the output directory."""
    print("\n══════════════════════════════════════════════════════════")
    print("  PyInstaller Build")
    print("══════════════════════════════════════════════════════════\n")

    version, suffix, full = get_version_info()
    env = os.environ.copy()
    env["APP_VERSION"] = version

    run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath", str(DIST_DIR),
            "--workpath", str(BUILD_DIR / "pyinstaller-work"),
            str(SPEC_FILE),
        ],
        env=env,
    )

    # Determine output directory name
    if sys.platform == "win32" or sys.platform == "darwin":
        app_name = "InnerPixLab"
    else:
        app_name = "innerpix-lab"

    output_dir = DIST_DIR / app_name
    if not output_dir.exists():
        print(f"ERROR: Expected output at {output_dir}")
        sys.exit(1)

    print(f"\n✅ PyInstaller output: {output_dir}")
    return output_dir


def package_linux(output_dir: Path, full_version: str) -> list[Path]:
    """Create .deb and .rpm packages using standard system tools."""
    print("\n── Linux Packaging ──────────────────────────────────────\n")
    artifacts = []
    app_name = "innerpix-lab"
    arch_deb = "amd64"
    arch_rpm = "x86_64"
    install_prefix = f"opt/{app_name}"

    # ── Common: prepare staging directory ──
    staging = DIST_DIR / "staging"
    if staging.exists():
        shutil.rmtree(staging)

    # Application files
    app_dest = staging / install_prefix
    shutil.copytree(output_dir, app_dest)

    # Desktop entry
    desktop_dir = staging / "usr" / "share" / "applications"
    desktop_dir.mkdir(parents=True)
    desktop_entry = textwrap.dedent(f"""\
        [Desktop Entry]
        Type=Application
        Name=Innerpix Lab
        Exec=/{install_prefix}/{app_name}
        Icon={app_name}
        Categories=Graphics;Photography;
        Comment=Privacy-first photo and video management
        Terminal=false
    """)
    (desktop_dir / f"{app_name}.desktop").write_text(desktop_entry)

    # Icon
    icon_src = ROOT / "assets" / "icon.png"
    icon_dest = staging / "usr" / "share" / "icons" / "hicolor" / "512x512" / "apps"
    icon_dest.mkdir(parents=True)
    if icon_src.exists():
        shutil.copy2(icon_src, icon_dest / f"{app_name}.png")

    # Symlink in /usr/bin
    bin_dir = staging / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    symlink = bin_dir / app_name
    symlink.symlink_to(f"/{install_prefix}/{app_name}")

    # ── .deb via dpkg-deb ──
    dpkg_deb = shutil.which("dpkg-deb")
    if dpkg_deb:
        deb_root = DIST_DIR / "deb-build"
        if deb_root.exists():
            shutil.rmtree(deb_root)
        shutil.copytree(staging, deb_root, symlinks=True)

        # DEBIAN control
        debian_dir = deb_root / "DEBIAN"
        debian_dir.mkdir()
        control = textwrap.dedent(f"""\
            Package: {app_name}
            Version: {full_version}
            Section: graphics
            Priority: optional
            Architecture: {arch_deb}
            Maintainer: SafeToolHub <contact@safetoolhub.org>
            Description: Privacy-first photo and video management
             Innerpix Lab manages, organizes, and optimizes photo/video
             collections with absolute privacy. 100% local processing,
             no cloud, no telemetry.
            Homepage: https://safetoolhub.org
        """)
        (debian_dir / "control").write_text(control)

        deb_name = f"InnerPixLab-{full_version}-linux-{arch_deb}.deb"
        deb_path = DIST_DIR / deb_name
        if deb_path.exists():
            deb_path.unlink()

        run([dpkg_deb, "--build", "--root-owner-group", str(deb_root), str(deb_path)])
        if deb_path.exists():
            artifacts.append(deb_path)
            print(f"✅ Deb: {deb_path}")
    else:
        print("⚠️  dpkg-deb not found, skipping .deb")

    # ── .rpm via rpmbuild ──
    rpmbuild = shutil.which("rpmbuild")
    if rpmbuild:
        rpm_topdir = DIST_DIR / "rpm-build"
        if rpm_topdir.exists():
            shutil.rmtree(rpm_topdir)
        for d in ["BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS", "BUILDROOT"]:
            (rpm_topdir / d).mkdir(parents=True)

        # Create tarball for rpmbuild
        tarball_name = f"{app_name}-{full_version}"
        tarball_src = rpm_topdir / "SOURCES" / tarball_name
        shutil.copytree(staging, tarball_src)

        spec_content = textwrap.dedent(f"""\
            Name:           {app_name}
            Version:        {full_version.replace('-', '_')}
            Release:        1%{{?dist}}
            Summary:        Privacy-first photo and video management
            License:        Proprietary
            URL:            https://safetoolhub.org

            AutoReqProv:    no

            %description
            Innerpix Lab manages, organizes, and optimizes photo/video
            collections with absolute privacy. 100% local processing,
            no cloud, no telemetry.

            %install
            cp -a %{{_sourcedir}}/{tarball_name}/* %{{buildroot}}/

            %files
            /{install_prefix}/
            /usr/bin/{app_name}
            /usr/share/applications/{app_name}.desktop
            /usr/share/icons/hicolor/512x512/apps/{app_name}.png
        """)
        spec_path = rpm_topdir / "SPECS" / f"{app_name}.spec"
        spec_path.write_text(spec_content)

        try:
            run([
                rpmbuild, "-bb",
                "--define", f"_topdir {rpm_topdir}",
                str(spec_path),
            ])

            # Find the output RPM
            rpm_out = rpm_topdir / "RPMS" / arch_rpm
            if rpm_out.exists():
                for rpm_file in rpm_out.glob("*.rpm"):
                    dest = DIST_DIR / f"InnerPixLab-{full_version}-linux-{arch_rpm}.rpm"
                    shutil.move(str(rpm_file), str(dest))
                    artifacts.append(dest)
                    print(f"✅ RPM: {dest}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  rpmbuild failed: {e}")
    else:
        print("⚠️  rpmbuild not found, skipping .rpm")

    return artifacts


def package_windows(output_dir: Path, full_version: str, version: str) -> list[Path]:
    """Create Inno Setup installer."""
    print("\n── Windows Packaging ────────────────────────────────────\n")
    artifacts = []

    iscc = shutil.which("iscc") or shutil.which("ISCC")
    iss = BUILD_DIR / "installer.iss"

    if iscc and iss.exists():
        env = os.environ.copy()
        env["APP_VERSION"] = version
        env["APP_FULL_VERSION"] = full_version

        run([iscc, str(iss)], env=env)

        # Find the output exe
        installer_name = f"InnerPixLab-{full_version}-windows-setup.exe"
        expected = DIST_DIR / installer_name
        if expected.exists():
            artifacts.append(expected)
            print(f"✅ Installer: {expected}")
        else:
            # Check default Inno output
            inno_output = BUILD_DIR / "Output"
            if inno_output.exists():
                for f in inno_output.iterdir():
                    if f.suffix == ".exe":
                        dest = DIST_DIR / installer_name
                        shutil.move(str(f), str(dest))
                        artifacts.append(dest)
                        print(f"✅ Installer: {dest}")
    else:
        if not iscc:
            print("⚠️  Inno Setup (iscc) not found, skipping Windows installer")
        if not iss.exists():
            print(f"⚠️  {iss} not found, skipping Windows installer")

    return artifacts


def package_macos(output_dir: Path, full_version: str) -> list[Path]:
    """Create .dmg from .app bundle."""
    print("\n── macOS Packaging ─────────────────────────────────────\n")
    artifacts = []

    app_bundle = DIST_DIR / "InnerPixLab.app"
    if not app_bundle.exists():
        print(f"⚠️  {app_bundle} not found, skipping DMG")
        return artifacts

    dmg_name = f"InnerPixLab-{full_version}-macos.dmg"
    dmg_path = DIST_DIR / dmg_name

    create_dmg = shutil.which("create-dmg")
    if create_dmg:
        if dmg_path.exists():
            dmg_path.unlink()

        try:
            run([
                create_dmg,
                "--volname", "Innerpix Lab",
                "--volicon", str(ROOT / "assets" / "icon.icns"),
                "--window-pos", "200", "120",
                "--window-size", "600", "400",
                "--icon-size", "100",
                "--icon", "InnerPixLab.app", "175", "200",
                "--app-drop-link", "425", "200",
                str(dmg_path),
                str(app_bundle),
            ])
        except subprocess.CalledProcessError:
            # create-dmg exits 2 on "no code sign" which is OK
            pass

        if dmg_path.exists():
            artifacts.append(dmg_path)
            print(f"✅ DMG: {dmg_path}")
    else:
        # Fallback: hdiutil
        try:
            run([
                "hdiutil", "create",
                "-volname", "Innerpix Lab",
                "-srcfolder", str(app_bundle),
                "-ov",
                "-format", "UDZO",
                str(dmg_path),
            ])
            if dmg_path.exists():
                artifacts.append(dmg_path)
                print(f"✅ DMG: {dmg_path}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  create-dmg/hdiutil not available, skipping DMG")

    return artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="Build InnerPix Lab")
    parser.add_argument("--skip-installer", action="store_true",
                        help="Only run PyInstaller, skip native installer packaging")
    args = parser.parse_args()

    version, suffix, full_version = get_version_info()
    print(f"Building InnerPix Lab v{full_version}")
    print(f"Platform: {platform.system()} {platform.machine()}")

    # Step 1: PyInstaller
    output_dir = build_pyinstaller()

    if args.skip_installer:
        print("\n--skip-installer: Skipping native packaging")
        return

    # Step 2: Platform-specific packaging
    artifacts = []
    system = platform.system()

    if system == "Linux":
        artifacts = package_linux(output_dir, full_version)
    elif system == "Windows":
        artifacts = package_windows(output_dir, full_version, version)
    elif system == "Darwin":
        artifacts = package_macos(output_dir, full_version)

    # Summary
    print("\n══════════════════════════════════════════════════════════")
    print("  Build Summary")
    print("══════════════════════════════════════════════════════════\n")
    print(f"  Version:  {full_version}")
    print(f"  Platform: {system}")
    if artifacts:
        print("  Artifacts:")
        for a in artifacts:
            size_mb = a.stat().st_size / (1024 * 1024)
            print(f"    • {a.name}  ({size_mb:.1f} MB)")
    else:
        print(f"  PyInstaller output: {output_dir}")
        print("  (No native installer created)")
    print()


if __name__ == "__main__":
    main()
