# Changelog

## 0.5.2

- Persistente Feedback-Regeln über Telegram ergänzt.
- Regeln werden lokal in `/config/ha_sentinel_rules.json` gespeichert.
- Neue Befehle: `/merke`, `/regeln`, `/vergiss` und `/regeln_loeschen`.
- Nutzerregeln werden kompakt in den Analyse-Prompt aufgenommen.
- Nach Regeländerungen wird der Analyse-Cache verworfen.
- Nur die konfigurierte Telegram-Chat-ID darf Regeln verwalten.

## 0.5.1

- Serielle LLM-Ausführung mit globalem Lock.
- Kompakte Snapshots, Snapshot-Hash und begrenzte History.
- Telegram-HTML-Dashboard und Schutz vor Doppelmeldungen.
- Token-Nutzung wird protokolliert.

## 0.5.0

- Aktueller Climate-State ist für Analysen verbindlich.
- Alte KI-Antworten werden nicht mehr erneut in den Prompt geladen.
- Telegram-Ausgabe wird von störender Markdown-Formatierung bereinigt.
- Snapshot und Prompt wurden verkleinert.
- Architekturabhängige Basis-Images sind in `build.yaml` definiert.