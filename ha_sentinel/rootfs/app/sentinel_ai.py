import html, json, re, time
from collections import deque
from datetime import datetime
import requests
from sentinel_config import *

def clean(t):
 t=re.sub(r'<think>.*?</think>','',t or '',flags=re.I|re.S); t=re.sub(r'[*_`#]+','',t); t=re.sub(r'^\s*[-•]+\s*','',t,flags=re.M); return ' '.join(t.split()).strip()
def llm(s,q='Nenne ausschließlich wichtige Auffälligkeiten. Antworte mit maximal 3 kurzen Sätzen.'):
 mode=str(get(s,CLIMATE).get('state','unbekannt'))
 rules=('/no_think\nDu bist ein technischer Smart-Home-Analyst. Nutze nur den kompakten aktuellen Snapshot. '
        f'Der verbindliche Klimamodus ist {mode}. Erfinde keine Werte. Im Modus cool sind 1200-1800 W plausibel, über 2500 W auffällig. '
        'Im Modus fan_only sind 30-100 W plausibel. FRITZ!Box 80-89 °C erhöht, ab 90 °C kritisch. Datenträger unter 80 % ist unkritisch. '
        'Gib nur echte Hinweise aus; wenn alles unauffällig ist, antworte exakt: Keine Auffälligkeiten.')
 p={'model':MODEL,'messages':[{'role':'system','content':rules},{'role':'user','content':json.dumps({'frage':q,'snapshot':s},ensure_ascii=False,separators=(',',':'))}], 'temperature':0.1,'max_tokens':220,'stream':False}
 with LLM_LOCK:
  r=requests.post(LM,json=p,timeout=TIMEOUT); r.raise_for_status(); body=r.json()
 u=body.get('usage') or {}; log(f'LLM Tokens: prompt={u.get("prompt_tokens","?")} completion={u.get("completion_tokens","?")} total={u.get("total_tokens","?")}')
 m=body['choices'][0]['message']; return clean(m.get('content') or m.get('reasoning_content') or '')
def bullet(label,value): return f'• {html.escape(label)}: {html.escape(str(value))}'
def section(title,lines): return f'<b>{html.escape(title)}</b>\n'+'\n'.join(lines or ['• Keine Daten verfügbar'])
def dashboard(s,analysis):
 now=datetime.now().astimezone(); c=get(s,CLIMATE); a=c.get('attributes',{}); mode=c.get('state','unbekannt'); names={'cool':'Kühlmodus','fan_only':'Lüftermodus','dry':'Entfeuchten','auto':'Automatik','heat':'Heizmodus','off':'Aus'}
 power=get(s,'sensor.klimaanlage_energy_power').get('state'); room=get(s,'sensor.temperatur_temperature').get('state') or a.get('current_temperature'); humidity=get(s,'sensor.temperatur_humidity').get('state')
 first=names.get(mode,mode)+(f', {num(power)} W' if valid(power) else ''); climate=[f'• {html.escape(first)}']
 if valid(a.get('temperature')): climate.append(bullet('Soll',f'{num(a["temperature"])} °C'))
 if valid(room): climate.append(bullet('Raum',f'{num(room)} °C'))
 if valid(humidity): climate.append(bullet('Luftfeuchtigkeit',f'{num(humidity)} %'))
 consumers=[]
 for e,f in [('sensor.waschmaschine_energy_power','Waschmaschine'),('sensor.spuelmaschine_energy_power','Spülmaschine'),('sensor.computer_energy_power','Computer'),('sensor.tv_energy_power','TV')]:
  v=get(s,e).get('state')
  if valid(v): consumers.append(bullet(name(s,e,f),f'{num(v)} W'))
 system=[]; vacuum=get(s,'sensor.polnische_putzkraft_status').get('state'); battery=get(s,'sensor.polnische_putzkraft_battery_level').get('state')
 if valid(vacuum): system.append(bullet('Saugroboter',str(vacuum)+(f', Akku {num(battery)} %' if valid(battery) else '')))
 disk=get(s,'sensor.localhost_config_datentragernutzung').get('state')
 if valid(disk): system.append(bullet('Home Assistant Speicher',f'{num(disk)} %'))
 updates=[name(s,e,e) for e in GROUPS['Updates'] if get(s,e).get('state')=='on']; system.append(bullet('Updates',', '.join(updates) if updates else 'keine verfügbar'))
 atext=clean(analysis); warning=bool(atext and atext.lower()!='keine auffälligkeiten.'); hints=[f'• {html.escape(atext)}'] if warning else ['• Keine Auffälligkeiten']; status='⚠️ Auffälligkeit erkannt' if warning else '✅ Status: OK'
 return f'🏠 <b>HA Sentinel</b> · {now:%H:%M}\n\n{status}\n\n{section("🌡️ Klima & Raum",climate)}\n\n{section("⚡ Stromverbrauch",consumers)}\n\n{section("🖥️ System & Geräte",system)}\n\n{section("💡 Hinweise",hints)}'
def analyze(force=False):
 s=snapshot(); h=digest(s)
 with CACHE_LOCK:
  if not force and h==LAST['snapshot_hash'] and LAST['dashboard']:
   log(f'Snapshot unverändert: {h[:12]} - kein neuer KI-Call'); return s,h,LAST['analysis'],LAST['dashboard'],False
 a=llm(s); d=dashboard(s,a)
 with CACHE_LOCK: LAST.update(snapshot=s,snapshot_hash=h,analysis=a,dashboard=d,analyzed_at=time.time())
 return s,h,a,d,True
def cached_dashboard():
 with CACHE_LOCK:
  if LAST['dashboard'] and time.time()-LAST['analyzed_at']<=STATUS_CACHE_SECONDS:return LAST['dashboard']
 return analyze(False)[3]
def write_history(h,a):
 entries=deque(maxlen=max(1,HISTORY_LIMIT))
 if HIST.exists():
  for line in HIST.read_text(errors='ignore').splitlines()[-HISTORY_LIMIT:]:
   try: entries.append(json.loads(line))
   except: pass
 entries.append({'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),'snapshot_hash':h,'summary':clean(a)[:500]}); HIST.write_text('\n'.join(json.dumps(x,ensure_ascii=False,separators=(',',':')) for x in entries)+'\n')