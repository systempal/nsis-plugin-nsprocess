# Contribuire a nsProcess

Grazie per il tuo interesse a contribuire!

> Repository primario: [https://gitea.emulab.it/Simone/nsis-plugin-nsprocess](https://gitea.emulab.it/Simone/nsis-plugin-nsprocess)  
> Mirror GitHub: [https://github.com/systempal/nsis-plugin-nsprocess](https://github.com/systempal/nsis-plugin-nsprocess) (read-only — apri PR su Gitea)

## Prerequisiti

| Strumento | Versione | Note |
|-----------|----------|------|
| Visual Studio | 2022 / 2026 | Workload: Desktop development with C++ (toolset v143/v145) |
| Python | 3.7+ | Per `build_plugin.py` |
| Git | 2.30+ | Con supporto submoduli se applicabile |

## Quick Start

```powershell
git clone https://gitea.emulab.it/Simone/nsis-plugin-nsprocess.git
cd nsis-plugin-nsprocess
python build_plugin.py
```

Output in `dist/{x86-ansi,x86-unicode,amd64-unicode}/`.

## Workflow Sviluppo

### 1. Branch

```powershell
git checkout -b feat/nome-feature   # nuova feature
git checkout -b fix/descrizione-bug  # bugfix
git checkout -b docs/aggiornamento   # solo doc
git checkout -b chore/manutenzione   # build, dipendenze
```

### 2. Commit

Segui [Conventional Commits](https://www.conventionalcommits.org/it/v1.0.0/):

```
feat: aggiunge supporto per formato XYZ
fix: corregge crash su Windows 11 ARM
docs: aggiorna esempio di utilizzo
chore: aggiorna toolset MSVC
refactor: estrae logica parsing in funzione separata
test: aggiunge test per edge case
build: aggiorna script di build
ci: aggiorna workflow GitHub Actions
```

Breaking changes:

```
feat!: rinomina API Foo() in Bar()

BREAKING CHANGE: Foo() rinominata in Bar(); aggiornare tutti i chiamanti.
```

### 3. Pull Request

PR aperte verso il branch `main` su Gitea. Verifica:

- [ ] Build completa senza warning per tutte le architetture: `python build_plugin.py`
- [ ] Esempi aggiornati se cambia l'API
- [ ] `CHANGELOG.md` aggiornato (sezione `[Unreleased]`)
- [ ] Documentazione aggiornata (README, docs/API.md se esiste)
- [ ] Conventional Commits rispettato
- [ ] Nessun file in `dist/` o `__pycache__/` committato

## Build Script

```
python build_plugin.py [opzioni]
```

| Opzione | Default | Descrizione |
|---------|---------|-------------|
| `--config` | `all` | Architettura: `x86-ansi`, `x86-unicode`, `x64-unicode`, `all` |
| `--toolset` | `auto` | Visual Studio: `2022`, `2026`, `auto` (rileva il più recente) |
| `--jobs` | numero CPU | Thread paralleli per la build |
| `--clean` | false | Pulisce `dist/` prima di compilare |
| `--install-dir` | none | Copia DLL anche in `<dir>/{arch}/` (es. NSIS plugin folder) |
| `--verbose` | false | Output dettagliato (mostra comandi MSBuild) |

Exit codes:
- `0` — Successo
- `1` — Errore di build
- `2` — Prerequisiti mancanti
- `3` — Argomenti invalidi

## Release Workflow

Le release sono automatiche via tag Git:

```powershell
# 1. Aggiorna VERSION e CHANGELOG.md
echo "1.7.0" > VERSION
# (modifica CHANGELOG.md spostando entry da [Unreleased] a [1.7.0])

# 2. Commit
git add VERSION CHANGELOG.md
git commit -m "chore(release): v1.7.0"

# 3. Tag annotato
git tag -a v1.7.0 -m "Release v1.7.0"

# 4. Push
git push origin main
git push origin v1.7.0
```

Il workflow `.github/workflows/release.yml` compilerà tutte le architetture
e creerà la release su Gitea con gli artifact ZIP allegati. Il mirror GitHub
riceverà automaticamente il tag.

## Code Style

- C/C++: stile coerente con il file modificato
- Python: PEP 8 (4 spazi indent, line length flessibile)
- Header file: `#include` ordinati: stdlib → Win32 → progetto
- Encoding: UTF-8 senza BOM (eccetto `.rc` che richiede UTF-16 LE)
- Line endings: LF in repo (`.gitattributes` normalizza)

## Reporting Bug

Apri una [issue](https://gitea.emulab.it/Simone/nsis-plugin-nsprocess/issues/new) usando il template "Bug Report".
Includi:
- Versione plugin e architettura DLL usata
- Versione NSIS
- Sistema operativo
- Script `.nsi` minimale che riproduce il problema
- Output / errore esatto

## Domande

Per domande generali, apri una [issue](https://gitea.emulab.it/Simone/nsis-plugin-nsprocess/issues) con label `question`.
