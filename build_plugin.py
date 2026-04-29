#!/usr/bin/env python3
"""
Build script canonico per il plugin nsProcess.

CLI standard: vedi `python build_plugin.py --help`
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
DIST_DIR = ROOT / "dist"
VERSION_FILE = ROOT / "VERSION"

# Mapping CLI config -> (MSBuild Configuration, MSBuild Platform, dist subdir)
CONFIGS = {
    "x86-ansi":     ("Release",         "Win32", "x86-ansi"),
    "x86-unicode":  ("Release Unicode", "Win32", "x86-unicode"),
    "x64-unicode":  ("Release Unicode", "x64",   "amd64-unicode"),
}

VCXPROJ = SRC_DIR / "nsProcess.vcxproj"
DLL_NAME = "nsProcess.dll"


def read_version() -> str:
    # utf-8-sig strips BOM (\ufeff) automatically
    return VERSION_FILE.read_text(encoding="utf-8-sig").strip()


def find_msbuild(toolset: str) -> Path:
    """Localizza MSBuild via vswhere; toolset='2022', '2026', o 'auto'.

    In auto mode, tries 2022 before 2026 because most vcxproj files use
    PlatformToolset v143 (VS2022) which may not be available in VS2026 build tools.
    """
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = Path(pf86) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.exists():
        sys.exit(2)

    def _query(version_range: str | None) -> list[str]:
        args = [str(vswhere), "-latest", "-products", "*",
                "-requires", "Microsoft.Component.MSBuild",
                "-find", r"MSBuild\**\Bin\MSBuild.exe"]
        if version_range:
            args += ["-version", version_range]
        result = subprocess.run(args, capture_output=True, text=True)
        return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]

    if toolset == "2022":
        paths = _query("[17.0,18.0)")
    elif toolset == "2026":
        paths = _query("[18.0,19.0)")
    else:  # auto: prefer 2022 (v143) over 2026 (v145)
        paths = _query("[17.0,18.0)") or _query("[18.0,19.0)") or _query(None)

    if not paths:
        sys.exit(2)
    return Path(paths[0])


def build_one(msbuild: Path, config: str, platform: str, jobs: int, verbose: bool) -> bool:
    cmd = [
        str(msbuild), str(VCXPROJ),
        f"/p:Configuration={config}",
        f"/p:Platform={platform}",
        f"/m:{jobs}",
        "/nologo",
        "/v:" + ("normal" if verbose else "minimal"),
    ]
    print(f"[build] {config} | {platform}")
    return subprocess.run(cmd).returncode == 0


def collect_dll(config: str, platform: str, dist_subdir: str) -> Path | None:
    """Trova la DLL prodotta dal vcxproj e la copia in dist/<dist_subdir>/."""
    plat_dir = "" if platform == "Win32" else platform + "/"
    candidates = list(SRC_DIR.glob(f"**/{plat_dir}{config}/{DLL_NAME}"))
    candidates += list(ROOT.glob(f"**/{plat_dir}{config}/{DLL_NAME}"))
    if not candidates:
        return None
    src = candidates[0]
    dst_dir = DIST_DIR / dist_subdir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / DLL_NAME
    shutil.copy2(src, dst)
    return dst


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Build nsProcess plugin")
    parser.add_argument("--config", default="all",
                        choices=list(CONFIGS.keys()) + ["all"])
    parser.add_argument("--toolset", default="auto", choices=["2022", "2026", "auto"])
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--install-dir", type=Path, default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--version", action="store_true",
                        help="Mostra versione e termina")
    args = parser.parse_args()

    if args.version:
        print(read_version())
        return 0

    if not VCXPROJ.exists():
        print(f"ERROR: {VCXPROJ} not found", file=sys.stderr)
        return 3

    if args.clean and DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    msbuild = find_msbuild(args.toolset)
    print(f"[info] MSBuild: {msbuild}")
    print(f"[info] Version: {read_version()}")

    targets = list(CONFIGS.keys()) if args.config == "all" else [args.config]
    failed = []
    for cfg_name in targets:
        config, platform, subdir = CONFIGS[cfg_name]
        if not build_one(msbuild, config, platform, args.jobs, args.verbose):
            failed.append(cfg_name)
            continue
        dst = collect_dll(config, platform, subdir)
        if dst is None:
            print(f"ERROR: DLL not found for {cfg_name}", file=sys.stderr)
            failed.append(cfg_name)
        else:
            print(f"[ok] {dst}")
            if args.install_dir:
                install_path = args.install_dir / subdir
                install_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, install_path / DLL_NAME)
                print(f"[install] {install_path / DLL_NAME}")

    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
        return 1
    print("[done] all targets built successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
