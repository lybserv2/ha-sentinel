import html,json,re,time
from collections import deque
from datetime import datetime
import requests
from sentinel_config import *
from sentinel_rules import prompt_rules

def clean(t):
 t=re.sub(r'<think>.*?</think>','',t or '',flags=re.I|re.S)
 t=re.sub(r'[*_`#]+','',t)
 return ' '.join(t.split()).strip()

def llm(s,q='Nenne nur echte Auffaelligkeiten.'):
 mode=str(get(s,CLIMATE).get('state','unbekannt'))
 rules=('/no_think\nAnalysiere nur echte Auffaelligkeiten im Snapshot. '
  f'Klimamodus ist {mode}. Erfinde nichts. Cool: 1200-1800 W normal, ueber 2500 W auffaellig. '
  'Fan_only: 30-100 W normal. Speicher unter 80 Prozent normal. '
  'Persoenliche Regeln sind verbindlich. Werte, die laut Regel normal oder zu ignorieren sind, NICHT erwaehnen. '
  'Keine Erklaerungen zu normalen Werten. Wenn nichts auffaellig ist, antworte exakt: Keine Auffaelligkeiten.\n'+prompt_rules())
 payload={'model':MODEL,'messages':[{'role':'system','content':rules},{'role':'user','content':json.dumps({'frage':q,'snapshot':s},ensure_ascii=False,separators=(',',':'))}],'temperature':0.1,'max_tokens':160,'stream':False}
 with LLM_LOCK:
  r=requests.post(LM,json=payload,timeout=TIMEOUT);r.raise_for_status();body=r.json()
 u=body.get('usage') or {};log(f'LLM Tokens: prompt={u.get("prompt_tokens","?")} completion={u.get("completion_tokens","?")} total={u.get("total_tokens","?")}')
 m=body['choices'][0]['message'];return clean(m.get('content') or m.get('reasoning_content') or '')

def bullet(label,value):return f'• {html.escape(label)}: {html.escape(str(value))}'
def section(title,lines):return f'<b>{html.escape(title)}</b>\n'+'\n'.join(lines or ['• Keine Daten verfügbar'])
def is_clear(text):
 n=clean(text).lower().rstrip('.! ')
 return not n or n=='keine auffälligkeiten' or n=='keine auffaelligkeiten' or n.endswith('keine auffälligkeiten') or n.endswith('keine auffaelligkeiten')

def dashboard(s,analysis):
 now=datetime.now().astimezone();c=get(s,CLIMATE);a=c.get('attributes',{});mode=c.get('state','unbekannt')
 names={'cool':'Kühlmodus','fan_only':'Lüftermodus','dry':'Entfeuchten','auto':'Automatik','heat':'Heizmodus','off':'Aus'}
 power=get(s,'sensor.klimaanlage_energy_power').get('state');room=get(s,'sensor.temperatur_temperature').get('state') or a.get('current_temperature');hum=get(s,'sensor.temperatur_humidity').get('state')
 first=names.get(mode,mode)+(f', {num(power)} W' if valid(power) else '');climate=[f'• {html.escape(first)}']
 if valid(a.get('temperature')):climate.append(bullet('Soll',f'{num(a["temperature"])} °C'))
 if valid(room):climate.append(bullet('Raum',f'{num(room)} °C'))
 if valid(hum):climate.append(bullet('Luftfeuchtigkeit',f'{num(hum)} %'))
 consumers=[]
 for e,label in [('sensor.waschmaschine_energy_power','Waschmaschine'),('sensor.spuelmaschine_energy_power','Spülmaschine'),('sensor.computer_energy_power','Computer'),('sensor.tv_energy_power','TV')]:
  v=get(s,e).get('state')
  if valid(v):consumers.append(bullet(label,f'{num(v)} W'))
 system=[];vac=get(s,'sensor.polnische_putzkraft_status').get('state');bat=get(s,'sensor.polnische_putzkraft_battery_level').get('state')
 if valid(vac):system.append(bullet('Saugroboter',str(vac)+(f', Akku {num(bat)} %' if valid(bat) else '')))
 disk=get(s,'sensor.localhost_config_datentragernutzung').get('state')
 if valid(disk):system.append(bullet('Home Assistant Speicher',f'{num(disk)} %'))
 updates=[name(s,e,e) for e in GROUPS['Updates'] if get(s,e).get('state')=='on'];system.append(bullet('Updates',', '.join(updates) if updates else 'keine verfügbar'))
 clear=is_clear(analysis);hints=['• Keine Auffälligkeiten'] if clear else [f'• {html.escape(clean(analysis))}'];status='✅ Status: OK' if clear else '⚠️ Auffälligkeit erkannt'
 return f'🏠 <b>HA Sentinel</b> · {now:%H:%M}\n\n{status}\n\n{section("🌡️ Klima & Raum",climate)}\n\n{section("⚡ Stromverbrauch",consumers)}\n\n{section("🖥️ System & Geräte",system)}\n\n{section("💡 Hinweise",hints)}'

def analyze(force=False):
 s=snapshot();h=digest(s)
 with CACHE_LOCK:
  if not force and h==LAST['snapshot_hash'] and LAST['dashboard']:return s,h,LAST['analysis'],LAST['dashboard'],False
 a=llm(s);d=dashboard(s,a)
 with CACHE_LOCK:LAST.update(snapshot=s,snapshot_hash=h,analysis=a,dashboard=d,analyzed_at=time.time())
 return s,h,a,d,True

def cached_dashboard():
 with CACHE_LOCK:
  if LAST['dashboard'] and time.time()-LAST['analyzed_at']<=STATUS_CACHE_SECONDS:return LAST['dashboard']
 return analyze(False)[3]
def invalidate_cache():
 with CACHE_LOCK:LAST.update(snapshot_hash=None,analysis=None,dashboard=None,analyzed_at=0.0)
def write_history(h,a):
 rows=deque(maxlen=max(1,HISTORY_LIMIT))
 if HIST.exists():
  for line in HIST.read_text(errors='ignore').splitlines()[-HISTORY_LIMIT:]:
   try:rows.append(json.loads(line))
   except:pass
 rows.append({'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),'snapshot_hash':h,'summary':clean(a)[:500]})
 HIST.write_text('\n'.join(json.dumps(x,ensure_ascii=False,separators=(',',':')) for x in rows)+'\n')