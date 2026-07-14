import hashlib, json, os, signal, threading
from datetime import datetime
from pathlib import Path
import requests

OPT=json.loads(Path('/data/options.json').read_text())
TOKEN=os.getenv('SUPERVISOR_TOKEN',''); HA='http://supervisor/core'
LM=OPT['lm_studio_url']; MODEL=OPT['model']; INTERVAL=int(OPT['interval_seconds']); TIMEOUT=int(OPT['request_timeout'])
TG=bool(OPT.get('telegram_enabled')); TGT=OPT.get('telegram_bot_token','').strip(); CHAT=str(OPT.get('telegram_chat_id','')).strip()
CLIMATE=OPT.get('climate_entity','climate.152832117768500_climate'); CSW=OPT.get('climate_switch_entity','switch.klimaanlage'); LAMP=OPT.get('floor_lamp_entity','switch.stehlampe')
HISTORY_LIMIT=int(OPT.get('history_limit',12)); STATUS_CACHE_SECONDS=int(OPT.get('status_cache_seconds',180)); NOTIFICATION_COOLDOWN=int(OPT.get('notification_cooldown_seconds',120))
STATE=Path('/config'); STATE.mkdir(exist_ok=True); OFFSET=STATE/'telegram_offset.txt'; HIST=STATE/'ha_sentinel_history.jsonl'
RUN=True; LLM_LOCK=threading.Lock(); CACHE_LOCK=threading.Lock()
LAST={'snapshot':None,'snapshot_hash':None,'analysis':None,'dashboard':None,'analyzed_at':0.0,'published_hash':None,'published_at':0.0}
GROUPS={'Klima':[CLIMATE,CSW,'sensor.klimaanlage_energy_power','sensor.temperatur_temperature','sensor.temperatur_humidity'],'Netzwerk':['binary_sensor.8_8_8_8','sensor.ping_google_latency','sensor.fritz_box_7590_cpu_temperatur'],'Home Assistant':['sensor.localhost_config_datentragernutzung','sensor.backup_backup_manager_state','binary_sensor.rpi_power_status'],'Verbraucher':[LAMP,'sensor.waschmaschine_energy_power','sensor.spuelmaschine_energy_power','sensor.computer_energy_power','sensor.tv_energy_power'],'Saugroboter':['sensor.polnische_putzkraft_status','sensor.polnische_putzkraft_error','sensor.polnische_putzkraft_battery_level'],'Updates':['update.home_assistant_core_update','update.home_assistant_mcp_server_update']}
KEEP=('friendly_name','unit_of_measurement','device_class','current_temperature','temperature','fan_mode','hvac_action','battery_level','percentage')

def log(x): print(f'[{datetime.now().astimezone().isoformat(timespec="seconds")}] {x}',flush=True)
def stop(*_):
 global RUN; RUN=False
signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
def headers(): return {'Authorization':f'Bearer {TOKEN}','Content-Type':'application/json'}
def state(e):
 r=requests.get(f'{HA}/api/states/{e}',headers=headers(),timeout=15); r.raise_for_status(); d=r.json(); a=d.get('attributes',{}); return {'state':d.get('state'),'attributes':{k:a[k] for k in KEEP if k in a}}
def service(domain,name,e,data=None):
 p={'entity_id':e}; p.update(data or {}); r=requests.post(f'{HA}/api/services/{domain}/{name}',headers=headers(),json=p,timeout=20); r.raise_for_status()
def snapshot():
 groups={}; errors={}; count=0
 for name,entities in GROUPS.items():
  groups[name]={}
  for e in entities:
   try: groups[name][e]=state(e); count+=1
   except Exception as x: errors[e]=type(x).__name__
 return {'groups':groups,'errors':errors,'entity_count':count}
def get(s,e):
 for g in s['groups'].values():
  if e in g:return g[e]
 return {}
def digest(s):
 raw=json.dumps({'groups':s['groups'],'errors':s['errors']},ensure_ascii=False,sort_keys=True,separators=(',',':')); return hashlib.sha256(raw.encode()).hexdigest()
def valid(v): return v not in (None,'','unknown','unavailable','none')
def num(v):
 try:
  f=float(v); return str(int(f)) if f.is_integer() else str(round(f,1)).replace('.',',')
 except: return str(v)
def name(s,e,fallback): return get(s,e).get('attributes',{}).get('friendly_name',fallback)