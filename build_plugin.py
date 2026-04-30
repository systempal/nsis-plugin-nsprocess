#!/usr/bin/env python3
"""
Build script for nsProcess plugin - All configurations
Supports multiple build configurations with flexible parameters
"""

import argparse
import errno
import multiprocessing
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple

# Ensure stdout/stderr handle Unicode on Windows CI (cp1252 default breaks non-ASCII)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf_8'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _on_rmtree_error(func, path, exc_info):
    if func in (os.unlink, os.rmdir) and exc_info[1].errno == errno.EACCES:
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
            return
        except Exception:
            pass
    for i in range(5):
        try:
            time.sleep(0.1 * (i + 1))
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
            return
        except Exception:
            pass
    raise exc_info[1]


def robust_rmtree(path):
    if not os.path.exists(path):
        return
    try:
        shutil.rmtree(path, onexc=_on_rmtree_error)
    except TypeError:
        try:
            shutil.rmtree(path, onerror=_on_rmtree_error)
        except Exception:
            pass
    except Exception:
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Colors & Spinner
# ---------------------------------------------------------------------------

class Colors:
    CYAN          = "\033[36m"
    GREEN         = "\033[32m"
    YELLOW        = "\033[33m"
    RED           = "\033[31m"
    GRAY          = "\033[90m"
    BLUE          = "\033[34m"
    RESET         = "\033[0m"
    BOLD          = "\033[1m"
    BRIGHT_GREEN  = "\033[92m"
    BRIGHT_CYAN   = "\033[96m"
    BRIGHT_WHITE  = "\033[97m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_RED    = "\033[91m"


class Spinner:
    def __init__(self, message: str = "Building...", delay: float = 0.1, total: int = 0):
        self.spinner    = ['\u280b', '\u2819', '\u2839', '\u2838', '\u283c', '\u2834', '\u2826', '\u2827', '\u2807', '\u280f']
        self.delay      = delay
        self.message    = message
        self.running    = False
        self.thread     = None
        self.start_time = time.time()

    def update(self, current=None):
        pass

    def _spin(self):
        idx    = 0
        _block = '\u28ff'
        while self.running:
            elapsed     = time.time() - self.start_time
            n_blocks    = int(elapsed // 2)
            time_blocks = f"{Colors.YELLOW}{_block * n_blocks}{Colors.RESET}"
            spin_char   = f"{Colors.YELLOW}{self.spinner[idx % len(self.spinner)]}{Colors.RESET}"
            msg         = f"{Colors.BOLD}{Colors.CYAN}{self.message}{Colors.RESET}"
            time_str    = f"{Colors.GREEN}{int(elapsed)}s{Colors.RESET}"
            sys.stdout.write(f"\r{msg} {time_str} {time_blocks}{spin_char} ")
            sys.stdout.flush()
            idx += 1
            time.sleep(self.delay)
        sys.stdout.write("\r" + " " * (len(self.message) + 80) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        if sys.stdout.isatty():
            self.running = True
            self.thread  = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()


# ---------------------------------------------------------------------------
# Build configuration
# ---------------------------------------------------------------------------

class BuildConfig:
    def __init__(self, name: str, config: str, platform: str, dest_dir: str):
        self.name     = name
        self.config   = config
        self.platform = platform
        self.dest_dir = dest_dir


CONFIGS = {
    'x86-ansi':    BuildConfig('x86-ansi',    'Release',         'Win32', 'x86-ansi'),
    'x86-unicode': BuildConfig('x86-unicode',  'Release UNICODE', 'Win32', 'x86-unicode'),
    'x64-unicode': BuildConfig('x64-unicode',  'Release UNICODE', 'x64',   'amd64-unicode'),
}

DLL_NAME     = 'nsProcess.dll'
_VSWHERE     = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe')
_VS_RANGES   = {'2026': '[18.0,19.0)', '2022': '[17.0,18.0)'}
_VS_TOOLSETS = {'2026': 'v145', '2022': 'v143'}


# ---------------------------------------------------------------------------
# MSBuild discovery
# ---------------------------------------------------------------------------

def _find_msbuild_vswhere(vs_version: str) -> Optional[Tuple[Path, str, str]]:
    if not _VSWHERE.exists():
        return None
    to_try = ['2026', '2022'] if vs_version == 'auto' else [vs_version]
    for ver in to_try:
        if ver not in _VS_RANGES:
            continue
        try:
            result = subprocess.run(
                [str(_VSWHERE), '-version', _VS_RANGES[ver], '-latest',
                 '-requires', 'Microsoft.Component.MSBuild',
                 '-find', r'MSBuild\**\Bin\MSBuild.exe'],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
                if lines:
                    p = Path(lines[0])
                    if p.exists():
                        return p, _VS_TOOLSETS[ver], ver
        except Exception:
            pass
    return None


def find_msbuild(vs_version: str = 'auto') -> Optional[Tuple[Path, str, str]]:
    result = _find_msbuild_vswhere(vs_version)
    if result:
        return result
    # Fallback: well-known paths
    to_try = ['2026', '2022'] if vs_version == 'auto' else [vs_version]
    for ver in to_try:
        for edition in ('Community', 'Professional', 'Enterprise', 'BuildTools'):
            p = Path(rf'C:\Program Files\Microsoft Visual Studio\{ver}\{edition}\MSBuild\Current\Bin\MSBuild.exe')
            if p.exists():
                return p, _VS_TOOLSETS[ver], ver
    return None


# ---------------------------------------------------------------------------
# Project paths & version
# ---------------------------------------------------------------------------

def get_project_paths() -> Tuple[Path, Path, Path]:
    script_dir   = Path(__file__).parent.absolute()
    project_dir  = script_dir / 'src'
    project_file = project_dir / 'nsProcess.vcxproj'
    dist_dir     = script_dir / 'dist'
    return project_dir, project_file, dist_dir


def get_plugins_dir() -> Optional[Path]:
    """Return workspace-level plugins/ dir (4 levels above src/modules/<plugin>/)."""
    p = Path(__file__).parent.parent.parent.parent / 'plugins'
    return p if p.is_dir() else None


def read_version() -> str:
    vf = Path(__file__).parent / 'VERSION'
    try:
        return vf.read_text(encoding='utf-8-sig').strip()
    except Exception:
        return '0.0.0'


# ---------------------------------------------------------------------------
# CPU info & build optimizations
# ---------------------------------------------------------------------------

def get_cpu_info() -> dict:
    try:
        import psutil
        logical  = psutil.cpu_count(logical=True)
        physical = psutil.cpu_count(logical=False)
        return {'logical_cores': logical, 'physical_cores': physical,
                'has_hyperthreading': logical > physical, 'has_psutil': True}
    except ImportError:
        n = multiprocessing.cpu_count()
        return {'logical_cores': n, 'physical_cores': n,
                'has_hyperthreading': False, 'has_psutil': False}


def get_optimal_threads() -> int:
    info = get_cpu_info()
    return info['physical_cores'] if info['has_hyperthreading'] and info['physical_cores'] > 1 else info['logical_cores']


def get_build_optimizations() -> List[str]:
    return [
        '/p:BuildInParallel=true',
        '/p:MultiProcessorCompilation=true',
        '/p:PreferredToolArchitecture=x64',
        '/p:UseSharedCompilation=true',
        '/nodeReuse:true',
        '/p:GenerateResourceUsePreserializedResources=true',
    ]


def get_memory_optimizations() -> List[str]:
    try:
        import psutil
        gb = psutil.virtual_memory().total / (1024 ** 3)
        if gb >= 16:
            return ['/p:DisableFastUpToDateCheck=false', '/p:BuildProjectReferences=true',
                    '/p:UseCommonOutputDirectory=false']
        elif gb >= 8:
            return ['/p:DisableFastUpToDateCheck=false']
        return []
    except ImportError:
        return ['/p:DisableFastUpToDateCheck=false']


def print_cpu_info(use_parallel: bool, use_optimizations: bool = True) -> None:
    if not use_parallel:
        print(f"{Colors.CYAN}Build mode:        {Colors.RESET} {Colors.BOLD}Single-threaded{Colors.RESET}")
        if use_optimizations:
            print(f"{Colors.CYAN}Optimizations:     {Colors.RESET} {Colors.GREEN}ENABLED{Colors.RESET} {Colors.GRAY}(memory, caching){Colors.RESET}")
        return

    info    = get_cpu_info()
    optimal = get_optimal_threads()
    print(f"{Colors.CYAN}Build mode:        {Colors.RESET} {Colors.BRIGHT_WHITE}{'Parallel' if use_parallel else 'Sequential'}{Colors.RESET}")
    print(f"{Colors.CYAN}Logical cores:     {Colors.RESET} {Colors.BRIGHT_WHITE}{info['logical_cores']}{Colors.RESET}")
    print(f"{Colors.CYAN}Physical cores:    {Colors.RESET} {Colors.BRIGHT_WHITE}{info['physical_cores']}{Colors.RESET}")
    if info['has_hyperthreading']:
        print(f"{Colors.CYAN}Hyperthreading:    {Colors.RESET} {Colors.BRIGHT_GREEN}ENABLED{Colors.RESET}")
        print(f"{Colors.CYAN}Optimal threads:   {Colors.RESET} {Colors.BRIGHT_WHITE}{optimal}{Colors.RESET} {Colors.GRAY}(using physical cores){Colors.RESET}")
    else:
        print(f"{Colors.CYAN}Hyperthreading:    {Colors.RESET} {Colors.GRAY}NOT AVAILABLE{Colors.RESET}")
        print(f"{Colors.CYAN}Optimal threads:   {Colors.RESET} {Colors.BRIGHT_WHITE}{optimal}{Colors.RESET}")
    print(f"{Colors.CYAN}MSBuild threads:   {Colors.RESET} {Colors.BRIGHT_WHITE}{optimal}{Colors.RESET}")
    if use_optimizations:
        print(f"{Colors.CYAN}Optimizations:     {Colors.RESET} {Colors.BRIGHT_GREEN}ENABLED{Colors.RESET} {Colors.GRAY}(parallel, memory, caching){Colors.RESET}")
        try:
            import psutil
            gb = psutil.virtual_memory().total / (1024 ** 3)
            print(f"{Colors.CYAN}Available memory:  {Colors.RESET} {Colors.BRIGHT_WHITE}{gb:.1f} GB{Colors.RESET}")
        except ImportError:
            print(f"{Colors.CYAN}Available memory:  {Colors.RESET} {Colors.GRAY}Unknown (install psutil){Colors.RESET}")
    else:
        print(f"{Colors.CYAN}Optimizations:     {Colors.RESET} {Colors.BRIGHT_RED}DISABLED{Colors.RESET}")
    if not info['has_psutil']:
        print(f"{Colors.GRAY}Note: Install 'psutil' for detailed CPU/memory info (pip install psutil){Colors.RESET}")
    print()


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------

def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {seconds % 60:.1f}s"
    return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m {seconds % 60:.0f}s"


def build_configuration(
    msbuild_path: Path,
    project_file: Path,
    config: BuildConfig,
    platform_toolset: str,
    *,
    rebuild: bool = True,
    verbosity: str = 'quiet',
    parallel: bool = True,
    optimizations: bool = True,
    counter: str = "",
    capture_output: bool = False,
) -> Tuple[bool, float, str]:
    optimal = get_optimal_threads()
    cmd = [
        str(msbuild_path),
        str(project_file),
        f'/t:{"Rebuild" if rebuild else "Build"}',
        f'/p:Configuration={config.config}',
        f'/p:Platform={config.platform}',
        f'/p:OutDir=Build\\{config.name}\\',
        f'/p:IntDir=Build\\{config.name}\\obj\\',
        '/p:WindowsTargetPlatformVersion=10.0',
        f'/p:PlatformToolset={platform_toolset}',
        f'/v:{verbosity}',
    ]
    if parallel:
        cmd += [f'/maxcpucount:{optimal}', '/p:UseMultiToolTask=true', f'/p:CL_MPCount={optimal}']
    cmd += ['/p:Optimization=MaxSpeed', '/p:ExceptionHandling=Sync']
    if optimizations:
        cmd += get_build_optimizations() + get_memory_optimizations()

    if not capture_output:
        color = Colors.BRIGHT_YELLOW
        print(f"\n{color}{'='*60}{Colors.RESET}")
        label = f"[{counter}] " if counter else ""
        print(f"{color}Building {Colors.BRIGHT_WHITE}{config.name:15s}{Colors.RESET} {color}{label}({'rebuild' if rebuild else 'incremental'}){Colors.RESET}")
        print(f"{color}{'='*60}{Colors.RESET}")

    start = time.time()
    try:
        if capture_output:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            return result.returncode == 0, time.time() - start, result.stdout + result.stderr
        else:
            result = subprocess.run(cmd, check=False)
            return result.returncode == 0, time.time() - start, ""
    except Exception as e:
        elapsed = time.time() - start
        msg = f"ERROR: Build failed with exception: {e}"
        if capture_output:
            return False, elapsed, msg
        print(msg)
        return False, elapsed, ""


def copy_output(project_dir: Path, dist_dir: Path, config: BuildConfig) -> Tuple[bool, int, Optional[Path]]:
    output_file = project_dir / 'Build' / config.name / DLL_NAME
    if not output_file.exists():
        print(f"ERROR: DLL not found: {output_file}")
        return False, 0, None
    dest = dist_dir / config.dest_dir
    dest.mkdir(parents=True, exist_ok=True)
    try:
        dst = dest / DLL_NAME
        shutil.copy2(output_file, dst)
        return True, output_file.stat().st_size, dst
    except Exception as e:
        print(f"ERROR: Failed to copy {config.name}: {e}")
        return False, 0, None


def copy_to_plugins(dist_dir: Path, config: BuildConfig, plugins_dir: Path) -> Optional[Path]:
    """Copy DLL from dist/<dest_dir>/ to plugins/<dest_dir>/."""
    src = dist_dir / config.dest_dir / DLL_NAME
    if not src.exists():
        return None
    dst_dir = plugins_dir / config.dest_dir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / DLL_NAME
    shutil.copy2(src, dst)
    return dst


def clean_build_artifacts(project_dir: Path, configs: List[BuildConfig]) -> None:
    print(f"\n{Colors.CYAN}Cleaning build artifacts...{Colors.RESET}")
    build_base = project_dir / 'Build'
    if not build_base.exists():
        return
    for cfg in configs:
        d = build_base / cfg.name
        if d.exists():
            try:
                robust_rmtree(d)
                print(f"  {Colors.GRAY}- Cleaned:{Colors.RESET} {cfg.name}")
            except Exception as e:
                print(f"  {Colors.RED}- Failed to clean {cfg.name}: {e}{Colors.RESET}")
    try:
        if build_base.exists() and not any(build_base.iterdir()):
            build_base.rmdir()
    except Exception:
        pass
    print(f"{Colors.BRIGHT_GREEN}Build artifacts cleaned successfully.{Colors.RESET}")


def print_available_configurations(project_file: Path) -> None:
    try:
        tree = ET.parse(project_file)
        root = tree.getroot()
        ns   = {'ms': 'http://schemas.microsoft.com/developer/msbuild/2003'}
        configs = []
        for ig in root.findall('.//ms:ItemGroup', ns):
            for pc in ig.findall('ms:ProjectConfiguration', ns):
                inc   = pc.get('Include', '')
                parts = inc.split('|')
                if len(parts) == 2:
                    configs.append(tuple(parts))
        print("Available configurations in project:")
        print("-" * 60)
        from collections import defaultdict
        grouped: dict = defaultdict(list)
        for cfg, plat in configs:
            grouped[cfg].append(plat)
        for cfg_name in sorted(grouped):
            print(f"  {cfg_name:25s} - {', '.join(sorted(grouped[cfg_name]))}")
        print(f"\nTotal: {len(configs)} configuration(s)\n")
    except Exception as e:
        print(f"Could not parse project file: {e}")


_print_lock = threading.Lock()


def _build_configs_parallel(
    msbuild_path: Path,
    project_file: Path,
    configs: List[BuildConfig],
    platform_toolset: str,
    *,
    rebuild: bool,
    verbosity: str,
    parallel: bool,
    optimizations: bool,
    project_dir: Path,
    dist_dir: Path,
) -> list:
    n = len(configs)
    print(f"\nParallel: launching {n} builds simultaneously...")
    print("=" * 50)
    total_start     = time.time()
    results_by_idx: dict = {}
    idx_lock        = threading.Lock()

    def _build_one(idx: int, config: BuildConfig):
        import contextlib
        import io as _io
        success, build_time, captured = build_configuration(
            msbuild_path, project_file, config, platform_toolset,
            rebuild=rebuild, verbosity=verbosity,
            parallel=parallel, optimizations=optimizations,
            capture_output=True,
        )
        copy_buf = _io.StringIO()
        if success:
            with contextlib.redirect_stdout(copy_buf):
                copy_ok, file_size, dest_path = copy_output(project_dir, dist_dir, config)
        else:
            copy_ok, file_size, dest_path = False, 0, None

        with _print_lock:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
            tag      = "OK" if (success and copy_ok) else "FAILED"
            size_str = f"{file_size:,} bytes" if file_size > 0 else "N/A"
            copy_out = copy_buf.getvalue()
            if copy_out.strip():
                print(copy_out.rstrip())
            if captured.strip():
                lines    = [ln for ln in captured.splitlines() if "MSBuild" not in ln and "Copyright" not in ln]
                filtered = "\n".join(lines).strip()
                if filtered:
                    print(filtered)
            color = Colors.BRIGHT_GREEN if (success and copy_ok) else Colors.RED
            print(f"{color}[{tag}]{Colors.RESET} {config.name}  ({format_time(build_time)})  {size_str}")
            if dest_path:
                print(f"        -> {dest_path}")

        with idx_lock:
            results_by_idx[idx] = (config, success and copy_ok, build_time, file_size, dest_path)

    with Spinner("Building configurations...", total=n) as s:
        with ThreadPoolExecutor(max_workers=n) as executor:
            futures = {executor.submit(_build_one, i, cfg): i for i, cfg in enumerate(configs)}
            for fut in as_completed(futures):
                s.update()
                exc = fut.exception()
                if exc:
                    idx = futures[fut]
                    with _print_lock:
                        print(f"ERROR: worker for config index {idx} raised: {exc}")
                    with idx_lock:
                        results_by_idx[idx] = (configs[idx], False, 0.0, 0, None)

    wall = time.time() - total_start
    print(f"\nAll {n} configs finished in {format_time(wall)} (wall clock)")
    return [results_by_idx[i] for i in range(n)]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description='Build nsProcess plugin for NSIS')
    parser.add_argument('--configs', nargs='+',
                        choices=list(CONFIGS.keys()) + ['all'], default=None)
    parser.add_argument('--config',                           # singular alias used by CI
                        choices=list(CONFIGS.keys()) + ['all'], default=None)
    parser.add_argument('--rebuild',     action='store_true',  default=True)
    parser.add_argument('--no-rebuild',  action='store_false', dest='rebuild')
    parser.add_argument('--parallel',    action='store_true',  default=True)
    parser.add_argument('--no-parallel', action='store_false', dest='parallel')
    parser.add_argument('--verbosity',
                        choices=['quiet', 'minimal', 'normal', 'detailed', 'diagnostic'],
                        default='quiet')
    parser.add_argument('--clean',         action='store_true', default=False)
    parser.add_argument('--list',          action='store_true')
    parser.add_argument('--list-project',  action='store_true')
    parser.add_argument('--no-optimizations', action='store_true')
    parser.add_argument('--vs-version',    choices=['auto', '2026', '2022'], default='auto')
    parser.add_argument('--final',         action='store_true', default=False,
                        help='Force rebuild + clean (pre-release build)')
    parser.add_argument('--install-dir',   type=Path, default=None,
                        help='Copy built DLLs to this directory (in <config>/ subdirs)')
    args = parser.parse_args()

    # Merge --config (singular) into --configs list
    if args.config and not args.configs:
        args.configs = [args.config]

    if args.final:
        args.rebuild = True
        args.clean   = True

    project_dir, project_file, dist_dir = get_project_paths()

    if args.list_project:
        print_available_configurations(project_file)
        return 0

    if args.list:
        for name, config in CONFIGS.items():
            print(f"  {name:15s} -> {config.config} / {config.platform}")
        return 0

    if not project_file.exists():
        print(f"ERROR: project file not found: {project_file}", file=sys.stderr)
        return 3

    msbuild_result = find_msbuild(args.vs_version)
    if not msbuild_result:
        print("ERROR: MSBuild not found. Install Visual Studio 2022 or 2026.", file=sys.stderr)
        return 2
    msbuild_path, platform_toolset, vs_version_name = msbuild_result

    version = read_version()

    if not args.configs:
        configs_to_build = list(CONFIGS.values())
    elif 'all' in args.configs:
        configs_to_build = list(CONFIGS.values())
    else:
        configs_to_build = [CONFIGS[n] for n in args.configs]

    # Banner
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'='*60}")
    print(f"Building nsProcess plugin v{version} - {Colors.BRIGHT_WHITE}{len(configs_to_build)}{Colors.RESET} {Colors.BOLD}{Colors.BRIGHT_CYAN}configuration(s)")
    print(f"{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}VS:           {Colors.RESET} {Colors.BRIGHT_WHITE}{vs_version_name}{Colors.RESET} {Colors.GRAY}({platform_toolset}){Colors.RESET}")
    print(f"{Colors.CYAN}MSBuild:      {Colors.RESET} {Colors.BRIGHT_WHITE}{msbuild_path}{Colors.RESET}")
    print(f"{Colors.CYAN}Project:      {Colors.RESET} {Colors.BRIGHT_WHITE}{project_file}{Colors.RESET}")
    print(f"{Colors.CYAN}Dist:         {Colors.RESET} {Colors.BRIGHT_WHITE}{dist_dir}{Colors.RESET}")
    print(f"{Colors.CYAN}Rebuild:      {Colors.RESET} {Colors.BRIGHT_WHITE}{args.rebuild}{Colors.RESET}")
    print(f"{Colors.CYAN}Verbosity:    {Colors.RESET} {Colors.BRIGHT_WHITE}{args.verbosity}{Colors.RESET}")
    print()

    use_optimizations = not args.no_optimizations
    print_cpu_info(args.parallel, use_optimizations)

    build_results = []
    total_start   = time.time()

    if args.parallel and len(configs_to_build) > 1:
        build_results = _build_configs_parallel(
            msbuild_path, project_file, configs_to_build, platform_toolset,
            rebuild=args.rebuild, verbosity=args.verbosity,
            parallel=True, optimizations=use_optimizations,
            project_dir=project_dir, dist_dir=dist_dir,
        )
    else:
        for i, config in enumerate(configs_to_build, 1):
            success, b_time, _ = build_configuration(
                msbuild_path, project_file, config, platform_toolset,
                rebuild=args.rebuild, verbosity=args.verbosity,
                parallel=args.parallel, optimizations=use_optimizations,
                counter=f"{i}/{len(configs_to_build)}",
            )
            if success:
                ok, size, path = copy_output(project_dir, dist_dir, config)
                build_results.append((config, ok, b_time, size, path))
            else:
                build_results.append((config, False, b_time, 0, None))

    total_time  = time.time() - total_start
    all_success = all(res[1] for res in build_results)

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_GREEN if all_success else Colors.RED}{'='*50}")
    print("ALL BUILDS SUCCESSFUL!" if all_success else "SOME BUILDS FAILED!")
    print(f"{'='*50}{Colors.RESET}")

    # Copy to workspace plugins/ dir if present
    plugins_dir    = get_plugins_dir()
    plugins_copied = []
    if plugins_dir and all_success:
        for cfg, ok, _, _, _ in build_results:
            if ok:
                dst = copy_to_plugins(dist_dir, cfg, plugins_dir)
                if dst:
                    plugins_copied.append(str(dst))
        if plugins_copied:
            print(f"\n{Colors.CYAN}Installed to plugins/:{Colors.RESET}")
            for p in plugins_copied:
                print(f"  {Colors.GRAY}->{Colors.RESET} {p}")

    if args.install_dir and all_success:
        print(f"\n{Colors.CYAN}Installing to {args.install_dir}...{Colors.RESET}")
        for cfg, ok, _, _, path in build_results:
            if ok and path:
                dest = args.install_dir / cfg.dest_dir
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest / DLL_NAME)
                print(f"  {Colors.GRAY}- Installed:{Colors.RESET} {dest / DLL_NAME}")

    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'-'*50}")
    print(f"Build Summary - VS {vs_version_name} ({platform_toolset}):")
    for cfg, ok, b_time, size, _ in build_results:
        color = Colors.GREEN if ok else Colors.RED
        tag   = "OK  " if ok else "FAIL"
        print(f"  {color}{tag}{Colors.RESET} {cfg.name:15s} - {format_time(b_time):8s} - {size:11,d} bytes")
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'-'*50}{Colors.RESET}")
    print(f"Total time: {format_time(total_time)}\n")

    if args.clean:
        clean_build_artifacts(project_dir, configs_to_build)

    return 0 if all_success else 1


if __name__ == '__main__':
    sys.exit(main())
