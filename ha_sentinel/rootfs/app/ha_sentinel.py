#!/usr/bin/env python3
import json, os, re, signal, threading, time
from datetime import datetime
from pathlib import Path
import requests

OPT=json.loads(Path('/data/options.json').read_text())
TOKEN=os.getenv('SUPERVISOR_TOKEN',''); HA='http://supervisor/core'; RUN=True
LM=OPT['lm_studio_url']; MODEL=OPT['model']; INTERVAL=int(OPT['interval_seconds']); TIMEOUT=int(OPT['request_timeout'])
TG=bool(OPT.get('telegram_enabled')); TGT=OPT.get('telegram_bot_token','').strip(); CHAT=str(OPT.get('telegram_chat_id','')).strip()
CLIMATE=OPT.get('climate_entity','climate.152832117768500_climate'); CSW=OPT.get('climate_switch_entity','switch.klimaanlage'); LAMP=OPT.get('floor_lamp_entity','switch.stehlampe')
STATE=Path('/config'); STATE.mkdir(exist_ok=True); OFFSET=STATE/'telegram_offset.txt'; HIST=STATE/'ha_sentinel_history.jsonl'
GROUPS={
 'Klima':[CLIMATE,CSW,'sensor.klimaanlage_energy_power','sensor.temperatur_temperature','sensor.temperatur_humidity'],
 'Netzwerk':['binary_sensor.8_8_8_8','sensor.ping_google_latency','sensor.fritz_box_7590_cpu_temperatur'],
 'Home Assistant':['sensor.localhost_config_datentragernutzung','sensor.backup_backup_manager_state','binary_sensor.rpi_power_status'],
 'Verbraucher':[LAMP,'sensor.waschmaschine_energy_power','sensor.spuelmaschine_energy_power','sensor.computer_energy_power','sensor.tv_energy_power'],
 'Saugroboter':['sensor.polnische_putzkraft_status','sensor.polnische_putzkraft_error','sensor.polnische_putzkraft_battery_level'],
 'Updates':['update.home_assistant_core_update','update.home_assistant_mcp_server_update']}

def log(x): print(f'[{datetime.now().astimezone().isoformat(timespec="seconds")}] {x}',flush=True)
def stop(*_):
 global RUN; RUN=False
signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
def headers(): return {'Authorization':f'Bearer {TOKEN}','Content-Type':'application/json'}
def state(e):
 r=requests.get(f'{HA}/api/states/{e}',headers=headers(),timeout=15); r.raise_for_status(); d=r.json(); a=d.get('attributes',{})
 keep={k:a[k] for k in ('friendly_name','unit_of_measurement','current_temperature','temperature','fan_mode') if k in a}
 return {'state':d.get('state'),'attributes':keep}
def service(domain,name,e,data=None):
 p={'entity_id':e}; p.update(data or {}); r=requests.post(f'{HA}/api/services/{domain}/{name}',headers=headers(),json=p,timeout=20); r.raise_for_status()
def snapshot():
 g={}; err={}; n=0
 for name,ents in GROUPS.items():
  g[name]={}
  for e in ents:
   try:g[name][e]=state(e);n+=1
   except Exception as x:err[e]=str(x)
 return {'captured_at':datetime.now().astimezone().isoformat(),'groups':g,'errors':err,'entity_count':n}
def get(s,e):
 for g in s['groups'].values():
  if e in g:return g[e]
 return {}
def llm(s,q='Erstelle eine kompakte Zustandsanalyse.'):
 mode=str(get(s,CLIMATE).get('state','unbekannt'))
 rules=('/no_think\nDu bist ein technischer Smart-Home-Analyst. Nutze nur den aktuellen Snapshot. '
        f'Der verbindliche aktuelle Klimamodus ist {mode}; maßgeblich ist climate.state. '
        'Erfinde keine Zustände. Im Modus cool sind 1200-1800 W plausibel, über 2500 W auffällig. '
        'Im Modus fan_only sind 30-100 W plausibel. FritzBox 80-89 °C erhöht, ab 90 °C kritisch. '
        'Datenträger unter 80 % unkritisch. Keine Markdown-Sternchen. Antworte knapp auf Deutsch.')
 p={'model':MODEL,'messages':[{'role':'system','content':rules},{'role':'user','content':json.dumps({'question':q,'snapshot':s},ensure_ascii=False,separators=(',',':'))}], 'temperature':0.1,'max_tokens':500,'stream':False}
 r=requests.post(LM,json=p,timeout=TIMEOUT);r.raise_for_status();m=r.json()['choices'][0]['message'];out=(m.get('content') or m.get('reasoning_content') or '').strip()
 return enforce(out,s)
def fmt(v):
 try:
  f=float(v);return str(int(f)) if f.is_integer() else str(round(f,1)).replace('.',',')
 except:return str(v)
def climate_line(s):
 c=get(s,CLIMATE);a=c.get('attributes',{});mode=c.get('state','unbekannt');p=get(s,'sensor.klimaanlage_energy_power').get('state');room=get(s,'sensor.temperatur_temperature').get('state') or a.get('current_temperature')
 names={'cool':'Kühlmodus','fan_only':'Lüftermodus','dry':'Entfeuchten','auto':'Automatik','heat':'Heizmodus','off':'aus'};parts=[f'Modus: {names.get(mode,mode)} ({mode})']
 if p not in (None,'unknown','unavailable'):parts.append(f'Leistung: {fmt(p)} W')
 if a.get('temperature') is not None:parts.append(f'Soll: {fmt(a["temperature"])} °C')
 if room not in (None,'unknown','unavailable'):parts.append(f'Raum: {fmt(room)} °C')
 return '- Klimaanlage: '+', '.join(parts)+'.'
