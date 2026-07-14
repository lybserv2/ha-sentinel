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
        return [str(x).strip() for x in data if str(x).strip()][:MAX_RULES]
    except Exception as exc:
        log