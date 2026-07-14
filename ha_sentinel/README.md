# HA Sentinel

HA Sentinel überwacht ausgewählte Home-Assistant-Entitäten mit einem lokalen OpenAI-kompatiblen LLM-Endpunkt, erstellt kompakte Zustandsanalysen und kann diese über Telegram senden.

## Konfiguration

Trage in den Add-on-Optionen deine eigene LM-Studio-Adresse ein, zum Beispiel:

```yaml
lm_studio_url: "http://lm-studio-host:1234/v1/chat/completions"
model: "qwen3-8b-mlx"
telegram_enabled: true
telegram_bot_token: "BOT-TOKEN"
telegram_chat_id: "DEINE-CHAT-ID"
```

Zugangsdaten werden ausschließlich in den lokalen Add-on-Optionen gespeichert und gehören nicht in dieses Repository.

## Wichtige Änderungen in 0.5.0

- Der aktuelle Klimamodus wird verbindlich aus `climate.state` übernommen.
- Frühere KI-Ausgaben werden nicht mehr in neue Analysen geladen.
- Die Klima-Zeile wird mit den aktuellen HA-Livedaten abgesichert.
- Telegram-Ausgaben werden von störender Markdown-Formatierung bereinigt.
- Der Prompt wurde verkleinert.
