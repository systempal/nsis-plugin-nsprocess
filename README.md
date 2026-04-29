# nsProcess NSIS Plugin v1.6

**Personal modified version**

---

## Original Description

**2006 Shengalts Aleksander aka Instructor (Shengalts@mail.ru)**

Source function FIND_PROC_BY_NAME based upon the Ravi Kochhar (kochhar@physiology.wisc.edu) code.
Thanks iceman_k (FindProcDLL plugin) and DITMan (KillProcDLL plugin) for direct me.
NSIS UNICODE compatible version (1.6) by brainsucker.

## Features

- Find a process by name
- Kill all processes with specified name (not only one)
- Close all processes with specified name (first tries to close all process windows, waits for 3 seconds for process to exit, terminates if still alive)
- The process name is case-insensitive
- Win95/98/ME/NT/2000/XP/Win7 support
- Small plugin size (4 Kb)
- NSIS UNICODE support

## Usage

### Find process

```nsis
${nsProcess::FindProcess} "[file.exe]" $var
```

**Parameters:**
- `[file.exe]` - Process name (e.g. "notepad.exe")

**Return values ($var):**
| Code | Description |
|------|-------------|
| 0 | Success |
| 603 | Process was not currently running |
| 604 | Unable to identify system type |
| 605 | Unsupported OS |
| 606 | Unable to load NTDLL.DLL |
| 607 | Unable to get procedure address from NTDLL.DLL |
| 608 | NtQuerySystemInformation failed |
| 609 | Unable to load KERNEL32.DLL |
| 610 | Unable to get procedure address from KERNEL32.DLL |
| 611 | CreateToolhelp32Snapshot failed |

### Kill/Close process

```nsis
${nsProcess::KillProcess} "[file.exe]" $var
${nsProcess::CloseProcess} "[file.exe]" $var
```

**Parameters:**
- `[file.exe]` - Process name (e.g. "notepad.exe")

**Return values ($var):**
| Code | Description |
|------|-------------|
| 0 | Success |
| 601 | No permission to terminate process |
| 602 | Not all processes terminated successfully |
| 603 | Process was not currently running |
| 604 | Unable to identify system type |
| 605 | Unsupported OS |
| 606 | Unable to load NTDLL.DLL |
| 607 | Unable to get procedure address from NTDLL.DLL |
| 608 | NtQuerySystemInformation failed |
| 609 | Unable to load KERNEL32.DLL |
| 610 | Unable to get procedure address from KERNEL32.DLL |
| 611 | CreateToolhelp32Snapshot failed |

### Direct plugin call (without macros)

```nsis
nsProcess::_CloseProcess "notepad.exe"
Pop $R0
```

### Unload plugin

```nsis
${nsProcess::Unload}
```

## Example

```nsis
!include "nsProcess.nsh"

Section "Check Notepad"
    ${nsProcess::FindProcess} "notepad.exe" $R0
    ${If} $R0 == 0
        MessageBox MB_YESNO "Notepad is running. Close it?" IDNO skip
        ${nsProcess::CloseProcess} "notepad.exe" $R0
        ${If} $R0 == 0
            MessageBox MB_OK "Notepad closed successfully"
        ${Else}
            MessageBox MB_OK "Failed to close Notepad"
        ${EndIf}
        skip:
    ${Else}
        MessageBox MB_OK "Notepad is not running"
    ${EndIf}
    ${nsProcess::Unload}
SectionEnd
```

## Include file

Include `nsProcess.nsh` to use the macros:

```nsis
!include "nsProcess.nsh"
```

---

## ⚠️ Differences in the Personal Version

### New supported architecture: x64 (amd64-unicode)

The original supported only:
- x86-ansi (Plugins\nsProcess.dll)
- x86-unicode (nsProcessW.dll renamed to nsProcess.dll)

The personal version adds support for:
- **amd64-unicode** (x64)

### Visual Studio Project

The original included:
- `Source/nsProcess.sln` - VS2008 Solution
- `Source/nsProcess.vcproj` - VS2008 Project (x86 only)

The personal version upgrades to VS2022 with x64 support:
- `nsProcess.sln` - VS2022 Solution
- `nsProcess/nsProcess.vcxproj` - VS2022 Project (x86-ansi, x86-unicode, amd64-unicode)

### Added Files

- `build_plugin.py` - Python script to compile the plugin for all architectures
- `nsis/` - Folder with NSIS headers for compilation:
  - `api.h`, `crt.c`, `nsis_tchar.h`, `pluginapi.c`, `pluginapi.h`

### Removed Files

Pre-compiled DLL files have been removed from the distribution:

- `Plugins/nsProcess.dll` (x86 ANSI)
- `nsProcessW.dll` (x86 UNICODE)

### Build

```cmd
cd nsProcess
python build_plugin.py
```

DLLs are copied to `plugins/{platform}/nsProcess.dll`.

### Build Options

```powershell
python build_plugin.py --config x86-unicode      # Single architecture (x86-ansi|x86-unicode|amd64-unicode|all)
python build_plugin.py --toolset 2026            # Specific toolset (2022|2026|auto)
python build_plugin.py --jobs 4                  # Number of parallel MSBuild jobs (default: CPU count)
python build_plugin.py --clean                   # Clean dist/ before build
python build_plugin.py --install-dir "C:\NSIS\Plugins"  # Copy to additional NSIS directory
python build_plugin.py --verbose                 # Extended MSBuild output
python build_plugin.py --version                 # Print version and exit
```

### Functional Changes

No functional changes compared to the original. Modifications are limited to the build infrastructure and x64 support.

---

*See [README_IT.md](README_IT.md) for the Italian version.*
