# Security Policy

## Versioni Supportate

Solo l'ultima versione minor riceve fix di security.

| Versione | Supporto |
|----------|----------|
| Latest minor (es. 1.6.0) | ✅ |
| Versioni precedenti | ❌ |

## Reporting di una Vulnerabilità

**Non aprire issue pubbliche per vulnerabilità di security.**

Per segnalare una vulnerabilità:

1. **Preferito**: usa la funzione [Security Advisory privato](https://gitea.emulab.it/Simone/nsis-plugin-nsprocess/security/advisories/new) di Gitea
2. **Alternativa**: invia email a `security@example.com` (sostituire con email reale prima del primo release)

Includi:
- Descrizione della vulnerabilità
- Passi per riprodurla
- Versione/i affette
- Possibile mitigazione (se nota)

## Tempo di Risposta

- Acknowledgment iniziale: entro 7 giorni
- Valutazione: entro 14 giorni
- Patch (se confermata): tempistiche dipendono dalla severità

## Hardening

Questo plugin gira con i permessi del processo NSIS chiamante (tipicamente
l'utente che esegue l'installer). Non richiede privilegi elevati per la
compilazione né per l'esecuzione, salvo dove esplicitamente documentato.

DLL distribuite tramite Releases sono compilate da CI GitHub Actions con
toolchain pinnata. Verificare hash SHA256 pubblicati nelle release.
