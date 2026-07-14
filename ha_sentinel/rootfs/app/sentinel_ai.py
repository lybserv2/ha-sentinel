import html, json, re, time
from collections import deque
from datetime import datetime
import requests
from sentinel_config import *
from sentinel_rules import prompt_rules

def clean(t):
 t=re.sub(r'<think>.*?</think>','',t or '',flags=re.I|re.S); t=re.sub(r'[*_`#]+','',t); t=re.sub(r'^\s*[-•]+\s*','',t,flags=re.M); return ' '.join(t.split()).strip()
def llm(s,q='Nenne ausschließlich