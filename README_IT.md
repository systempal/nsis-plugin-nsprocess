# nsProcess NSIS Plugin v1.6

**Versione personale modificata**

---

## Descrizione Originale

**2006 Shengalts Aleksander aka Instructor (Shengalts@mail.ru)**

Funzione sorgente FIND_PROC_BY_NAME basata sul codice di Ravi Kochhar (kochhar@physiology.wisc.edu).
Grazie a iceman_k (plugin FindProcDLL) e DITMan (plugin KillProcDLL) per l'ispirazione.
Versione NSIS UNICODE compatibile (1.6) di brainsucker.

## Funzionalità

- Cerca un processo per nome
- Termina tutti i processi con il nome specificato (non solo uno)
- Chiude tutti i processi con il nome specificato (prima tenta di chiudere le finestre, attende 3 secondi, poi termina se ancora attivo)
- Il nome del processo non è case-sensitive
- Supporto Win95/98/ME/NT/2000/XP/Win7
- Dimensione plugin ridotta (4 Kb)
- Supporto NSIS UNICODE

## Utilizzo

### Ricerca processo

```nsis
${nsProcess::FindProcess} "[file.exe]" $var
```

**Parametri:**
- `[file.exe]` - Nome processo (es. "notepad.exe")

**Valori restituiti ($var):**
| Codice | Descrizione |
|--------|-------------|
| 0 | Successo |
| 603 | Processo non in esecuzione |
| 604 | Impossibile identificare il tipo di sistema |
| 605 | OS non supportato |
| 606 | Impossibile caricare NTDLL.DLL |
| 607 | Impossibile ottenere l'indirizzo della procedura da NTDLL.DLL |
| 608 | NtQuerySystemInformation fallita |
| 609 | Impossibile caricare KERNEL32.DLL |
| 610 | Impossibile ottenere l'indirizzo della procedura da KERNEL32.DLL |
| 611 | CreateToolhelp32Snapshot fallita |

### Terminazione/Chiusura processo

```nsis
${nsProcess::KillProcess} "[file.exe]" $var
${nsProcess::CloseProcess} "[file.exe]" $var
```

**Valori restituiti ($var):**
| Codice | Descrizione |
|--------|-------------|
| 0 | Successo |
| 601 | Permessi insufficienti per terminare il processo |
| 602 | Non tutti i processi sono stati terminati |
| 603 | Processo non in esecuzione |
| 604 | Impossibile identificare il tipo di sistema |
| 605 | OS non supportato |
| ... | (vedi sopra) |

### Chiamata diretta al plugin (senza macro)

```nsis
nsProcess::_CloseProcess "notepad.exe"
Pop $R0
```

### Scaricamento plugin

```nsis
${nsProcess::Unload}
```

## Esempio

```nsis
!include "nsProcess.nsh"

Section "Verifica Notepad"
    ${nsProcess::FindProcess} "notepad.exe" $R0
    ${If} $R0 == 0
        MessageBox MB_YESNO "Notepad è in esecuzione. Chiuderlo?" IDNO skip
        ${nsProcess::CloseProcess} "notepad.exe" $R0
        ${If} $R0 == 0
            MessageBox MB_OK "Notepad chiuso con successo"
        ${Else}
            MessageBox MB_OK "Impossibile chiudere Notepad"
        ${EndIf}
        skip:
    ${Else}
        MessageBox MB_OK "Notepad non è in esecuzione"
    ${EndIf}
    ${nsProcess::Unload}
SectionEnd
```

## File include

Includi `nsProcess.nsh` per utilizzare le macro:

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

```powershell
python build_plugin.py
```

I DLL vengono copiati in `dist/{platform}/nsProcess.dll`.

### Opzioni build

```powershell
python build_plugin.py --configs x86-unicode       # Solo un'architettura (x86-ansi|x86-unicode|amd64-unicode|all)
python build_plugin.py --vs-version 2026           # Versione VS specifica (2022|2026|auto)
python build_plugin.py --clean                     # Pulizia dist/ prima della build
python build_plugin.py --install-dir "C:\NSIS\Plugins"  # Copia in directory NSIS aggiuntiva
python build_plugin.py --verbosity minimal         # Verbosità MSBuild (quiet|minimal|normal|detailed|diagnostic)
python build_plugin.py --final                     # Rebuild forzato + pulizia (build pre-release)
```

### Modifiche funzionali

Nessuna modifica funzionale rispetto all'originale. Le modifiche riguardano solo l'infrastruttura di build e il supporto x64.

---

*See [README.md](README.md) for the English version.*
