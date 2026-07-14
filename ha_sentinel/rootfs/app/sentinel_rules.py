import json
from sentinel_config import STATE, log

RULES_FILE = STATE / 'ha_sentinel_rules.json'
MAX_RULES = 30
MAX_RULE_LENGTH = 240


def load_rules():
    if not RULES_FILE.exists():
        return []
    try:
        data = json.loads(RULES_FILE.read_text(encoding='utf-8'))
        if not isinstance(data, list):
            return []
        return [str(item).strip() for item in data if str(item).strip()][:MAX_RULES]
    except Exception as exc:
        log(f'Regeldatei konnte nicht gelesen werden: {exc}')
        return []


def save_rules(rules):
    cleaned = []
    for rule in rules:
        text = ' '.join(str(rule).split()).strip()[:MAX_RULE_LENGTH]
        if text and text not in cleaned:
            cleaned.append(text)
    cleaned = cleaned[:MAX_RULES]
    RULES_FILE.write_text(
