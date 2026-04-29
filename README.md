# nsProcess NSIS Plugin v1.6

**Versione personale modificata**

---

## Descrizione Originale

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

## ⚠️ Differenze nella versione personale

### Nuova architettura supportata: x64 (amd64-unicode)

L'originale supportava solo:
- x86-ansi (Plugins\nsProcess.dll)
- x86-unicode (nsProcessW.dll da rinominare in nsProcess.dll)

La versione personale aggiunge il supporto per:
- **amd64-unicode** (x64)

### Progetto Visual Studio

L'originale includeva:
- `Source/nsProcess.sln` - Solution VS2008
- `Source/nsProcess.vcproj` - Progetto VS2008 (solo x86)

La versione personale converte a VS2022 con supporto x64:
- `nsProcess.sln` - Solution VS2022
- `nsProcess/nsProcess.vcxproj` - Progetto VS2022 (x86-ansi, x86-unicode, amd64-unicode)

### File aggiunti

- `build_plugin.py` - Script Python per compilare il plugin per tutte le architetture
- `nsis/` - Cartella con gli header NSIS per la compilazione:
  - `api.h`, `crt.c`, `nsis_tchar.h`, `pluginapi.c`, `pluginapi.h`

### File rimossi

I file DLL precompilati sono stati rimossi dalla distribuzione:

- `Plugins/nsProcess.dll` (x86 ANSI)
- `nsProcessW.dll` (x86 UNICODE)

### Compilazione

```cmd
cd nsProcess
python build_plugin.py
```

I DLL vengono copiati in `plugins/{platform}/nsProcess.dll`.

### Modifiche funzionali

Nessuna modifica funzionale rispetto all'originale. Le modifiche riguardano solo l'infrastruttura di build e il supporto x64.