import json
from sentinel_config import STATE, log

RULES_FILE = STATE / 'ha_sentinel_rules.json'
MAX_RULES = 30
MAX_RULE_LENGTH = 240


def load_rules():
    try:
        if not RULES_FILE.exists():
            return []
        data = json.loads(RULES_FILE.read_text(encoding='utf-8'))
        if not isinstance(data, list):
            return []
        return [str(x).strip() for x in data if str(x).strip()][:MAX_RULES]
    except Exception as exc:
        log(f'Regeldatei konnte nicht gelesen werden: {exc}')
        return []


def save_rules(rules):
    cleaned = []
    for item in rules:
        text = ' '.join(str(item).split()).strip()[:MAX_RULE_LENGTH]
        if text and text not in cleaned:
            cleaned.append(text)
    RULES_FILE.write_text(json.dumps(cleaned[:MAX_RULES], ensure_ascii=False, indent=2), encoding='utf-8')
    return cleaned[:MAX_RULES]


def add_rule(rule):
    text = ' '.join(str(rule).split()).strip()[:MAX_RULE_LENGTH]
    if not text:
        raise ValueError('Regel darf nicht leer sein.')
    rules = load_rules()
    added = text not in rules
    if added:
        rules.append(text)
        save_rules(rules)
    return rules, added


def delete_rule(selector):
    rules = load_rules()
    try:
        index = int(str(selector).strip()) - 1
    except ValueError as exc:
        raise ValueError('Bitte die Regelnummer angeben.') from exc
    if index < 0 or index >= len(rules):
        raise ValueError('Regelnummer nicht gefunden.')
    removed = rules.pop(index)
    save_rules(rules)
    return removed


def clear_rules():
    count = len(load_rules())
    save_rules([])
    return count


def prompt_rules():
    rules = load_rules()
    if not rules:
        return ''
    return 'Persoenliche Regeln des Nutzers, verbindlich beachten:\n' + '\n'.join(f'- {rule}' for rule in rules)
