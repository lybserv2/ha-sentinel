import re, threading, time
from datetime import datetime
import requests
from sentinel_config import *
from sentinel_ai import analyze, write_history
from sentinel_telegram_052 import poll
from sentinel_telegram import send

def publish(text,h,analysis):
 now=time.time()
 with CACHE_LOCK:
  if LAST['published_hash']==h and now-LAST['published_at']<NOTIFICATION_COOLDOWN:
   log('Benachrichtigung unterdrückt: identischer Snapshot im Cooldown'); return
  LAST['published_hash']=h; LAST['published_at']=now
 title=f'HA Sentinel - {datetime.now().astimezone():%H:%M}'; plain=re.sub(r'<[^>]+>','',text)
 requests.post(f'{HA}/api/services/persistent_notification/create',headers=headers(),json={'notification_id':'ha_sentinel_letzte_analyse','title':title,'message':plain},timeout=20).raise_for_status()
 ns=str(OPT.get('notify_service','')).strip()
 if ns and '.' in ns:
  d,n=ns.split('.',1); requests.post(f'{HA}/api/services/{d}/{n}',headers=headers(),json={'title':title,'message':plain},timeout=20).raise_for_status()
 if TG and TGT and CHAT: send(text)
 write_history(h,analysis)
def monitor():
 while RUN:
  started=time.monotonic()
  try:
   s,h,a,d,changed=analyze(False); log(f'Snapshot: {s["entity_count"]} Werte, {len(s["errors"])} Fehler, Hash {h[:12]}')
   if changed:
    log('KI: '+a)
    if OPT.get('notify_every_run',True): publish(d,h,a)
  except Exception as x: log(f'Analysefehler: {x}')
  for _ in range(max(1,INTERVAL-int(time.monotonic()-started))):
   if not RUN:break
   time.sleep(1)
def main():
 if not TOKEN:raise RuntimeError('SUPERVISOR_TOKEN fehlt')
 log('HA Sentinel 0.5.2 startet'); threading.Thread(target=poll,daemon=True).start(); monitor()
if __name__=='__main__':main()