import html, re, time
import requests
from sentinel_config import *
from sentinel_ai import cached_dashboard, llm

def tg(method,p=None,timeout=35):
 r=requests.post(f'https://api.telegram.org/bot{TGT}/{method}',json=p or {},timeout=timeout); r.raise_for_status(); return r.json()
def send(text,chat=None): tg('sendMessage',{'chat_id':str(chat or CHAT),'text':text,'parse_mode':'HTML','disable_web_page_preview':True,'disable_notification':bool(OPT.get('telegram_disable_notification'))})
def summary(e):
 d=state(e); a=d['attributes']; x=[f'{a.get("friendly_name",e)}: {d["state"]}']
 if 'current_temperature' in a:x.append(f'Ist {a["current_temperature"]} °C')
 if 'temperature' in a:x.append(f'Soll {a["temperature"]} °C')
 return ', '.join(x)
def command(t):
 n=t.lower().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')
 if n.strip() in ('status','/status','haus status'): return cached_dashboard()
 if 'stehlampe' in n:
  if ' aus' in n: service('switch','turn_off',LAMP); return '✅ '+html.escape(summary(LAMP))
  if ' an' in n: service('switch','turn_on',LAMP); return '✅ '+html.escape(summary(LAMP))
  return '💡 '+html.escape(summary(LAMP))
 m=re.search(r'\b(1[6-9]|2[0-9]|30)(?:[.,]5)?\b',n)
 if ('klima' in n or 'kuehl' in n) and m:
  service('switch','turn_on',CSW); service('climate','set_temperature',CLIMATE,{'temperature':float(m.group().replace(',','.'))}); return '✅ '+html.escape(summary(CLIMATE))
 if 'klima' in n or 'kuehl' in n:
  fans={'silent':'silent','leise':'silent','low':'low','niedrig':'low','medium':'medium','mittel':'medium','high':'high','hoch':'high','full':'full','voll':'full','luefter auto':'auto'}
  for k,v in fans.items():
   if k in n: service('switch','turn_on',CSW); service('climate','set_fan_mode',CLIMATE,{'fan_mode':v}); return '✅ '+html.escape(summary(CLIMATE))
  modes={'kuehl':'cool','cool':'cool','lueftermodus':'fan_only','fan_only':'fan_only','entfeucht':'dry','dry':'dry','automatik':'auto',' auto':'auto','heiz':'heat','heat':'heat'}
  for k,v in modes.items():
   if k in n: service('switch','turn_on',CSW); service('climate','set_hvac_mode',CLIMATE,{'hvac_mode':v}); return '✅ '+html.escape(summary(CLIMATE))
  if ' aus' in n: service('climate','set_hvac_mode',CLIMATE,{'hvac_mode':'off'}); service('switch','turn_off',CSW); return '✅ Klimaanlage ist aus.'
  if ' an' in n: service('switch','turn_on',CSW); return '✅ '+html.escape(summary(CSW))
  if 'status' in n:return '❄️ '+html.escape(summary(CLIMATE))
 if n.strip() in ('/start','/help','hilfe'): return '<b>HA Sentinel</b>\nStatus · Klima Status · Klima an/aus · Kühlmodus · Lüftermodus · Entfeuchten · Automatik · Heizen · Klima auf 22 Grad · Lüfter silent/low/medium/high/full/auto · Stehlampe an/aus'
 return html.escape(llm(snapshot(),'Beantworte knapp, ohne Aktionen auszuführen: '+t))
def poll():
 if not(TG and TGT and CHAT and OPT.get('telegram_control_enabled',True)):return
 off=int(OFFSET.read_text()) if OFFSET.exists() else 0
 try: send('🤖 <b>HA Sentinel 0.5.1</b> ist online.')
 except Exception as x: log(f'Telegram Startmeldung: {x}')
 while RUN:
  try:
   for u in tg('getUpdates',{'offset':off,'timeout':int(OPT.get('telegram_poll_timeout',20)),'allowed_updates':['message']},40).get('result',[]):
    off=int(u['update_id'])+1; OFFSET.write_text(str(off)); m=u.get('message') or {}; c=str((m.get('chat') or {}).get('id','')); t=str(m.get('text','')).strip()
    if t and c==CHAT:
     try: send(command(t),c)
     except Exception as x: send(f'❌ Befehl fehlgeschlagen: {html.escape(str(x))}',c)
  except Exception as x: log(f'Telegram: {x}'); time.sleep(5)