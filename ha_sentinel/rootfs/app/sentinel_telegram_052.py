import html, re, time
import sentinel_telegram as base
from sentinel_config import *
from sentinel_ai import invalidate_cache
from sentinel_rules import add_rule, clear_rules, delete_rule, load_rules

def rules_text():
 rules=load_rules()
 if not rules:return '<b>Gespeicherte Regeln</b>\n• Keine Regeln vorhanden'
 return '<b>Gespeicherte Regeln</b>\n'+'\n'.join(f'{i+1}. {html.escape(rule)}' for i,rule in enumerate(rules))

def command(text):
 raw=text.strip(); norm=raw.lower().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')
 if norm.startswith('/merke ') or norm.startswith('merke:') or norm.startswith('merke '):
  rule=re.sub(r'^(?:/merke\s+|merke\s*:\s*|merke\s+)','',raw,flags=re.I).strip()
  _,added=add_rule(rule); invalidate_cache()
  return ('✅ <b>Regel gespeichert</b>\n• ' if added else 'ℹ️ Regel war bereits gespeichert.\n• ')+html.escape(rule)
 if norm in ('/regeln','regeln','zeige regeln','gespeicherte regeln'):return rules_text()
 if norm.startswith('/vergiss ') or norm.startswith('vergiss:') or norm.startswith('vergiss '):
  selector=re.sub(r'^(?:/vergiss\s+|vergiss\s*:\s*|vergiss\s+)','',raw,flags=re.I).strip()
  removed=delete_rule(selector); invalidate_cache(); return '🗑️ <b>Regel gelöscht</b>\n• '+html.escape(removed)
 if norm in ('/regeln_loeschen','regeln loeschen','alle regeln loeschen'):
  count=clear_rules(); invalidate_cache(); return f'🗑️ {count} Regel(n) gelöscht.'
 if norm in ('/start','/help','hilfe'):
  return base.command(raw)+'\n\n<b>Feedback-Regeln</b>\n/merke FritzBox bis 90 °C ignorieren\n/regeln\n/vergiss 1\n/regeln_loeschen'
 return base.command(raw)

def poll():
 if not(TG and TGT and CHAT and OPT.get('telegram_control_enabled',True)):return
 off=int(OFFSET.read_text()) if OFFSET.exists() else 0
 try:base.send('🤖 <b>HA Sentinel 0.5.2</b> ist online.')
 except Exception as exc:log(f'Telegram Startmeldung: {exc}')
 while RUN:
  try:
   for update in base.tg('getUpdates',{'offset':off,'timeout':int(OPT.get('telegram_poll_timeout',20)),'allowed_updates':['message']},40).get('result',[]):
    off=int(update['update_id'])+1; OFFSET.write_text(str(off)); msg=update.get('message') or {}; chat=str((msg.get('chat') or {}).get('id','')); text=str(msg.get('text','')).strip()
    if text and chat==CHAT:
     try:base.send(command(text),chat)
     except Exception as exc:base.send(f'❌ Befehl fehlgeschlagen: {html.escape(str(exc))}',chat)
  except Exception as exc:log(f'Telegram: {exc}'); time.sleep(5)