def enforce(text,s):
 out=[];done=False
 for line in text.splitlines():
  n=re.sub(r'[*_`#]','',line).lower()
  if 'klimaanlage' in n or n.strip().startswith('klima:'):
   if not done:out.append(climate_line(s));done=True
  else:out.append(line)
 if not done:out.insert(0,climate_line(s))
 return re.sub(r'[*_`]','', '\n'.join(out)).strip()
def tg(method,p=None,timeout=35):
 r=requests.post(f'https://api.telegram.org/bot{TGT}/{method}',json=p or {},timeout=timeout);r.raise_for_status();return r.json()
def send(text,chat=None):
 tg('sendMessage',{'chat_id':str(chat or CHAT),'text':text,'disable_notification':bool(OPT.get('telegram_disable_notification'))})
def publish(text):
 title=f'HA Sentinel - {datetime.now().astimezone():%H:%M}'
 requests.post(f'{HA}/api/services/persistent_notification/create',headers=headers(),json={'notification_id':'ha_sentinel_letzte_analyse','title':title,'message':text},timeout=20).raise_for_status()
 ns=str(OPT.get('notify_service','')).strip()
 if ns and '.' in ns:
  d,n=ns.split('.',1);requests.post(f'{HA}/api/services/{d}/{n}',headers=headers(),json={'title':title,'message':text},timeout=20).raise_for_status()
 if TG and TGT and CHAT:send(f'🏠 {title}\n\n{text}')
 with HIST.open('a') as f:f.write(json.dumps({'timestamp':datetime.now().astimezone().isoformat(),'result':text},ensure_ascii=False)+'\n')
def summary(e):
 d=state(e);a=d['attributes'];x=[f'{a.get("friendly_name",e)}: {d["state"]}']
 if 'current_temperature' in a:x.append(f'Ist {a["current_temperature"]} °C')
 if 'temperature' in a:x.append(f'Soll {a["temperature"]} °C')
 return ', '.join(x)
def cmd(t):
 n=t.lower().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss')
 if 'stehlampe' in n:
  if ' aus' in n:service('switch','turn_off',LAMP);return '✅ '+summary(LAMP)
  if ' an' in n:service('switch','turn_on',LAMP);return '✅ '+summary(LAMP)
  return '💡 '+summary(LAMP)
 m=re.search(r'\b(1[6-9]|2[0-9]|30)(?:[.,]5)?\b',n)
 if ('klima' in n or 'kuehl' in n) and m:
  service('switch','turn_on',CSW);service('climate','set_temperature',CLIMATE,{'temperature':float(m.group().replace(',','.'))});return '✅ '+summary(CLIMATE)
 if 'klima' in n or 'kuehl' in n:
  modes={'kuehl':'cool','cool':'cool','lueftermodus':'fan_only','fan_only':'fan_only','entfeucht':'dry','automatik':'auto'}
  for k,v in modes.items():
   if k in n:service('switch','turn_on',CSW);service('climate','set_hvac_mode',CLIMATE,{'hvac_mode':v});return '✅ '+summary(CLIMATE)
  if ' aus' in n:service('climate','set_hvac_mode',CLIMATE,{'hvac_mode':'off'});service('switch','turn_off',CSW);return '✅ Klimaanlage ist aus.'
  if ' an' in n:service('switch','turn_on',CSW);return '✅ '+summary(CSW)
  if 'status' in n:return '❄️ '+summary(CLIMATE)
 if n.strip() in ('/start','/help','hilfe'):return '🤖 Befehle: Status, Klima Status, Klima an/aus, Kühlmodus, Lüftermodus, Klima auf 19 Grad, Stehlampe an/aus.'
 return llm(snapshot(), 'Beantworte diese Frage ohne Aktionen auszuführen: '+t)
def poll():
 if not(TG and TGT and CHAT and OPT.get('telegram_control_enabled',True)):return
 off=int(OFFSET.read_text()) if OFFSET.exists() else 0
 try:send('🤖 HA Sentinel 0.5.0 ist online.')
 except Exception as x:log(x)
 while RUN:
  try:
   for u in tg('getUpdates',{'offset':off,'timeout':int(OPT.get('telegram_poll_timeout',20)),'allowed_updates':['message']},40).get('result',[]):
    off=int(u['update_id'])+1;OFFSET.write_text(str(off));m=u.get('message') or {};c=str((m.get('chat') or {}).get('id',''));t=str(m.get('text','')).strip()
    if t and c==CHAT:
     try:send(cmd(t),c)
     except Exception as x:send(f'❌ Befehl fehlgeschlagen: {x}',c)
  except Exception as x:log(f'Telegram: {x}');time.sleep(5)
def monitor():
 while RUN:
  start=time.monotonic()
  try:
   s=snapshot();log(f'Snapshot: {s["entity_count"]} Werte, {len(s["errors"])} Fehler');r=llm(s);log('KI: '+r.replace('\n',' '))
   if OPT.get('notify_every_run',True):publish(r)
  except Exception as x:log(f'Analysefehler: {x}')
  for _ in range(max(1,INTERVAL-int(time.monotonic()-start))):
   if not RUN:break
   time.sleep(1)
def main():
 if not TOKEN:raise RuntimeError('SUPERVISOR_TOKEN fehlt')
 log('HA Sentinel 0.5.0 startet');threading.Thread(target=poll,daemon=True).start();monitor()
if __name__=='__main__':main()
