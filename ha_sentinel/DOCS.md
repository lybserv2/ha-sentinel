# HA Sentinel – Dokumentation

## Einrichtung

1. Installiere und starte LM Studio auf einem im Netzwerk erreichbaren Rechner.
2. Aktiviere dort den OpenAI-kompatiblen API-Server.
3. Trage dessen Adresse in `lm_studio_url` ein.
4. Hinterlege optional Telegram-Bot-Token und Chat-ID in den lokalen Add-on-Optionen.
5. Starte HA Sentinel neu.

Beispiel:

```yaml
lm_studio_url: "http://lm-studio-host:1234/v1/chat/completions"
model: "qwen3-8b-mlx"
interval_seconds: 300
telegram_enabled: false
```

Die Beispieladresse muss durch deine eigene interne Adresse ersetzt werden.
